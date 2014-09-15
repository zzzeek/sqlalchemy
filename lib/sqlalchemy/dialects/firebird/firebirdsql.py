# firebird/firebirdsql.py
# Copyright (C) 2005-2014 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: firebird+firebirdsql
    :name: firebirdsql
    :connectstring: firebird+firebirdsql://user:password@host:port/path/to/db[?key=value&key=value...]
    :url: https://pypi.python.org/pypi/firebirdsql

    firebirdsql is a DBAPI for Firebird.

Arguments
----------

The ``firebirdsql`` dialect is based on the :mod:`sqlalchemy.dialects.firebird.fdb`
dialect, however does not accept every argument that Kinterbasdb does.

"""
import sys
from re import match
from .base import FBDialect, FBExecutionContext
from ... import util

def Binary(x):
    if isinstance(x, bytes):
        return x
    if util.py3k:
        return str(x).encode('utf-8')
    else:
        return bytes(x)

class FBExecutionContext_kinterbasdb(FBExecutionContext):
    @property
    def rowcount(self):
        if self.execution_options.get('enable_rowcount',
                                        self.dialect.enable_rowcount):
            return self.cursor.rowcount
        else:
            return -1


class FBDialect_firebirdsql(FBDialect):
    driver = 'firebirdsql'
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False
    supports_native_decimal = True
    supports_unicode_statements = True

    def __init__(self, enable_rowcount=True,
                        retaining=False, **kwargs):
        super(FBDialect_firebirdsql, self).__init__(
                            enable_rowcount=True,
                            retaining=retaining, **kwargs)
        self.enable_rowcount = enable_rowcount
        self.retaining = retaining
        if enable_rowcount:
            self.supports_sane_rowcount = True

    @classmethod
    def dbapi(cls):
        module = __import__('firebirdsql')
        module.Binary = Binary
        return module

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if opts.get('port'):
            opts['host'] = "%s/%s" % (opts['host'], opts['port'])
            del opts['port']
        opts.update(url.query)

        return ([], opts)

    def _parse_version_info(self, version):
        m = match('\w+-[VT](\d+)\.(\d+)\.(\d+)\.(\d+)( \w+ (\d+)\.(\d+))?', version)
        if not m:
            raise AssertionError(
                    "Could not determine version from string '%s'" % version)

        if m.group(5) != None:
            return tuple([int(x) for x in m.group(6, 7, 4)] + ['firebird'])
        else:
            return tuple([int(x) for x in m.group(1, 2, 3)] + ['interbase'])

    def initialize(self, connection):
        super(FBDialect_firebirdsql, self).initialize(connection)

    def do_rollback(self, dbapi_connection):
        dbapi_connection.rollback(self.retaining)

    def do_commit(self, dbapi_connection):
        dbapi_connection.commit(self.retaining)


    def _get_server_version_info(self, connection):
        """Get the version of the Firebird server used by a connection.

        Returns a tuple of (`major`, `minor`, `build`), three integers
        representing the version of the attached server.
        """

        # This is the simpler approach (the other uses the services api),
        # that for backward compatibility reasons returns a string like
        #   LI-V6.3.3.12981 Firebird 2.0
        # where the first version is a fake one resembling the old
        # Interbase signature.

        isc_info_firebird_version = 103
        fbconn = connection.connection

        version = fbconn.db_info(isc_info_firebird_version)

        return self._parse_version_info(version)

    def is_disconnect(self, e, connection, cursor):
        return connection is None or connection.is_disconnect()

dialect = FBDialect_firebirdsql
