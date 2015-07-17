# connectors/pytds.py

from . import Connector
from ..util import asbool

import sys
import re
import urllib


class PyTDSConnector(Connector):
    driver = 'pytds'

    supports_sane_multi_rowcount = False
    supports_unicode = sys.maxunicode == 65535
    supports_unicode_binds = supports_unicode
    supports_unicode_statements = supports_unicode
    supports_native_decimal = True
    default_paramstyle = 'pyformat'

    @classmethod
    def dbapi(cls):
        return __import__('pytds')

    def is_disconnect(self, e, connection, cursor):
        if isinstance(e, self.dbapi.ProgrammingError):
            return "The cursor's connection has been closed." in str(e) or \
                            'Attempt to use a closed connection.' in str(e)
        elif isinstance(e, self.dbapi.Error):
            return '[08S01]' in str(e)
        else:
            return False

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        opts.update(url.query)

        keys = opts
        query = url.query

        connect_args = {}
        for param in ('autocommit', 'use_mars', 'as_dict'):
            if param in keys:
                connect_args[param] = asbool(keys.pop(param))
        for param in ('port', 'timeout', 'login_timeout'):
            if param in keys:
                connect_args[param] = int(keys.pop(param))
        for param in ('host', 'user', 'password', 'database'):
            if param in keys:
                connect_args[param] = keys.pop(param)
        connect_args['server'] = connect_args['host']
        del connect_args['host']

        return [[], connect_args]

    def _dbapi_version(self):
        if not self.dbapi:
            return ()
        return self._parse_dbapi_version(self.dbapi.version)

    def _parse_dbapi_version(self, vers):
        m = re.match(
                r'(?:py.*-)?([\d\.]+)(?:-(\w+))?',
                vers
            )
        if not m:
            return ()
        vers = tuple([int(x) for x in m.group(1).split(".")])
        if m.group(2):
            vers += (m.group(2),)
        return vers

    def _get_server_version_info(self, connection):
        l = connection.connection.product_version
        version = []
        for i in range(4):
            version.append(l&0xff)
            l >>= 8
        version.reverse()
        return tuple(version)
