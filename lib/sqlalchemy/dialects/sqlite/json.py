from ... import types as sqltypes


class JSON(sqltypes.JSON):
    """SQLite JSON type.

    SQLite supports JSON as of version 3.9 through its JSON1_ extension. Note
    that JSON1_ is a `loadable extension <https://www.sqlite.org/loadext.html>`_
    and as such may not be available, or may require run-time loading.

    The :class:`.sqlite.JSON` type supports persistence of JSON values
    as well as the core index operations provided by :class:`.types.JSON`
    datatype, by adapting the operations to render the ``JSON_EXTRACT``
    function wrapped in the ``JSON_QUOTE`` function at the database level.
    Extracted values are quoted in order to ensure that the results are
    always JSON string values.

    .. versionadded:: N/A
    .. _JSON1: https://www.sqlite.org/json1.html
    """


# TODO: MySQL and SQLite seem to share the same JSON path syntax, maybe unify?
class _FormatTypeMixin(object):
    def _format_value(self, value):
        raise NotImplementedError()

    def bind_processor(self, dialect):
        super_proc = self.string_bind_processor(dialect)

        def process(value):
            value = self._format_value(value)
            if super_proc:
                value = super_proc(value)
            return value

        return process

    def literal_processor(self, dialect):
        super_proc = self.string_literal_processor(dialect)

        def process(value):
            value = self._format_value(value)
            if super_proc:
                value = super_proc(value)
            return value

        return process


class JSONIndexType(_FormatTypeMixin, sqltypes.JSON.JSONIndexType):

    def _format_value(self, value):
        if isinstance(value, int):
            value = "$[%s]" % value
        else:
            value = '$."%s"' % value
        return value


class JSONPathType(_FormatTypeMixin, sqltypes.JSON.JSONPathType):
    def _format_value(self, value):
        return "$%s" % (
            "".join([
                "[%s]" % elem if isinstance(elem, int)
                else '."%s"' % elem for elem in value
            ])
        )
