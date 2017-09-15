# postgresql/pg8000.py
# Copyright (C) 2005-2018 the SQLAlchemy authors and contributors <see AUTHORS
# file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql+pg8000
    :name: pg8000
    :dbapi: pg8000
    :connectstring: \
postgresql+pg8000://user:password@host:port/dbname[?key=value&key=value...]
    :url: https://pythonhosted.org/pg8000/


.. _pg8000_unicode:

Unicode
-------

pg8000 will encode / decode string values between it and the server using the
PostgreSQL ``client_encoding`` parameter; by default this is the value in
the ``postgresql.conf`` file, which often defaults to ``SQL_ASCII``.
Typically, this can be changed to ``utf-8``, as a more useful default::

    #client_encoding = sql_ascii # actually, defaults to database
                                 # encoding
    client_encoding = utf8

The ``client_encoding`` can be overridden for a session by executing the SQL:

SET CLIENT_ENCODING TO 'utf8';

SQLAlchemy will execute this SQL on all new connections based on the value
passed to :func:`.create_engine` using the ``client_encoding`` parameter::

    engine = create_engine(
        "postgresql+pg8000://user:pass@host/dbname", client_encoding='utf8')


.. _pg8000_isolation_level:

pg8000 Transaction Isolation Level
-------------------------------------

The pg8000 dialect offers the same isolation level settings as that
of the :ref:`psycopg2 <psycopg2_isolation_level>` dialect:

* ``READ COMMITTED``
* ``READ UNCOMMITTED``
* ``REPEATABLE READ``
* ``SERIALIZABLE``
* ``AUTOCOMMIT``

.. versionadded:: 0.9.5 support for AUTOCOMMIT isolation level when using
   pg8000.

.. seealso::

    :ref:`postgresql_isolation_level`

    :ref:`psycopg2_isolation_level`


"""
from ... import util, exc
import decimal
from ... import processors
from ... import types as sqltypes
from .base import (
    PGDialect, PGCompiler, PGIdentifierPreparer, PGExecutionContext,
    _DECIMAL_TYPES, _FLOAT_TYPES, _INT_TYPES, UUID, ENUM, TSVECTOR)
import re
from sqlalchemy.dialects.postgresql.json import JSON, JSONB
from ...sql.elements import quoted_name, Null
import collections

try:
    from uuid import UUID as _python_UUID
except ImportError:
    _python_UUID = None


class _PGEnum(ENUM):
    def result_processor(self, dialect, coltype):
        if self.native_enum and util.py2k and self.convert_unicode is True:
            # we can't easily use PG's extensions here because
            # the OID is on the fly, and we need to give it a python
            # function anyway - not really worth it.
            self.convert_unicode = "force_nocheck"
        return super(_PGEnum, self).result_processor(dialect, coltype)

    def bind_processor(self, dialect):
        pg_enum = dialect.dbapi.PGEnum

        def process(value):
            return None if value is None else pg_enum(value)

        return process


class _PGNumeric(sqltypes.Numeric):
    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            if coltype in _FLOAT_TYPES:
                return processors.to_decimal_processor_factory(
                    decimal.Decimal, self._effective_decimal_return_scale)
            elif coltype in _DECIMAL_TYPES or coltype in _INT_TYPES:
                # pg8000 returns Decimal natively for 1700
                return None
            else:
                raise exc.InvalidRequestError(
                    "Unknown PG numeric type: %d" % coltype)
        else:
            if coltype in _FLOAT_TYPES:
                # pg8000 returns float natively for 701
                return None
            elif coltype in _DECIMAL_TYPES or coltype in _INT_TYPES:
                return processors.to_float
            else:
                raise exc.InvalidRequestError(
                    "Unknown PG numeric type: %d" % coltype)


class _PGNumericNoBind(_PGNumeric):
    def bind_processor(self, dialect):
        return None


class _PGJSON(JSON):
    def bind_processor(self, dialect):
        pg_json = dialect.dbapi.PGJson

        def process(value):
            if value is self.NULL:
                value = None
            elif isinstance(value, Null) or (
                    value is None and self.none_as_null):
                return None
            return pg_json(value)

        return process

    def result_processor(self, dialect, coltype):
        if dialect._dbapi_version > (1, 10, 1):
            return None  # Has native JSON
        else:
            return super(_PGJSON, self).result_processor(dialect, coltype)


class _PGJSONB(JSONB):

    def bind_processor(self, dialect):
        pg_jsonb = dialect.dbapi.PGJsonb

        def process(value):
            if value is self.NULL:
                value = None
            elif isinstance(value, Null) or (
                    value is None and self.none_as_null):
                return None
            return pg_jsonb(value)

        return process

    def result_processor(self, dialect, coltype):
        pass


class JSONPathType(sqltypes.JSON.JSONPathType):
    def bind_processor(self, dialect):
        def process(value):
            assert isinstance(value, collections.Sequence)
            return [util.text_type(elem)for elem in value]

        return process

    def literal_processor(self, dialect):
        super_proc = self.string_literal_processor(dialect)

        def process(value):
            assert isinstance(value, collections.Sequence)
            tokens = [util.text_type(elem)for elem in value]
            value = "{%s}" % (", ".join(tokens))
            if super_proc:
                value = super_proc(value)
            return value

        return process


class _PGTSVECTOR(TSVECTOR):

    def bind_processor(self, dialect):
        pg_tsvector = dialect.dbapi.PGTsvector

        def process(value):
            if value is not None:
                value = pg_tsvector(value)
            return value
        return process

    def result_processor(self, dialect, coltype):
        pass


class _PGVarchar(sqltypes.VARCHAR):
    def bind_processor(self, dialect):
        proc = super(_PGVarchar, self).bind_processor(dialect)
        if proc is None:
            return proc
        else:
            pg_varchar = dialect.dbapi.PGVarchar

            def new_proc(value):
                res = proc(value)
                if res is None:
                    return res
                else:
                    return pg_varchar(value)
            return new_proc


class _PGText(sqltypes.TEXT):
    def bind_processor(self, dialect):
        proc = super(_PGText, self).bind_processor(dialect)
        if proc is None:
            return proc
        else:
            pg_text = dialect.dbapi.PGText

            def new_proc(value):
                res = proc(value)
                if res is None:
                    return res
                else:
                    return pg_text(value)
            return new_proc


class _PGUUID(UUID):
    def bind_processor(self, dialect):
        if not self.as_uuid:
            def process(value):
                if value is not None:
                    value = _python_UUID(value)
                return value
            return process

    def result_processor(self, dialect, coltype):
        if not self.as_uuid:
            def process(value):
                if value is not None:
                    value = str(value)
                return value
            return process


class PGExecutionContext_pg8000(PGExecutionContext):
    pass


class PGCompiler_pg8000(PGCompiler):
    def visit_mod_binary(self, binary, operator, **kw):
        return self.process(binary.left, **kw) + " %% " + self.process(
            binary.right, **kw)


class PGIdentifierPreparer_pg8000(PGIdentifierPreparer):
    def __init__(self, *args, **kwargs):
        PGIdentifierPreparer.__init__(self, *args, **kwargs)
        self._double_percents = False


class PGDialect_pg8000(PGDialect):
    driver = 'pg8000'

    supports_unicode_statements = True

    supports_unicode_binds = True

    default_paramstyle = 'format'
    supports_sane_multi_rowcount = True
    execution_ctx_cls = PGExecutionContext_pg8000
    statement_compiler = PGCompiler_pg8000
    preparer = PGIdentifierPreparer_pg8000
    description_encoding = 'use_encoding'

    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            ENUM: _PGEnum,  # needs force_unicode
            sqltypes.Enum: _PGEnum,  # needs force_unicode
            sqltypes.Numeric: _PGNumericNoBind,
            sqltypes.Float: _PGNumeric,
            JSON: _PGJSON,
            sqltypes.JSON: _PGJSON,
            JSONB: _PGJSONB,
            sqltypes.JSON.JSONPathType: JSONPathType,
            TSVECTOR: _PGTSVECTOR,
            UUID: _PGUUID,
            sqltypes.VARCHAR: _PGVarchar,
            sqltypes.TEXT: _PGText,
            sqltypes.Text: _PGText,
            sqltypes.Unicode: _PGText,
            sqltypes.UnicodeText: _PGText,
            sqltypes.String: _PGText
        }
    )

    def __init__(self, client_encoding=None, **kwargs):
        PGDialect.__init__(self, **kwargs)
        self.client_encoding = client_encoding

    def initialize(self, connection):
        self.supports_sane_multi_rowcount = self._dbapi_version >= (1, 9, 14)
        super(PGDialect_pg8000, self).initialize(connection)

    @util.memoized_property
    def _dbapi_version(self):
        if self.dbapi and hasattr(self.dbapi, '__version__'):
            return tuple(
                [
                    int(x) for x in re.findall(
                        r'(\d+)(?:[-\.]?|$)', self.dbapi.__version__)])
        else:
            return (99, 99, 99)

    @classmethod
    def dbapi(cls):
        return __import__('pg8000')

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['port'] = int(opts['port'])
        opts.update(url.query)
        return ([], opts)

    def is_disconnect(self, e, connection, cursor):
        return "connection is closed" in str(e)

    def set_isolation_level(self, connection, level):
        level = level.replace('_', ' ')

        # adjust for ConnectionFairy possibly being present
        if hasattr(connection, 'connection'):
            connection = connection.connection

        if level == 'AUTOCOMMIT':
            connection.autocommit = True
        elif level in self._isolation_lookup:
            connection.autocommit = False
            cursor = connection.cursor()
            cursor.execute(
                "SET SESSION CHARACTERISTICS AS TRANSACTION "
                "ISOLATION LEVEL %s" % level)
            cursor.execute("COMMIT")
            cursor.close()
        else:
            raise exc.ArgumentError(
                "Invalid value '%s' for isolation_level. "
                "Valid isolation levels for %s are %s or AUTOCOMMIT" %
                (level, self.name, ", ".join(self._isolation_lookup))
            )

    def set_client_encoding(self, connection, client_encoding):
        # adjust for ConnectionFairy possibly being present
        if hasattr(connection, 'connection'):
            connection = connection.connection

        cursor = connection.cursor()
        cursor.execute("SET CLIENT_ENCODING TO '" + client_encoding + "'")
        cursor.execute("COMMIT")
        cursor.close()

    def do_begin_twophase(self, connection, xid):
        connection.connection.tpc_begin((0, xid, ''))

    def do_prepare_twophase(self, connection, xid):
        connection.connection.tpc_prepare()

    def do_rollback_twophase(
            self, connection, xid, is_prepared=True, recover=False):
        connection.connection.tpc_rollback((0, xid, ''))

    def do_commit_twophase(
            self, connection, xid, is_prepared=True, recover=False):
        connection.connection.tpc_commit((0, xid, ''))

    def do_recover_twophase(self, connection):
        return [row[1] for row in connection.connection.tpc_recover()]

    def on_connect(self):
        fns = []

        def on_connect(conn):
            conn.py_types[quoted_name] = conn.py_types[util.text_type]
        fns.append(on_connect)

        if self.client_encoding is not None:
            def on_connect(conn):
                self.set_client_encoding(conn, self.client_encoding)
            fns.append(on_connect)

        if self.isolation_level is not None:
            def on_connect(conn):
                self.set_isolation_level(conn, self.isolation_level)
            fns.append(on_connect)

        if len(fns) > 0:
            def on_connect(conn):
                for fn in fns:
                    fn(conn)
            return on_connect
        else:
            return None

dialect = PGDialect_pg8000
