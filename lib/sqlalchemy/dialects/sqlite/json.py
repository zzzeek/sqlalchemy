from ... import types as sqltypes


class JSON(sqltypes.JSON):
    """SQLite JSON type.

    SQLite supports JSON as of version 3.9 through its JSON1_ extension.
    Note that JSON1_ is a `loadable extension`_ and as such may not be
    available, or may require run-time loading.

    .. _JSON1: https://www.sqlite.org/json1.html
    .. _`loadable extension`: https://www.sqlite.org/loadext.html
    """

    class Comparator(sqltypes.JSON.Comparator):
        """Define comparison operations for :class:`.JSON`."""

        def _setup_getitem(self, index):
            operator, index, _ = super()._setup_getitem(index)
            # https://www.sqlite.org/json1.html#jex
            # "the SQL datatype of the result is NULL for a JSON null, INTEGER
            # or REAL for a JSON numeric value, an INTEGER zero for a JSON false
            # value, an INTEGER one for a JSON true value, the dequoted text for
            # a JSON string value, and a text representation for JSON object and
            # array values. If there are multiple path arguments (P1, P2, and so
            # forth) then this routine returns SQLite text which is a
            # well-formed JSON array holding the various values."
            return operator, index, sqltypes.NullType()

    comparator_factory = Comparator
