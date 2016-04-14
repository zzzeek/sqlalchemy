from ...sql.expression import ClauseElement, ColumnClause, ColumnElement
from ...ext.compiler import compiles
from ...exc import CompileError

__all__ = ('DoUpdate', 'DoNothing')

class _EXCLUDED:
    pass

def resolve_on_conflict_option(option_value, crud_columns):
    if option_value is None:
        return None
    if isinstance(option_value, OnConflictAction):
        return option_value
    if str(option_value) == 'update':
        if not crud_columns:
            raise CompileError("Cannot compile postgresql_on_conflict='update' option when no insert columns are available")
        crud_table_pk = crud_columns[0][0].table.primary_key
        if not crud_table_pk.columns:
            raise CompileError("Cannot compile postgresql_on_conflict='update' option when no target table has no primary key column(s)")
        return DoUpdate(crud_table_pk.columns.values()).set_with_excluded(
            *[c[0] for c in crud_columns if not crud_table_pk.contains_column(c[0])]
            )
    if str(option_value) == 'nothing':
        return DoNothing()

def resolve_columnish_arg(arg):
    for col in (arg if isinstance(arg, (list, tuple)) else (arg,)):
        if not isinstance(col, (ColumnClause, str)):
            raise ValueError("column arguments must be ColumnClause objects or str object with column name: %r" % col)
    return tuple(arg) if isinstance(arg, (list, tuple)) else (arg,)

class OnConflictAction(ClauseElement):
    def __init__(self, conflict_target):
        super(OnConflictAction, self).__init__()
        if not isinstance(conflict_target, ConflictTarget):
            conflict_target = ConflictTarget(conflict_target)
        self.conflict_target = conflict_target

class DoUpdate(OnConflictAction):
    def __init__(self, conflict_target):
        super(DoUpdate, self).__init__(conflict_target)
        if not self.conflict_target.contents:
            raise ValueError("conflict_target may not be None or empty for DoUpdate")
        self.values_to_set = {}

    def set_with_excluded(self, *columns):
        for col in resolve_columnish_arg(columns):
           self.values_to_set[col] = _EXCLUDED
        return self

class DoNothing(OnConflictAction):
    def __init__(self, conflict_target=[]):
        super(DoNothing, self).__init__(conflict_target)

class ConflictTarget(ClauseElement):
    def __init__(self, contents):
        self.contents = resolve_columnish_arg(contents)

@compiles(ConflictTarget)
def compile_conflict_target(conflict_target, compiler, **kw):
    if not conflict_target.contents:
        return ''
    return "(" + (", ".join(compiler.preparer.format_column(i) for i in conflict_target.contents)) + ")"

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
    compiled_cf = compiler.process(do_nothing.conflict_target)
    if compiled_cf:
        return "ON CONFLICT %s DO NOTHING" % compiled_cf
    else:
        return "ON CONFLICT DO NOTHING"

