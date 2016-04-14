from ...sql.expression import ClauseElement, ColumnClause, ColumnElement
from ...ext.compiler import compiles
from ...exc import CompileError
from ...schema import UniqueConstraint, PrimaryKeyConstraint, Index
from .ext import ExcludeConstraint

from collections import Iterable

__all__ = ('DoUpdate', 'DoNothing')

class _EXCLUDED:
    pass

def resolve_on_conflict_option(option_value, crud_columns):
    if option_value is None:
        return None
    if isinstance(option_value, OnConflictClause):
        return option_value
    if str(option_value) == 'update':
        if not crud_columns:
            raise CompileError("Cannot compile postgresql_on_conflict='update' option when no insert columns are available")
        crud_table_pk = crud_columns[0][0].table.primary_key
        if not crud_table_pk.columns:
            raise CompileError(
                "Cannot compile postgresql_on_conflict='update' "
                "option when no target table has no primary key column(s)"
                )
        return DoUpdate(crud_table_pk.columns.values()).set_with_excluded(
            *[c[0] for c in crud_columns if not crud_table_pk.contains_column(c[0])]
            )
    if str(option_value) == 'nothing':
        return DoNothing()

class OnConflictClause(ClauseElement):
    def __init__(self, conflict_target):
        super(OnConflictClause, self).__init__()
        self.conflict_target = conflict_target

class DoUpdate(OnConflictClause):
    """
    Represents an ``ON CONFLICT`` clause with a  ``DO UPDATE SET ...`` action.
    """
    def __init__(self, conflict_target):
        """
        :param conflict_target:
          One of the following: A single :class:`.Column` object to string with column name;
          a list or tuple of :class:`.Column` or column name strings;
          a single :class:`.PrimaryKeyConstraint`, :class:`.UniqueConstraint`, 
          or :class:`.postgresql.ExcludeConstraint`;
          or an :class:`.Index` object representing the constraint.  
          This value represents the unique constraint to target for conflict detection.
        """
        super(DoUpdate, self).__init__(ConflictTarget(conflict_target))
        if not self.conflict_target.contents:
            raise ValueError("conflict_target may not be None or empty for DoUpdate")
        self.values_to_set = {}

    def set_with_excluded(self, *columns):
        """
        :param \*columns:
          One or more :class:`.Column` objects or strings representing column names.
          These columns will be added to the ``SET`` clause using the `excluded` row's
          values from the same columns. e.g. ``SET colname = excluded.colname``.
        """
        super(DoUpdate, self).__init__(ConflictTarget(conflict_target))
        for col in columns:
            if not isinstance(col, (ColumnClause, str)):
                raise ValueError(
                    "column arguments must be ColumnClause objects "
                    "or str object with column name: %r" % col
                    )
            self.values_to_set[col] = _EXCLUDED
        return self

class DoNothing(OnConflictClause):
    """
    Represents an ``ON CONFLICT` clause with a ``DO NOTHING`` action.
    """
    def __init__(self, conflict_target=None):
        """
        :param conflict_target:
          Optional argument. If specified, one of the following:
          a single :class:`.Column` object to string with column name;
          a list or tuple of :class:`.Column` or column name strings;
          a single :class:`.PrimaryKeyConstraint`, :class:`.UniqueConstraint`, 
          or :class:`.postgresql.ExcludeConstraint`; 
          or an :class:`.Index` object representing a constraint. 
          This value represents 
          the unique constraint to target for conflict detection.
          If omitted, allows any unique constraint violation to cause
          the row insertion to be skipped.
        """
        super(DoUpdate, self).__init__(ConflictTarget(conflict_target))
        super(DoNothing, self).__init__(ConflictTarget(conflict_target) if conflict_target else None)

class ConflictTarget(ClauseElement):
    """
    A ConflictTarget represents the targeted constraint that will be used to determine
    when a row proposed for insertion is in conflict and should be handled as specified
    in the OnConflictClause.

    A target can be one of the following:

    - A column or list of columns, either column objects or strings, that together
      represent a unique or primary key constraint on the table. The compiler
      will produce a list like `(col1, col2, col3)` as the conflict target SQL clause.

    - A single PrimaryKeyConstraint or UniqueConstraint object representing the constraint
      used to detect the conflict. If the object has a :attr:`.name` attribute,
      the compiler will produce `ON CONSTRAINT constraint_name` as the conflict target
      SQL clause. If the constraint lacks a `.name` attribute, a list of its
      constituent columns, like `(col1, col2, col3)` will be used.

    - An single :class:`Index` object representing the index used to detect the conflict.
      Use this in place of the Constraint objects mentioned above if you require
      the clauses of a conflict target specific to index definitions -- collation,
      opclass used to detect conflict, and WHERE clauses for partial indexes.
    """
    def __init__(self, contents):
        if isinstance(contents, (str, ColumnClause)):
            self.contents = (contents,)
        elif isinstance(contents, (list, tuple)):
            if not contents:
                raise ValueError("list of column arguments cannot be empty")
            for c in contents:
                if not isinstance(c, (str, ColumnClause)):
                    raise ValueError("column arguments must be ColumnClause objects or str object with column name: %r" % c)
            self.contents = tuple(contents)
        elif isinstance(contents, (PrimaryKeyConstraint, UniqueConstraint, ExcludeConstraint, Index)):
            self.contents = contents
        else:
            raise ValueError(
                "ConflictTarget contents must be single Column/str, "
                "sequence of Column/str; or a PrimaryKeyConsraint, UniqueConstraint, or Index")

@compiles(ConflictTarget)
def compile_conflict_target(conflict_target, compiler, **kw):
    target = conflict_target.contents
    if isinstance(target, (PrimaryKeyConstraint, UniqueConstraint, ExcludeConstraint)):
        fmt_cnst = None
        if target.name is not None:
            fmt_cnst = compiler.preparer.format_constraint(target)
        if fmt_cnst is not None:
            return "ON CONSTRAINT %s" % fmt_cnst
        else:
            return "(" + (", ".join(compiler.preparer.format_column(i) for i in target.columns.values())) + ")"
    if isinstance(target, (str, ColumnClause)):
        return "(" + compiler.preparer.format_column(target) + ")"
    if isinstance(target, (list, tuple)):
        return "(" + (", ".join(compiler.preparer.format_column(i) for i in target)) + ")"
    if isinstance(target, Index):
        # columns required first.
        ops = target.dialect_options["postgresql"]["ops"]
        text = "(%s)" \
                % (
                    ', '.join([
                        compiler.process(
                            expr.self_group()
                            if not isinstance(expr, ColumnClause)
                            else expr,
                            include_table=False, literal_binds=True) +
                        (
                            (' ' + ops[expr.key])
                            if hasattr(expr, 'key')
                            and expr.key in ops else ''
                        )
                        for expr in target.expressions
                    ])
                )

        whereclause = target.dialect_options["postgresql"]["where"]

        if whereclause is not None:
            where_compiled = compiler.process(
                whereclause, include_table=False,
                literal_binds=True)
            text += " WHERE " + where_compiled
        return text

@compiles(DoUpdate)
def compile_do_update(do_update, compiler, **kw):
    compiled_cf = compiler.process(do_update.conflict_target)
    if not compiled_cf:
        raise CompileError("Cannot have empty conflict_target")
    text = "ON CONFLICT %s DO UPDATE" % compiled_cf
    if not do_update.values_to_set:
        raise CompileEror("Cannot have empty set of values to SET in DO UPDATE") 
    names = []
    for col, value in do_update.values_to_set.items():
        fmt_name = compiler.preparer.format_column(col) if isinstance(col, ColumnClause) else col
        if value is _EXCLUDED:
            fmt_value = "excluded.%s" % fmt_name
        else:
            # TODO support expressions/literals, other than excluded
            raise CompileError("Value to SET in DO UPDATE of unsupported type: %r" % value)
        names.append("%s = %s" % (fmt_name, fmt_value))
    text += (
        " SET " + 
        ", ".join(names)
        )
    return text

@compiles(DoNothing)
def compile_do_nothing(do_nothing, compiler, **kw):
    if do_nothing.conflict_target is not None:
        return "ON CONFLICT %s DO NOTHING" % compiler.process(do_nothing.conflict_target)
    else:
        return "ON CONFLICT DO NOTHING"

