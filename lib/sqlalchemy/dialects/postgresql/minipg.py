# postgresql/minipg.py
# Copyright (C) 2005-2014 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql+minipg
    :name: minipg
    :dbapi: minipg
    :connectstring: postgresql+minipg://user:password@host:port/dbname\
[?key=value&key=value...]
    :url: https://github.com/nakagami/minipg


"""
import decimal
from ... import util, exc
from ... import types as sqltypes
from .base import PGDialect, PGCompiler, \
    PGExecutionContext, _DECIMAL_TYPES, _FLOAT_TYPES, _INT_TYPES
from ... import processors

class _PGNumeric(sqltypes.Numeric):
    def bind_processor(self, dialect):
        return None

    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            if coltype in _FLOAT_TYPES:
                return processors.to_decimal_processor_factory(
                    decimal.Decimal,
                    self._effective_decimal_return_scale)
            elif coltype in _DECIMAL_TYPES or coltype in _INT_TYPES:
                # minipg returns Decimal natively for 1700
                return None
            else:
                raise exc.InvalidRequestError(
                    "Unknown PG numeric type: %d" % coltype)
        else:
            if coltype in _FLOAT_TYPES:
                # minipg returns float natively for 701
                return None
            elif coltype in _DECIMAL_TYPES or coltype in _INT_TYPES:
                return processors.to_float
            else:
                raise exc.InvalidRequestError(
                    "Unknown PG numeric type: %d" % coltype)



class PGCompiler_minipg(PGCompiler):
    def visit_match_op_binary(self, binary, operator, **kw):
        v = __import__('minipg').escape_parameter(binary.right)
        return "%s=%s" % (self.process(binary.left, **kw), v)

class PGDialect_minipg(PGDialect):
    driver = 'minipg'

    default_paramstyle = 'format'
    supports_sane_multi_rowcount = True
    supports_unicode_statements = True
    supports_unicode_binds = True
    description_encoding = 'use_encoding'
    statement_compiler = PGCompiler_minipg

    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            sqltypes.Numeric: _PGNumeric,
        }
    )

    @classmethod
    def dbapi(cls):
        return __import__('minipg')

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['port'] = int(opts['port'])
        else:
            opts['port'] = 5432
        opts.update(url.query)
        return ([], opts)

    def is_disconnect(self, e, connection, cursor):
        if not connection:
            return False
        return not connection.is_connect()

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


dialect = PGDialect_minipg
