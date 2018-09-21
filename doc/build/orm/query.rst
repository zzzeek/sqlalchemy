.. module:: sqlalchemy.orm

.. _query_api_toplevel:

=========
Query API
=========

This section presents the API reference for the ORM :class:`.Query` object.  For a walkthrough
of how to use this object, see :ref:`ormtutorial_toplevel`.

The Query Object
================

:class:`~.Query` is produced in terms of a given :class:`~.Session`, using the :meth:`~.Session.query` method:

.. sourcecode:: python

    q = session.query(SomeMappedClass)

Following is the full interface for the :class:`.Query` object.

.. autoclass:: sqlalchemy.orm.query.Query
   :members:

ORM-Specific Query Constructs
=============================

.. autofunction:: sqlalchemy.orm.aliased

.. autoclass:: sqlalchemy.orm.util.AliasedClass

.. autoclass:: sqlalchemy.orm.util.AliasedInsp

.. autoclass:: sqlalchemy.orm.query.Bundle
    :members:

.. autoclass:: sqlalchemy.util.KeyedTuple
    :members: keys, _fields, _asdict

.. autoclass:: sqlalchemy.orm.strategy_options.Load
    :members:

.. autofunction:: join

.. autofunction:: outerjoin

.. autofunction:: with_parent

