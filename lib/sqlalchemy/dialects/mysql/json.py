# postgresql/json.py
# Copyright (C) 2005-2015 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from __future__ import absolute_import

import collections
import json

from .base import ischema_names
from ... import types as sqltypes
from ...sql import elements
from ...sql import expression
from ... import util
from operator import getitem


__all__ = ('JSON',)


class JSON(sqltypes.Indexable, sqltypes.TypeEngine):

    """Represent the Mysql JSON type.

    The :class:`.JSON` type stores arbitrary JSON format data, e.g.::

        data_table = Table('data_table', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', JSON)
        )

        with engine.connect() as conn:
            conn.execute(
                data_table.insert(),
                data = {"key1": "value1", "key2": "value2"}
            )

    :class:`.JSON` provides several operations:

    * Index operations::

        data_table.c.data['some key']

    * Index operations with CAST
      (equivalent to
        ``CAST(JSON_EXPORT(data_table.data, $."some key" AS <type>)``)::

        data_table.c.data['some key'].cast(Integer)

    * Path index operations::

        data_table.c.data[('key_1', 'key_2', ..., 'key_n')]

    * Path attribute operations::

        data_table.c.data.json.key_1.key_2

        (equivalent to: data_table.c.data.json['key_1']['key_2'])

    * Wildcards::

        data_table.c.data['*'], rendered as [*], array index wildcard
        data_table.c.data['%'], rendered as .*, object key wildcard

    Index operations return an expression object whose type defaults to
    :class:`.JSON` by default, so that further JSON-oriented instructions
    may be called upon the result type.

    The :class:`.JSON` type, when used with the SQLAlchemy ORM, does not
    detect in-place mutations to the structure.  In order to detect these, the
    :mod:`sqlalchemy.ext.mutable` extension must be used.  This extension will
    allow "in-place" changes to the datastructure to produce events which
    will be detected by the unit of work.  See the example at :class:`.HSTORE`
    for a simple example involving a dictionary.

    When working with NULL values, the :class:`.JSON` type recommends the
    use of two specific constants in order to differentiate between a column
    that evaluates to SQL NULL, e.g. no value, vs. the JSON-encoded string
    of ``"null"``.   To insert or select against a value that is SQL NULL,
    use the constant :func:`.null`::

        conn.execute(table.insert(), json_value=null())

    To insert or select against a value that is JSON ``"null"``, use the
    constant :attr:`.JSON.NULL`::

        conn.execute(table.insert(), json_value=JSON.NULL)

    The :class:`.JSON` type supports a flag
    :paramref:`.JSON.none_as_null` which when set to True will result
    in the Python constant ``None`` evaluating to the value of SQL
    NULL, and when set to False results in the Python constant
    ``None`` evaluating to the value of JSON ``"null"``.    The Python
    value ``None`` may be used in conjunction with either
    :attr:`.JSON.NULL` and :func:`.null` in order to indicate NULL
    values, but care must be taken as to the value of the
    :paramref:`.JSON.none_as_null` in these cases.

    Custom serializers and deserializers are specified at the dialect level,
    that is using :func:`.create_engine`.  The reason for this is that when
    using psycopg2, the DBAPI only allows serializers at the per-cursor
    or per-connection level.   E.g.::

        engine = create_engine("postgresql://scott:tiger@localhost/test",
                                json_serializer=my_serialize_fn,
                                json_deserializer=my_deserialize_fn
                        )

    When using the psycopg2 dialect, the json_deserializer is registered
    against the database using ``psycopg2.extras.register_default_json``.

    .. versionadded:: 1.1

    """

    __visit_name__ = 'JSON'

    hashable = False

    NULL = util.symbol('JSON_NULL')
    """Describe the json value of NULL.

    This value is used to force the JSON value of ``"null"`` to be
    used as the value.   A value of Python ``None`` will be recognized
    either as SQL NULL or JSON ``"null"``, based on the setting
    of the :paramref:`.JSON.none_as_null` flag; the :attr:`.JSON.NULL`
    constant can be used to always resolve to JSON ``"null"`` regardless
    of this setting.  This is in contrast to the :func:`.sql.null` construct,
    which always resolves to SQL NULL.  E.g.::

        from sqlalchemy import null
        from sqlalchemy.dialects.postgresql import JSON

        obj1 = MyObject(json_value=null())  # *always* insert SQL NULL
        obj2 = MyObject(json_value=JSON.NULL)  # *always* insert JSON "null"

        session.add_all([obj1, obj2])
        session.commit()

    .. versionadded:: 1.1

    """

    def __init__(self, none_as_null=False):
        """Construct a :class:`.JSON` type.

        :param none_as_null: if True, persist the value ``None`` as a
         SQL NULL value, not the JSON encoding of ``null``.   Note that
         when this flag is False, the :func:`.null` construct can still
         be used to persist a NULL value::

             from sqlalchemy import null
             conn.execute(table.insert(), data=null())

         .. seealso::

              :attr:`.JSON.NULL`

         .. versionadded:: 1.1.0

         """
        self.none_as_null = none_as_null

    @property
    def should_evaluate_none(self):
        return not self.none_as_null

    class Comparator(
            sqltypes.Indexable.Comparator, sqltypes.Concatenable.Comparator):
        """Define comparison operations for :class:`.JSON`."""

        def _setup_getitem(self, index):
            return getitem, JSON._massage_index(index), self.type

        def operate(self, op, *other, **kwargs):
            if op.__name__ == 'getitem':
                return JSON.MySqlJsonExtract(self.expr, *other)
            else:
                if len(other) > 0 and isinstance(
                        other[0], (list, tuple, dict)):
                    # convert list, tuple or dict json doc.
                    other = list(other)
                    other[0] = JSON.MySqlJsonDocument(other[0], op)

                return super(JSON.Comparator, self).operate(
                    op, *other, **kwargs)

        @property
        def json(self):
            """Property which allows attribute access to document fields
            eg:
                data_table.c.data.json.k1

            is equivalent to:
                data_table.c.data['k1']
            """
            return JSON.MySqlJsonExtract(self.expr, "", attribute_access=True)

    comparator_factory = Comparator

    class MySqlJsonExtract(expression.Function, dict):
        """Represents a Json Extract Function which can be invoked via getitem.
        """

        def __init__(self, doc, path, attribute_access=False):
            self.json_doc = doc
            self.json_path = path
            self.attribute_access = attribute_access
            expression.Function.__init__(
                    self, "JSON_EXTRACT", doc, '$' + path, type_=JSON)

            # these two lines, along with the json property on the
            # comparator above, support the __getattr__ method below
            if self.attribute_access:
                local_dict = {}
                dict.__init__(self, local_dict)

        def __getitem__(self, path):
            """getitem on an existing json_extract just adds to the path"""
            new_path = self.json_path + JSON._massage_index(path)
            return JSON.MySqlJsonExtract(
                self.json_doc, new_path, attribute_access=self.attribute_access)

        def __getattr__(self, item):
            """Maps attributes to json doc path.  Only called if this class
            does not have an attribute with this name.  This allows attribute
            based access to sub-documents, but it means that hasattr()
            will now be broken when acting on this class.

            The test for "item[0] != '_' works around this for the known
            cases of hasattr() usage in the framework. So attributes names
            not starting with '_' will be considered to be part of the
            json document.
            """
            if self.attribute_access or item[0] != '_':
                return self.__getitem__(item)
            raise AttributeError(item)

    class MySqlJsonDocument(expression.Function):
        """Represents a literal Json Document"""

        def __init__(self, doc, op=None):
            if isinstance(doc, (list, tuple)):
                name = "json_array"
                empty = '[]'
            else:
                name = "json_object"
                empty = '{}'

            self.obj = doc
            bound_doc = expression.bindparam(
                    name, value=doc, type_=JSON, unique=True,
                    _compared_to_operator=op, _compared_to_type=JSON)

            # could not find a way to represent a json literal document,
            #  so resorted to JSON_MERGE() function which takes as a
            # parameter a json document.
            expression.Function.__init__(
                self, "JSON_MERGE", empty, bound_doc, type_=JSON)

    @staticmethod
    def _massage_index(index):
        """
        Integers are assumed to be array lookups and are formatted as: [x]
        Strings are assumed to be dict lookups and are formatted as: ."x"
        Wildcard ['*'] from python is formatted as an array wildcard [*]
        Wildcard ['%'] from python is formatted as an object wildcard .*
        """

        if isinstance(index, int):
            index = '[%d]' % index
        elif not isinstance(index, util.string_types):
            assert isinstance(index, collections.Sequence)
            tokens = ["%s" % JSON._massage_index(elem) for elem in index]
            index = "".join(tokens)
        elif index == '%':
            index = '.*'
        elif index == '*':
            index = '[*]'
        elif index[:2] != '**':
            index = '."%s"' % index
        return index

    def bind_processor(self, dialect):
        json_serializer = dialect._json_serializer or json.dumps
        if util.py2k:
            encoding = dialect.encoding
        else:
            encoding = None

        def process(value):
            if value is self.NULL:
                value = None
            elif isinstance(value, elements.Null) or (
                value is None and self.none_as_null
            ):
                return None
            if encoding:
                encoded = json_serializer(value).encode(encoding)
            else:
                encoded = json_serializer(value)

            return encoded

        return process

    def result_processor(self, dialect, coltype):
        json_deserializer = dialect._json_deserializer or json.loads
        if util.py2k:
            encoding = dialect.encoding
        else:
            encoding = None

        def process(value):
            if value is None:
                return None
            if encoding:
                value = value.decode(encoding)
            return json_deserializer(value)
        return process


ischema_names['json'] = JSON
