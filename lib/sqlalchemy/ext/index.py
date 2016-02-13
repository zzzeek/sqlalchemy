# ext/index.py
# Copyright (C) 2005-2016 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Property interface implementations for Indexable columns.

This is a private module.

"""
from __future__ import absolute_import

from ..sql.sqltypes import TypeEngine, JSON
from ..dialects import postgresql
from ..orm.attributes import flag_modified
from ..util.langhelpers import public_factory


__all__ = ['index_property', 'json_property']


class IndexPropertyInterface(object):
    """Describes an object attribute that corresponds to an indexable column.

    Public constructors are the :func:`.orm.index_property` and
    :func:`.orm.json_property` function

    """

    __slots__ = (
        'attr_name', 'index', 'default', 'use_column_default_for_none',
        'cast_type')

    class IndexPropertyDefault(object):
        def __init__(self, arg):
            self.arg = arg

    column_index_mappers = {
        JSON: lambda key: str(key),
        postgresql.JSON: lambda key: str(key),
        postgresql.ARRAY: lambda index: index + 1,  # 1-based index in pg
        postgresql.HSTORE: lambda key: str(key),
    }

    def __init__(self, attr_name, index, **kwargs):
        """Provide a sub-column property ingredients for Indexable typed columns.

        An index property subscribe an index of a column with Indexable type.
        Use this function to concentrate more on each index of indexable columns.

        See `index_property` or `json_property` for actual properties.

        :param attr_name:
            An attritube name of a `Indexable` typed column.

        :param index:
            An index with matching type for column's type.

        :param default:
            When given, accessing will returns the value if IndexError or
            KeyError is raised while accessing by the index.

        :param use_column_default_for_none:
            When ``True``, the subscribing column will be automatically set to
            its default value.
        """
        if 'default' in kwargs:
            default = self.IndexPropertyDefault(kwargs.pop('default'))
        else:
            default = None
        use_column_default_for_none = kwargs.pop('use_column_default_for_none',
                                                 False)

        if kwargs:
            raise TypeError('Unknown parameter(s) for index property: %s'
                            % kwargs.keys())

        self.attr_name = attr_name
        self.index = index
        self.default = default
        self.use_column_default_for_none = use_column_default_for_none

    def fget(self, instance):
        attr_name = self.attr_name
        column_value = getattr(instance, attr_name)
        if column_value is None:
            if self.use_column_default_for_none and\
                    (self.use_column_default_for_none is True or
                     'getter' in self.use_column_default_for_none):
                column = getattr(instance.__class__, attr_name)
                column_value = column.default.arg
            elif self.default:
                return self.default.arg
        try:
            return column_value[self.index]
        except (KeyError, IndexError):
            if self.default:
                return self.default.arg
            raise

    def fset(self, instance, value):
        attr_name = self.attr_name
        column_value = getattr(instance, attr_name)
        if column_value is None:
            if self.use_column_default_for_none and\
                    (self.use_column_default_for_none is True or
                     'setter' in self.use_column_default_for_none):
                column = getattr(instance.__class__, attr_name)
                column_value = column.default.arg
        column_value[self.index] = value
        setattr(instance, attr_name, column_value)
        flag_modified(instance, attr_name)

    def fdel(self, instance):
        attr_name = self.attr_name
        column_value = getattr(instance, attr_name)
        if column_value is None:
            if self.use_column_default_for_none and \
                    (self.use_column_default_for_none is True or
                     'deleter' in self.use_column_default_for_none):
                column = getattr(self.__class__, attr_name)
                column_value = column.default.arg
        del column_value[self.index]
        setattr(instance, attr_name, column_value)
        flag_modified(instance, attr_name)

    def expr(self, model):
        column = getattr(model, self.attr_name)

        index = self.index
        column_type = type(column.type)
        column_index_mapper = self.column_index_mappers.get(column_type, None)
        if column_index_mapper:
            index = column_index_mapper(index)
        expr = column[index]
        return expr

    def json_expr(self, model):
        expr = self.expr(model)
        if self.cast_type is not None:
            expr = expr.astext.cast(self.cast_type)
        return expr

    @classmethod
    def property(cls, column, index, **kwargs):
        from sqlalchemy.ext.hybrid import hybrid_property

        mutable = kwargs.pop('mutable', False)
        interface = cls(column, index, **kwargs)
        if mutable:
            property = hybrid_property(interface.fget, interface.fset,
                                       interface.fdel, interface.expr)
        else:
            property = hybrid_property(interface.fget, None, None,
                                       interface.expr)
        return property

    @classmethod
    def json_property(cls, column, index, **kwargs):
        from sqlalchemy.ext.hybrid import hybrid_property

        cast_type = kwargs.pop('cast_type', None)
        if cast_type is not None:
            if not (isinstance(cast_type, TypeEngine) or callable(cast_type)):
                raise TypeError("'cast_type' must be a schema type but '%s' "
                                "found" % cast_type)

        mutable = kwargs.pop('mutable', False)
        interface = cls(column, index, **kwargs)
        interface.cast_type = cast_type
        if mutable:
            property = hybrid_property(interface.fget, interface.fset,
                                       interface.fdel, interface.json_expr)
        else:
            property = hybrid_property(interface.fget, None, None,
                                       interface.json_expr)
        return property


index_property = public_factory(IndexPropertyInterface.property,
                                ".ext.index.index_property")
json_property = public_factory(IndexPropertyInterface.json_property,
                               ".ext.index.json_property")
