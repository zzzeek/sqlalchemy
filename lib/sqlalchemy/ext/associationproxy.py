# ext/associationproxy.py
# Copyright (C) 2005-2018 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Contain the ``AssociationProxy`` class.

The ``AssociationProxy`` is a Python property object which provides
transparent proxied access to the endpoint of an association object.

See the example ``examples/association/proxied_association.py``.

"""
import operator
import weakref
from .. import exc, orm, util
from ..orm import collections, interfaces
from ..sql import or_
from .. import inspect


def association_proxy(target_collection, attr, **kw):
    r"""Return a Python property implementing a view of a target
    attribute which references an attribute on members of the
    target.

    The returned value is an instance of :class:`.AssociationProxy`.

    Implements a Python property representing a relationship as a collection
    of simpler values, or a scalar value.  The proxied property will mimic
    the collection type of the target (list, dict or set), or, in the case of
    a one to one relationship, a simple scalar value.

    :param target_collection: Name of the attribute we'll proxy to.
      This attribute is typically mapped by
      :func:`~sqlalchemy.orm.relationship` to link to a target collection, but
      can also be a many-to-one or non-scalar relationship.

    :param attr: Attribute on the associated instance or instances we'll
      proxy for.

      For example, given a target collection of [obj1, obj2], a list created
      by this proxy property would look like [getattr(obj1, *attr*),
      getattr(obj2, *attr*)]

      If the relationship is one-to-one or otherwise uselist=False, then
      simply: getattr(obj, *attr*)

    :param creator: optional.

      When new items are added to this proxied collection, new instances of
      the class collected by the target collection will be created.  For list
      and set collections, the target class constructor will be called with
      the 'value' for the new instance.  For dict types, two arguments are
      passed: key and value.

      If you want to construct instances differently, supply a *creator*
      function that takes arguments as above and returns instances.

      For scalar relationships, creator() will be called if the target is None.
      If the target is present, set operations are proxied to setattr() on the
      associated object.

      If you have an associated object with multiple attributes, you may set
      up multiple association proxies mapping to different attributes.  See
      the unit tests for examples, and for examples of how creator() functions
      can be used to construct the scalar relationship on-demand in this
      situation.

    :param \*\*kw: Passes along any other keyword arguments to
      :class:`.AssociationProxy`.

    """
    return AssociationProxy(target_collection, attr, **kw)


ASSOCIATION_PROXY = util.symbol('ASSOCIATION_PROXY')
"""Symbol indicating an :class:`InspectionAttr` that's
    of type :class:`.AssociationProxy`.

   Is assigned to the :attr:`.InspectionAttr.extension_type`
   attibute.

"""


class AssociationProxy(interfaces.InspectionAttrInfo):
    """A descriptor that presents a read/write view of an object attribute."""

    is_attribute = False
    extension_type = ASSOCIATION_PROXY

    def __init__(self, target_collection, attr, creator=None,
                 getset_factory=None, proxy_factory=None,
                 proxy_bulk_set=None, info=None,
                 cascade_scalar_deletes=False):
        """Construct a new :class:`.AssociationProxy`.

        The :func:`.association_proxy` function is provided as the usual
        entrypoint here, though :class:`.AssociationProxy` can be instantiated
        and/or subclassed directly.

        :param target_collection: Name of the collection we'll proxy to,
          usually created with :func:`.relationship`.

        :param attr: Attribute on the collected instances we'll proxy
          for.  For example, given a target collection of [obj1, obj2], a
          list created by this proxy property would look like
          [getattr(obj1, attr), getattr(obj2, attr)]

        :param creator: Optional. When new items are added to this proxied
          collection, new instances of the class collected by the target
          collection will be created.  For list and set collections, the
          target class constructor will be called with the 'value' for the
          new instance.  For dict types, two arguments are passed:
          key and value.

          If you want to construct instances differently, supply a 'creator'
          function that takes arguments as above and returns instances.

        :param cascade_scalar_deletes: when True, indicates that setting
         the proxied value to ``None``, or deleting it via ``del``, should
         also remove the source object.  Only applies to scalar attributes.
         Normally, removing the proxied target will not remove the proxy
         source, as this object may have other state that is still to be
         kept.

         .. versionadded:: 1.3

        :param getset_factory: Optional.  Proxied attribute access is
          automatically handled by routines that get and set values based on
          the `attr` argument for this proxy.

          If you would like to customize this behavior, you may supply a
          `getset_factory` callable that produces a tuple of `getter` and
          `setter` functions.  The factory is called with two arguments, the
          abstract type of the underlying collection and this proxy instance.

        :param proxy_factory: Optional.  The type of collection to emulate is
          determined by sniffing the target collection.  If your collection
          type can't be determined by duck typing or you'd like to use a
          different collection implementation, you may supply a factory
          function to produce those collections.  Only applicable to
          non-scalar relationships.

        :param proxy_bulk_set: Optional, use with proxy_factory.  See
          the _set() method for details.

        :param info: optional, will be assigned to
         :attr:`.AssociationProxy.info` if present.

         .. versionadded:: 1.0.9

        """
        self.target_collection = target_collection
        self.value_attr = attr
        self.creator = creator
        self.getset_factory = getset_factory
        self.proxy_factory = proxy_factory
        self.proxy_bulk_set = proxy_bulk_set
        self.cascade_scalar_deletes = cascade_scalar_deletes

        self.owning_class = None
        self.key = '_%s_%s_%s' % (
            type(self).__name__, target_collection, id(self))
        self.collection_class = None
        if info:
            self.info = info

    @property
    def remote_attr(self):
        """The 'remote' :class:`.MapperProperty` referenced by this
        :class:`.AssociationProxy`.

        .. versionadded:: 0.7.3

        See also:

        :attr:`.AssociationProxy.attr`

        :attr:`.AssociationProxy.local_attr`

        """
        return getattr(self.target_class, self.value_attr)

    @property
    def local_attr(self):
        """The 'local' :class:`.MapperProperty` referenced by this
        :class:`.AssociationProxy`.

        .. versionadded:: 0.7.3

        See also:

        :attr:`.AssociationProxy.attr`

        :attr:`.AssociationProxy.remote_attr`

        """
        return getattr(self.owning_class, self.target_collection)

    @property
    def attr(self):
        """Return a tuple of ``(local_attr, remote_attr)``.

        This attribute is convenient when specifying a join
        using :meth:`.Query.join` across two relationships:

        .. sourcecode:: python

            sess.query(Parent).join(*Parent.proxied.attr)

        .. versionadded:: 0.7.3

        See also:

        :attr:`.AssociationProxy.local_attr`

        :attr:`.AssociationProxy.remote_attr`

        """
        return (self.local_attr, self.remote_attr)

    def _get_property(self):
        owning_class = self.owning_class
        if owning_class is None:
            raise exc.InvalidRequestError(
                "This association proxy has no mapped owning class; "
                "can't locate a mapped property")
        return (orm.class_mapper(owning_class).
                get_property(self.target_collection))

    @util.memoized_property
    def target_class(self):
        """The intermediary class handled by this :class:`.AssociationProxy`.

        Intercepted append/set/assignment events will result
        in the generation of new instances of this class.

        """
        return self._get_property().mapper.class_

    @util.memoized_property
    def scalar(self):
        """Return ``True`` if this :class:`.AssociationProxy` proxies a scalar
        relationship on the local side."""

        scalar = not self._get_property().uselist
        if scalar:
            self._initialize_scalar_accessors()
        return scalar

    @util.memoized_property
    def _value_is_scalar(self):
        return not self._get_property().\
            mapper.get_property(self.value_attr).uselist

    @util.memoized_property
    def _target_is_object(self):
        return getattr(self.target_class, self.value_attr).impl.uses_objects

    def _calc_owner(self, obj, class_):
        if obj is not None and class_ is None:
            target_cls = type(obj)
        elif class_ is not None:
            target_cls = class_
        else:
            return

        # we might be getting invoked for a subclass
        # that is not mapped yet, in some declarative situations.
        # save until we are mapped
        try:
            insp = inspect(target_cls)
        except exc.NoInspectionAvailable:
            # can't find a mapper, don't set owner. if we are a not-yet-mapped
            # subclass, we can also scan through __mro__ to find a mapped
            # class, but instead just wait for us to be called again against a
            # mapped class normally.
            return

        # note we can get our real .key here too
        owner = insp.mapper.class_manager._locate_owning_manager(self)
        if owner is not None:
            self.owning_class = owner.class_
        else:
            # the proxy is attached to a class that is not mapped
            # (like a mixin), we are mapped, so, it's us.
            self.owning_class = target_cls

    def __get__(self, obj, class_):
        if self.owning_class is None:
            self._calc_owner(obj, class_)

        if obj is None:
            return self

        if self.scalar:
            target = getattr(obj, self.target_collection)
            return self._scalar_get(target)
        else:
            try:
                # If the owning instance is reborn (orm session resurrect,
                # etc.), refresh the proxy cache.
                creator_id, proxy = getattr(obj, self.key)
                if id(obj) == creator_id:
                    return proxy
            except AttributeError:
                pass
            proxy = self._new(_lazy_collection(obj, self.target_collection))
            setattr(obj, self.key, (id(obj), proxy))
            return proxy

    def __set__(self, obj, values):
        if self.owning_class is None:
            self._calc_owner(obj, None)

        if self.scalar:
            creator = self.creator and self.creator or self.target_class
            target = getattr(obj, self.target_collection)
            if target is None:
                if values is None:
                    return
                setattr(obj, self.target_collection, creator(values))
            else:
                self._scalar_set(target, values)
                if values is None and self.cascade_scalar_deletes:
                    setattr(obj, self.target_collection, None)
        else:
            proxy = self.__get__(obj, None)
            if proxy is not values:
                proxy.clear()
                self._set(proxy, values)

    def __delete__(self, obj):
        if self.owning_class is None:
            self._calc_owner(obj, None)

        if self.scalar:
            target = getattr(obj, self.target_collection)
            if target is not None:
                delattr(target, self.value_attr)
        delattr(obj, self.target_collection)

    def _initialize_scalar_accessors(self):
        if self.getset_factory:
            get, set = self.getset_factory(None, self)
        else:
            get, set = self._default_getset(None)
        self._scalar_get, self._scalar_set = get, set

    def _default_getset(self, collection_class):
        attr = self.value_attr
        _getter = operator.attrgetter(attr)

        def getter(target):
            return _getter(target) if target is not None else None

        if collection_class is dict:
            def setter(o, k, v):
                setattr(o, attr, v)
        else:
            def setter(o, v):
                setattr(o, attr, v)
        return getter, setter

    def _new(self, lazy_collection):
        creator = self.creator and self.creator or self.target_class
        self.collection_class = util.duck_type_collection(lazy_collection())

        if self.proxy_factory:
            return self.proxy_factory(
                lazy_collection, creator, self.value_attr, self)

        if self.getset_factory:
            getter, setter = self.getset_factory(self.collection_class, self)
        else:
            getter, setter = self._default_getset(self.collection_class)

        if self.collection_class is list:
            return _AssociationList(
                lazy_collection, creator, getter, setter, self)
        elif self.collection_class is dict:
            return _AssociationDict(
                lazy_collection, creator, getter, setter, self)
        elif self.collection_class is set:
            return _AssociationSet(
                lazy_collection, creator, getter, setter, self)
        else:
            raise exc.ArgumentError(
                'could not guess which interface to use for '
                'collection_class "%s" backing "%s"; specify a '
                'proxy_factory and proxy_bulk_set manually' %
                (self.collection_class.__name__, self.target_collection))

    def _inflate(self, proxy):
        creator = self.creator and self.creator or self.target_class

        if self.getset_factory:
            getter, setter = self.getset_factory(self.collection_class, self)
        else:
            getter, setter = self._default_getset(self.collection_class)

        proxy.creator = creator
        proxy.getter = getter
        proxy.setter = setter

    def _set(self, proxy, values):
        if self.proxy_bulk_set:
            self.proxy_bulk_set(proxy, values)
        elif self.collection_class is list:
            proxy.extend(values)
        elif self.collection_class is dict:
            proxy.update(values)
        elif self.collection_class is set:
            proxy.update(values)
        else:
            raise exc.ArgumentError(
                'no proxy_bulk_set supplied for custom '
                'collection_class implementation')

    @property
    def _comparator(self):
        return self._get_property().comparator

    @util.memoized_property
    def _unwrap_target_assoc_proxy(self):
        attr = getattr(self.target_class, self.value_attr)
        if isinstance(attr, AssociationProxy):
            return attr
        return None

    def _criterion_exists(self, criterion=None, **kwargs):
        is_has = kwargs.pop('is_has', None)

        target_assoc = self._unwrap_target_assoc_proxy
        if target_assoc is not None:
            inner = target_assoc._criterion_exists(
                criterion=criterion, **kwargs)
            return self._comparator._criterion_exists(inner)

        if self._target_is_object:
            prop = getattr(self.target_class, self.value_attr)
            value_expr = prop._criterion_exists(criterion, **kwargs)
        else:
            if kwargs:
                raise exc.ArgumentError(
                    "Can't apply keyword arguments to column-targeted "
                    "association proxy; use =="
                )
            elif is_has and criterion is not None:
                raise exc.ArgumentError(
                    "Non-empty has() not allowed for "
                    "column-targeted association proxy; use =="
                )

            value_expr = criterion

        return self._comparator._criterion_exists(value_expr)

    def any(self, criterion=None, **kwargs):
        """Produce a proxied 'any' expression using EXISTS.

        This expression will be a composed product
        using the :meth:`.RelationshipProperty.Comparator.any`
        and/or :meth:`.RelationshipProperty.Comparator.has`
        operators of the underlying proxied attributes.

        """
        if self._unwrap_target_assoc_proxy is None and (
            self.scalar and (
                not self._target_is_object or self._value_is_scalar)
        ):
            raise exc.InvalidRequestError(
                "'any()' not implemented for scalar "
                "attributes. Use has()."
            )
        return self._criterion_exists(
            criterion=criterion, is_has=False, **kwargs)

    def has(self, criterion=None, **kwargs):
        """Produce a proxied 'has' expression using EXISTS.

        This expression will be a composed product
        using the :meth:`.RelationshipProperty.Comparator.any`
        and/or :meth:`.RelationshipProperty.Comparator.has`
        operators of the underlying proxied attributes.

        """
        if self._unwrap_target_assoc_proxy is None and (
                not self.scalar or (
                self._target_is_object and not self._value_is_scalar)
        ):
            raise exc.InvalidRequestError(
                "'has()' not implemented for collections.  "
                "Use any().")
        return self._criterion_exists(
            criterion=criterion, is_has=True, **kwargs)

    def contains(self, obj):
        """Produce a proxied 'contains' expression using EXISTS.

        This expression will be a composed product
        using the :meth:`.RelationshipProperty.Comparator.any`
        , :meth:`.RelationshipProperty.Comparator.has`,
        and/or :meth:`.RelationshipProperty.Comparator.contains`
        operators of the underlying proxied attributes.
        """

        target_assoc = self._unwrap_target_assoc_proxy
        if target_assoc is not None:
            return self._comparator._criterion_exists(
                target_assoc.contains(obj)
                if not target_assoc.scalar else target_assoc == obj
            )
        elif self._target_is_object and self.scalar and \
                not self._value_is_scalar:
            return self._comparator.has(
                getattr(self.target_class, self.value_attr).contains(obj)
            )
        elif self._target_is_object and self.scalar and \
                self._value_is_scalar:
            raise exc.InvalidRequestError(
                "contains() doesn't apply to a scalar endpoint; use ==")
        else:

            return self._comparator._criterion_exists(**{self.value_attr: obj})

    def __eq__(self, obj):
        # note the has() here will fail for collections; eq_()
        # is only allowed with a scalar.
        if obj is None:
            return or_(
                self._comparator.has(**{self.value_attr: obj}),
                self._comparator == None
            )
        else:
            return self._comparator.has(**{self.value_attr: obj})

    def __ne__(self, obj):
        # note the has() here will fail for collections; eq_()
        # is only allowed with a scalar.
        return self._comparator.has(
            getattr(self.target_class, self.value_attr) != obj)

    def __repr__(self):
        return "AssociationProxy(%r, %r)" % (
            self.target_collection, self.value_attr)


class _lazy_collection(object):
    def __init__(self, obj, target):
        self.ref = weakref.ref(obj)
        self.target = target

    def __call__(self):
        obj = self.ref()
        if obj is None:
            raise exc.InvalidRequestError(
                "stale association proxy, parent object has gone out of "
                "scope")
        return getattr(obj, self.target)

    def __getstate__(self):
        return {'obj': self.ref(), 'target': self.target}

    def __setstate__(self, state):
        self.ref = weakref.ref(state['obj'])
        self.target = state['target']


class _AssociationCollection(object):
    def __init__(self, lazy_collection, creator, getter, setter, parent):
        """Constructs an _AssociationCollection.

        This will always be a subclass of either _AssociationList,
        _AssociationSet, or _AssociationDict.

        lazy_collection
          A callable returning a list-based collection of entities (usually an
          object attribute managed by a SQLAlchemy relationship())

        creator
          A function that creates new target entities.  Given one parameter:
          value.  This assertion is assumed:

          .. sourcecode:: python

            obj = creator(somevalue)
            assert getter(obj) == somevalue

        getter
          A function.  Given an associated object, return the 'value'.

        setter
          A function.  Given an associated object and a value, store that
          value on the object.

        """
        self.lazy_collection = lazy_collection
        self.creator = creator
        self.getter = getter
        self.setter = setter
        self.parent = parent

    col = property(lambda self: self.lazy_collection())

    def __len__(self):
        return len(self.col)

    def __bool__(self):
        return bool(self.col)

    __nonzero__ = __bool__

    def __getstate__(self):
        return {'parent': self.parent, 'lazy_collection': self.lazy_collection}

    def __setstate__(self, state):
        self.parent = state['parent']
        self.lazy_collection = state['lazy_collection']
        self.parent._inflate(self)


class _AssociationList(_AssociationCollection):
    """Generic, converting, list-to-list proxy."""

    def _create(self, value):
        return self.creator(value)

    def _get(self, object):
        return self.getter(object)

    def _set(self, object, value):
        return self.setter(object, value)

    def __getitem__(self, index):
        if not isinstance(index, slice):
            return self._get(self.col[index])
        else:
            return [self._get(member) for member in self.col[index]]

    def __setitem__(self, index, value):
        if not isinstance(index, slice):
            self._set(self.col[index], value)
        else:
            if index.stop is None:
                stop = len(self)
            elif index.stop < 0:
                stop = len(self) + index.stop
            else:
                stop = index.stop
            step = index.step or 1

            start = index.start or 0
            rng = list(range(index.start or 0, stop, step))
            if step == 1:
                for i in rng:
                    del self[start]
                i = start
                for item in value:
                    self.insert(i, item)
                    i += 1
            else:
                if len(value) != len(rng):
                    raise ValueError(
                        "attempt to assign sequence of size %s to "
                        "extended slice of size %s" % (len(value),
                                                       len(rng)))
                for i, item in zip(rng, value):
                    self._set(self.col[i], item)

    def __delitem__(self, index):
        del self.col[index]

    def __contains__(self, value):
        for member in self.col:
            # testlib.pragma exempt:__eq__
            if self._get(member) == value:
                return True
        return False

    def __getslice__(self, start, end):
        return [self._get(member) for member in self.col[start:end]]

    def __setslice__(self, start, end, values):
        members = [self._create(v) for v in values]
        self.col[start:end] = members

    def __delslice__(self, start, end):
        del self.col[start:end]

    def __iter__(self):
        """Iterate over proxied values.

        For the actual domain objects, iterate over .col instead or
        just use the underlying collection directly from its property
        on the parent.
        """

        for member in self.col:
            yield self._get(member)
        return

    def append(self, value):
        col = self.col
        item = self._create(value)
        col.append(item)

    def count(self, value):
        return sum([1 for _ in
                    util.itertools_filter(lambda v: v == value, iter(self))])

    def extend(self, values):
        for v in values:
            self.append(v)

    def insert(self, index, value):
        self.col[index:index] = [self._create(value)]

    def pop(self, index=-1):
        return self.getter(self.col.pop(index))

    def remove(self, value):
        for i, val in enumerate(self):
            if val == value:
                del self.col[i]
                return
        raise ValueError("value not in list")

    def reverse(self):
        """Not supported, use reversed(mylist)"""

        raise NotImplementedError

    def sort(self):
        """Not supported, use sorted(mylist)"""

        raise NotImplementedError

    def clear(self):
        del self.col[0:len(self.col)]

    def __eq__(self, other):
        return list(self) == other

    def __ne__(self, other):
        return list(self) != other

    def __lt__(self, other):
        return list(self) < other

    def __le__(self, other):
        return list(self) <= other

    def __gt__(self, other):
        return list(self) > other

    def __ge__(self, other):
        return list(self) >= other

    def __cmp__(self, other):
        return util.cmp(list(self), other)

    def __add__(self, iterable):
        try:
            other = list(iterable)
        except TypeError:
            return NotImplemented
        return list(self) + other

    def __radd__(self, iterable):
        try:
            other = list(iterable)
        except TypeError:
            return NotImplemented
        return other + list(self)

    def __mul__(self, n):
        if not isinstance(n, int):
            return NotImplemented
        return list(self) * n
    __rmul__ = __mul__

    def __iadd__(self, iterable):
        self.extend(iterable)
        return self

    def __imul__(self, n):
        # unlike a regular list *=, proxied __imul__ will generate unique
        # backing objects for each copy.  *= on proxied lists is a bit of
        # a stretch anyhow, and this interpretation of the __imul__ contract
        # is more plausibly useful than copying the backing objects.
        if not isinstance(n, int):
            return NotImplemented
        if n == 0:
            self.clear()
        elif n > 1:
            self.extend(list(self) * (n - 1))
        return self

    def copy(self):
        return list(self)

    def __repr__(self):
        return repr(list(self))

    def __hash__(self):
        raise TypeError("%s objects are unhashable" % type(self).__name__)

    for func_name, func in list(locals().items()):
        if (util.callable(func) and func.__name__ == func_name and
                not func.__doc__ and hasattr(list, func_name)):
            func.__doc__ = getattr(list, func_name).__doc__
    del func_name, func


_NotProvided = util.symbol('_NotProvided')


class _AssociationDict(_AssociationCollection):
    """Generic, converting, dict-to-dict proxy."""

    def _create(self, key, value):
        return self.creator(key, value)

    def _get(self, object):
        return self.getter(object)

    def _set(self, object, key, value):
        return self.setter(object, key, value)

    def __getitem__(self, key):
        return self._get(self.col[key])

    def __setitem__(self, key, value):
        if key in self.col:
            self._set(self.col[key], key, value)
        else:
            self.col[key] = self._create(key, value)

    def __delitem__(self, key):
        del self.col[key]

    def __contains__(self, key):
        # testlib.pragma exempt:__hash__
        return key in self.col

    def has_key(self, key):
        # testlib.pragma exempt:__hash__
        return key in self.col

    def __iter__(self):
        return iter(self.col.keys())

    def clear(self):
        self.col.clear()

    def __eq__(self, other):
        return dict(self) == other

    def __ne__(self, other):
        return dict(self) != other

    def __lt__(self, other):
        return dict(self) < other

    def __le__(self, other):
        return dict(self) <= other

    def __gt__(self, other):
        return dict(self) > other

    def __ge__(self, other):
        return dict(self) >= other

    def __cmp__(self, other):
        return util.cmp(dict(self), other)

    def __repr__(self):
        return repr(dict(self.items()))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        if key not in self.col:
            self.col[key] = self._create(key, default)
            return default
        else:
            return self[key]

    def keys(self):
        return self.col.keys()

    if util.py2k:
        def iteritems(self):
            return ((key, self._get(self.col[key])) for key in self.col)

        def itervalues(self):
            return (self._get(self.col[key]) for key in self.col)

        def iterkeys(self):
            return self.col.iterkeys()

        def values(self):
            return [self._get(member) for member in self.col.values()]

        def items(self):
            return [(k, self._get(self.col[k])) for k in self]
    else:
        def items(self):
            return ((key, self._get(self.col[key])) for key in self.col)

        def values(self):
            return (self._get(self.col[key]) for key in self.col)

    def pop(self, key, default=_NotProvided):
        if default is _NotProvided:
            member = self.col.pop(key)
        else:
            member = self.col.pop(key, default)
        return self._get(member)

    def popitem(self):
        item = self.col.popitem()
        return (item[0], self._get(item[1]))

    def update(self, *a, **kw):
        if len(a) > 1:
            raise TypeError('update expected at most 1 arguments, got %i' %
                            len(a))
        elif len(a) == 1:
            seq_or_map = a[0]
            # discern dict from sequence - took the advice from
            # http://www.voidspace.org.uk/python/articles/duck_typing.shtml
            # still not perfect :(
            if hasattr(seq_or_map, 'keys'):
                for item in seq_or_map:
                    self[item] = seq_or_map[item]
            else:
                try:
                    for k, v in seq_or_map:
                        self[k] = v
                except ValueError:
                    raise ValueError(
                        "dictionary update sequence "
                        "requires 2-element tuples")

        for key, value in kw:
            self[key] = value

    def copy(self):
        return dict(self.items())

    def __hash__(self):
        raise TypeError("%s objects are unhashable" % type(self).__name__)

    for func_name, func in list(locals().items()):
        if (util.callable(func) and func.__name__ == func_name and
                not func.__doc__ and hasattr(dict, func_name)):
            func.__doc__ = getattr(dict, func_name).__doc__
    del func_name, func


class _AssociationSet(_AssociationCollection):
    """Generic, converting, set-to-set proxy."""

    def _create(self, value):
        return self.creator(value)

    def _get(self, object):
        return self.getter(object)

    def __len__(self):
        return len(self.col)

    def __bool__(self):
        if self.col:
            return True
        else:
            return False

    __nonzero__ = __bool__

    def __contains__(self, value):
        for member in self.col:
            # testlib.pragma exempt:__eq__
            if self._get(member) == value:
                return True
        return False

    def __iter__(self):
        """Iterate over proxied values.

        For the actual domain objects, iterate over .col instead or just use
        the underlying collection directly from its property on the parent.

        """
        for member in self.col:
            yield self._get(member)
        return

    def add(self, value):
        if value not in self:
            self.col.add(self._create(value))

    # for discard and remove, choosing a more expensive check strategy rather
    # than call self.creator()
    def discard(self, value):
        for member in self.col:
            if self._get(member) == value:
                self.col.discard(member)
                break

    def remove(self, value):
        for member in self.col:
            if self._get(member) == value:
                self.col.discard(member)
                return
        raise KeyError(value)

    def pop(self):
        if not self.col:
            raise KeyError('pop from an empty set')
        member = self.col.pop()
        return self._get(member)

    def update(self, other):
        for value in other:
            self.add(value)

    def __ior__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        for value in other:
            self.add(value)
        return self

    def _set(self):
        return set(iter(self))

    def union(self, other):
        return set(self).union(other)

    __or__ = union

    def difference(self, other):
        return set(self).difference(other)

    __sub__ = difference

    def difference_update(self, other):
        for value in other:
            self.discard(value)

    def __isub__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        for value in other:
            self.discard(value)
        return self

    def intersection(self, other):
        return set(self).intersection(other)

    __and__ = intersection

    def intersection_update(self, other):
        want, have = self.intersection(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)

    def __iand__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        want, have = self.intersection(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)
        return self

    def symmetric_difference(self, other):
        return set(self).symmetric_difference(other)

    __xor__ = symmetric_difference

    def symmetric_difference_update(self, other):
        want, have = self.symmetric_difference(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)

    def __ixor__(self, other):
        if not collections._set_binops_check_strict(self, other):
            return NotImplemented
        want, have = self.symmetric_difference(other), set(self)

        remove, add = have - want, want - have

        for value in remove:
            self.remove(value)
        for value in add:
            self.add(value)
        return self

    def issubset(self, other):
        return set(self).issubset(other)

    def issuperset(self, other):
        return set(self).issuperset(other)

    def clear(self):
        self.col.clear()

    def copy(self):
        return set(self)

    def __eq__(self, other):
        return set(self) == other

    def __ne__(self, other):
        return set(self) != other

    def __lt__(self, other):
        return set(self) < other

    def __le__(self, other):
        return set(self) <= other

    def __gt__(self, other):
        return set(self) > other

    def __ge__(self, other):
        return set(self) >= other

    def __repr__(self):
        return repr(set(self))

    def __hash__(self):
        raise TypeError("%s objects are unhashable" % type(self).__name__)

    for func_name, func in list(locals().items()):
        if (util.callable(func) and func.__name__ == func_name and
                not func.__doc__ and hasattr(set, func_name)):
            func.__doc__ = getattr(set, func_name).__doc__
    del func_name, func
