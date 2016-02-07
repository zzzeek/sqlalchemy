# postgresql/pygresql.py
# Copyright (C) 2005-2016 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql+pygresql
    :name: pygresql
    :dbapi: pgdb
    :connectstring: postgresql+pygresql://user:password@host:port/dbname\
[?key=value&key=value...]
    :url: http://www.pygresql.org/
"""

import decimal
import re

from ... import exc, processors, util
from ...types import Numeric, JSON as Json
from .base import PGDialect, _DECIMAL_TYPES, _FLOAT_TYPES, _INT_TYPES, UUID
from .hstore import HSTORE
from .json import JSON, JSONB


class _PGNumeric(Numeric):

    def bind_processor(self, dialect):
        return None

    def result_processor(self, dialect, coltype):
        oid = coltype.oid
        if self.asdecimal:
            if oid in _FLOAT_TYPES:
                return processors.to_decimal_processor_factory(
                    decimal.Decimal,
                    self._effective_decimal_return_scale)
            elif oid in _DECIMAL_TYPES or coltype in _INT_TYPES:
                # PyGreSQL returns Decimal natively for 1700 (numeric)
                return None
            else:
                raise exc.InvalidRequestError(
                    "Unknown PG numeric type: %d" % coltype)
        else:
            if oid in _FLOAT_TYPES:
                # PyGreSQL returns float natively for 701 (float8)
                return None
            elif oid in _DECIMAL_TYPES or coltype in _INT_TYPES:
                return processors.to_float
            else:
                raise exc.InvalidRequestError(
                    "Unknown PG numeric type: %d" % coltype)


class _PGHStore(HSTORE):

    def bind_processor(self, dialect):
        if not dialect.use_native_hstore:
            return super(_PGHStore, self).bind_processor(dialect)

    def result_processor(self, dialect, coltype):
        if not dialect.use_native_hstore:
            return super(_PGHStore, self).result_processor(dialect, coltype)


class _PGJSON(JSON):

    def bind_processor(self, dialect):
        if not dialect.use_native_json:
            return super(_PGJSON, self).bind_processor(dialect)

    def result_processor(self, dialect, coltype):
        if not dialect.use_native_json:
            return super(_PGJSON, self).result_processor(dialect, coltype)


class _PGJSONB(JSONB):

    def bind_processor(self, dialect):
        if not dialect.use_native_json:
            return super(_PGJSONB, self).bind_processor(dialect)

    def result_processor(self, dialect, coltype):
        if not dialect.use_native_json:
            return super(_PGJSONB, self).result_processor(dialect, coltype)


class _PGUUID(UUID):

    def bind_processor(self, dialect):
        if not dialect.use_native_uuid:
            return super(_PGUUID, self).bind_processor(dialect)

    def result_processor(self, dialect, coltype):
        if not dialect.use_native_uuid:
            return super(_PGUUID, self).result_processor(dialect, coltype)


class PGDialect_pygresql(PGDialect):
    driver = 'pygresql'

    _has_native_hstore = False

    @classmethod
    def dbapi(cls):
        import pgdb
        return pgdb

    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            Numeric: _PGNumeric,
            HSTORE: _PGHStore,
            Json: _PGJSON,
            JSON: _PGJSON,
            JSONB: _PGJSONB,
            UUID: _PGUUID,
        }
    )

    def __init__(self, use_native_hstore=False,
            use_native_json=False, use_native_uuid=True, **kwargs):
        super(PGDialect_pygresql, self).__init__(**kwargs)
        try:
            version = self.dbapi.version
            m = re.match(r'(\d+)\.(\d+)', version)
            version = (int(m.group(1)), int(m.group(2)))
        except (AttributeError, ValueError, TypeError):
            version = (0, 0)
        self.dbapi_version = version
        self.use_native_hstore = use_native_hstore and version >= (5, 0)
        self.use_native_json = use_native_json and version >= (5, 0)
        self.use_native_uuid = use_native_uuid and version >= (5, 0)

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['host'] = '%s:%s' % (
                opts.get('host', '').rsplit(':', 1)[0], opts.pop('port'))
        opts.update(url.query)
        return [], opts


dialect = PGDialect_pygresql
