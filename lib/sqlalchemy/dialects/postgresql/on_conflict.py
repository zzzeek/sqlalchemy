from sqlalchemy.sql.expression import ClauseElement, ColumnClause, ColumnElement
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.exc import CompileError

__all__ = ('DoUpdate', 'DoNothing')

def resolve_on_conflict_option(option_value, crud_columns):
    if option_value is None:
        return None
    if isinstance(option_value, OnConflictBase):
        return option_value
    if str(option_value).lower() in ('update', 'do update'):
        if not crud_columns:
            raise CompileError("Cannot perform postgresql_on_conflict='update' when no insert columns are available")
        return DoUpdate([c[0] for c in crud_columns if c[0].primary_key]).with_excluded([c[0] for c in crud_columns if not c[0].primary_key])
    if str(option_value).lower() in ('nothing', 'do nothing'):
        return DoNothing()

def resolve_columnish_arg(arg):
    for col in (arg if isinstance(arg, (list, tuple)) else (arg,)):
        if not isinstance(col, (ColumnClause, str)):
            raise ValueError("column arguments must be ColumnClause objects or str object with column name: %r" % col)
    return tuple(arg) if isinstance(arg, (list, tuple)) else (arg,)

class OnConflictBase(ClauseElement):
    def __init__(self, conflict_target):
        super(OnConflictBase, self).__init__()
        if not isinstance(conflict_target, ConflictTarget):
            conflict_target = ConflictTarget(conflict_target)
        self.conflict_target = conflict_target

class DoUpdate(OnConflictBase):
    def __init__(self, conflict_target):
        super(DoUpdate, self).__init__(conflict_target)
        if not self.conflict_target.content:
            raise ValueError("conflict_target may not be None or empty for DoUpdate")
        self.excluded_columns = None

    def with_excluded(self, columns):
        self.excluded_columns = resolve_columnish_arg(columns)
        return self

class DoNothing(OnConflictBase):
    def __init__(self, conflict_target=[]):
        super(DoNothing, self).__init__(conflict_target)

class ConflictTarget(ClauseElement):
    def __init__(self, content):
        self.content = resolve_columnish_arg(content)

@compiles(ConflictTarget)
def compile_conflict_target(conflict_target, compiler, **kw):
    if not conflict_target.content:
        return ''
    return "(" + (", ".join(compiler.preparer.format_column(i) for i in conflict_target.content)) + ")"

@compiles(DoUpdate)
def compile_do_update(do_update, compiler, **kw):
    compiled_cf = compiler.process(do_update.conflict_target)
    if not compiled_cf:
        raise Exception("Can't have empty conflict_target")
    text = "ON CONFLICT %s DO UPDATE" % compiled_cf
    if do_update.excluded_columns:
        names = []
        for col in do_update.excluded_columns:
            fmt_name = compiler.preparer.format_column(col) if isinstance(col, ColumnClause) else col
            names.append("%s = excluded.%s" % (fmt_name, fmt_name))
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

