from .base import MSExecutionContext, MSDialect
from ...connectors.pytds import PyTDSConnector

class MSExecutionContext_pytds(MSExecutionContext):
    _embedded_scope_identity = False

    def pre_exec(self):
        super(MSExecutionContext_pytds, self).pre_exec()
        if self._select_lastrowid and \
                self.dialect.use_scope_identity and \
                len(self.parameters[0]):
            self._embedded_scope_identity = True

            self.statement += "; select scope_identity()"

    def post_exec(self):
        if self._embedded_scope_identity:
            while True:
                try:
                    row = self.cursor.fetchall()[0]
                    break
                except self.dialect.dbapi.Error, e:
                    self.cursor.nextset()

            self._lastrowid = int(row[0])
        else:
            super(MSExecutionContext_pytds, self).post_exec()


class MSDialect_pytds(PyTDSConnector, MSDialect):

    execution_ctx_cls = MSExecutionContext_pytds

    def __init__(self, description_encoding=None, **params):
        super(MSDialect_pytds, self).__init__(**params)
        self.description_encoding = description_encoding
        self.use_scope_identity = True

dialect = MSDialect_pytds
