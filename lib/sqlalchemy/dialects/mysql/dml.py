from ...sql.elements import ClauseElement, _literal_as_binds
from ...sql.dml import Insert as StandardInsert
from ...sql.expression import alias
from ...util.langhelpers import public_factory
from ...sql.base import _generative
from ... import util

__all__ = ('Insert', 'insert')


class Insert(StandardInsert):
    @util.memoized_property
    def vals(self):
        self.values_alias = alias(self.table, name='values')
        return self.values_alias.columns

    @_generative
    def on_duplicate_key_update(self, **update):
        values_alias = getattr(self, 'values_alias', None)
        self._post_values_clause = OnDuplicateClause(values_alias, update)
        return self


insert = public_factory(Insert, '.dialects.postgresql.insert')


class OnDuplicateClause(ClauseElement):
    __visit_name__ = 'on_duplicate_key_update'
    def __init__(self, values_alias, update):
        self.values_alias = values_alias
        if not update or not isinstance(update, dict):
            raise ValueError('update parameter must be a non-empty dictionary')
        self.update = update

