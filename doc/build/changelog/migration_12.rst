=============================
What's New in SQLAlchemy 1.2?
=============================

.. admonition:: About this Document

    This document describes changes between SQLAlchemy version 1.1
    and SQLAlchemy version 1.2.   1.2 is currently under development
    and is unreleased.


Introduction
============

This guide introduces what's new in SQLAlchemy version 1.2,
and also documents changes which affect users migrating
their applications from the 1.1 series of SQLAlchemy to 1.2.

Please carefully review the sections on behavioral changes for
potentially backwards-incompatible changes in behavior.

Platform Support
================

Targeting Python 2.7 and Up
---------------------------

SQLAlchemy 1.2 now moves the minimum Python version to 2.7, no longer
supporting 2.6.   New language features are expected to be merged
into the 1.2 series that were not supported in Python 2.6.  For Python 3 support,
SQLAlchemy is currently tested on versions 3.5 and 3.6.


New Features and Improvements - ORM
===================================

.. _change_3954:

"Baked" loading now the default for lazy loads
----------------------------------------------

The :mod:`sqlalchemy.ext.baked` extension, first introduced in the 1.0 series,
allows for the construction of a so-called :class:`.BakedQuery` object,
which is an object that generates a :class:`.Query` object in conjunction
with a cache key representing the structure of the query; this cache key
is then linked to the resulting string SQL statement so that subsequent use
of another :class:`.BakedQuery` with the same structure will bypass all the
overhead of building the :class:`.Query` object, building the core
:func:`.select` object within, as well as the compilation of the :func:`.select`
into a string, cutting out well the majority of function call overhead normally
associated with constructing and emitting an ORM :class:`.Query` object.

The :class:`.BakedQuery` is now used by default by the ORM when it generates
a "lazy" query for the lazy load of a :func:`.relationship` construct, e.g.
that of the default ``lazy="select"`` relationship loader strategy.  This
will allow for a significant reduction in function calls within the scope
of an application's use of lazy load queries to load collections and related
objects.   Previously, this feature was available
in 1.0 and 1.1 through the use of a global API method or by using the
``baked_select`` strategy, it's now the only implementation for this behavior.
The feature has also been improved such that the caching can still take place
for objects that have additional loader options in effect subsequent
to the lazy load.

The caching behavior can be disabled on a per-relationship basis using the
:paramref:`.relationship.bake_queries` flag, which is available for
very unusual cases, such as a relationship that uses a custom
:class:`.Query` implementation that's not compatible with caching.


:ticket:`3954`

.. _change_3944:

New "selectin" eager loading, loads all collections at once using IN
--------------------------------------------------------------------

A new eager loader called "selectin" loading is added, which in many ways
is similar to "subquery" loading, however produces a simpler SQL statement
that is cacheable as well as more efficient.

Given a query as below::

    q = session.query(User).\
        filter(User.name.like('%ed%')).\
        options(subqueryload(User.addresses))

The SQL produced would be the query against ``User`` followed by the
subqueryload for ``User.addresses`` (note the parameters are also listed)::

    SELECT users.id AS users_id, users.name AS users_name
    FROM users
    WHERE users.name LIKE ?
    ('%ed%',)

    SELECT addresses.id AS addresses_id,
           addresses.user_id AS addresses_user_id,
           addresses.email_address AS addresses_email_address,
           anon_1.users_id AS anon_1_users_id
    FROM (SELECT users.id AS users_id
    FROM users
    WHERE users.name LIKE ?) AS anon_1
    JOIN addresses ON anon_1.users_id = addresses.user_id
    ORDER BY anon_1.users_id
    ('%ed%',)

With "selectin" loading, we instead get a SELECT that refers to the
actual primary key values loaded in the parent query::

    q = session.query(User).\
        filter(User.name.like('%ed%')).\
        options(selectinload(User.addresses))

Produces::

    SELECT users.id AS users_id, users.name AS users_name
    FROM users
    WHERE users.name LIKE ?
    ('%ed%',)

    SELECT users_1.id AS users_1_id,
           addresses.id AS addresses_id,
           addresses.user_id AS addresses_user_id,
           addresses.email_address AS addresses_email_address
    FROM users AS users_1
    JOIN addresses ON users_1.id = addresses.user_id
    WHERE users_1.id IN (?, ?)
    ORDER BY users_1.id
    (1, 3)

The above SELECT statement includes these advantages:

* It doesn't use a subquery, just an INNER JOIN, meaning it will perform
  much better on a database like MySQL that doesn't like subqueries

* Its structure is independent of the original query; in conjunction with the
  new :ref:`expanding IN parameter system <change_3953>_` we can in most cases
  use the "baked" query to cache the string SQL, reducing per-query overhead
  significantly

* Because the query only fetches for a given list of primary key identifiers,
  "selectin" loading is potentially compatible with :meth:`.Query.yield_per` to
  operate on chunks of a SELECT result at a time, provided that the
  database driver allows for multiple, simultaneous cursors (SQlite, Postgresql;
  **not** MySQL drivers or SQL Server ODBC drivers).   Neither joined eager
  loading nor subquery eager loading are compatible with :meth:`.Query.yield_per`.

The disadvanages of selectin eager loading are potentially large SQL
queries, with large lists of IN parameters.  The list of IN parameters themselves
are chunked in groups of 500, so a result set of more than 500 lead objects
will have more additional "SELECT IN" queries following.  Also, support
for composite primary keys depends on the database's ability to use
tuples with IN, e.g.
``(table.column_one, table_column_two) IN ((?, ?), (?, ?) (?, ?))``.
Currently, Postgresql and MySQL are known to be compatible with this syntax,
SQLite is not.

.. seealso::

    :ref:`selectin_eager_loading`

:ticket:`3944`

.. _change_3229:

Support for bulk updates of hybrids, composites
-----------------------------------------------

Both hybrid attributes (e.g. :mod:`sqlalchemy.ext.hybrid`) as well as composite
attributes (:ref:`mapper_composite`) now support being used in the
SET clause of an UPDATE statement when using :meth:`.Query.update`.

For hybrids, simple expressions can be used directly, or the new decorator
:meth:`.hybrid_property.update_expression` can be used to break a value
into multiple columns/expressions::

    class Person(Base):
        # ...

        first_name = Column(String(10))
        last_name = Column(String(10))

        @hybrid.hybrid_property
        def name(self):
            return self.first_name + ' ' + self.last_name

        @name.expression
        def name(cls):
            return func.concat(cls.first_name, ' ', cls.last_name)

        @name.update_expression
        def name(cls, value):
            f, l = value.split(' ', 1)
            return [(cls.first_name, f), (cls.last_name, l)]

Above, an UPDATE can be rendered using::

    session.query(Person).filter(Person.id == 5).update(
        {Person.name: "Dr. No"})

Similar functionality is available for composites, where composite values
will be broken out into their individual columns for bulk UPDATE::

    session.query(Vertex).update({Edge.start: Point(3, 4)})


.. seealso::

    :ref:`hybrid_bulk_update`

.. _change_3911_3912:

Hybrid attributes support reuse among subclasses, redefinition of @getter
-------------------------------------------------------------------------

The :class:`sqlalchemy.ext.hybrid.hybrid_property` class now supports
calling mutators like ``@setter``, ``@expression`` etc. multiple times
across subclasses, and now provides a ``@getter`` mutator, so that
a particular hybrid can be repurposed across subclasses or other
classes.  This now is similar to the behavior of ``@property`` in standard
Python::

    class FirstNameOnly(Base):
        # ...

        first_name = Column(String)

        @hybrid_property
        def name(self):
            return self.first_name

        @name.setter
        def name(self, value):
            self.first_name = value

    class FirstNameLastName(FirstNameOnly):
        # ...

        last_name = Column(String)

        @FirstNameOnly.name.getter
        def name(self):
            return self.first_name + ' ' + self.last_name

        @name.setter
        def name(self, value):
            self.first_name, self.last_name = value.split(' ', maxsplit=1)

        @name.expression
        def name(cls):
            return func.concat(cls.first_name, ' ', cls.last_name)

Above, the ``FirstNameOnly.name`` hybrid is referenced by the
``FirstNameLastName`` subclass in order to repurpose it specifically to the
new subclass.   This is achieved by copying the hybrid object to a new one
within each call to ``@getter``, ``@setter``, as well as in all other
mutator methods like ``@expression``, leaving the previous hybrid's definition
intact.  Previously, methods like ``@setter`` would modify the existing
hybrid in-place, interfering with the definition on the superclass.

.. note:: Be sure to read the documentation at :ref:`hybrid_reuse_subclass`
   for important notes regarding how to override
   :meth:`.hybrid_property.expression`
   and :meth:`.hybrid_property.comparator`, as a special qualifier
   :attr:`.hybrid_property.overrides` may be necessary to avoid name
   conflicts with :class:`.QueryableAttribute` in some cases.

:ticket:`3911`

:ticket:`3912`

.. _change_3896_event:

New bulk_replace event
----------------------

To suit the validation use case described in :ref:`change_3896_validates`,
a new :meth:`.AttributeEvents.bulk_replace` method is added, which is
called in conjunction with the :meth:`.AttributeEvents.append` and
:meth:`.AttributeEvents.remove` events.  "bulk_replace" is called before
"append" and "remove" so that the collection can be modified ahead of comparison
to the existing collection.   After that, individual items
are appended to a new target collection, firing off the "append"
event for items new to the collection, as was the previous behavior.
Below illustrates both "bulk_replace" and
"append" at the same time, including that "append" will receive an object
already handled by "bulk_replace" if collection assignment is used.
A new symbol :attr:`~.attributes.OP_BULK_REPLACE` may be used to determine
if this "append" event is the second part of a bulk replace::

    from sqlalchemy.orm.attributes import OP_BULK_REPLACE

    @event.listens_for(SomeObject.collection, "bulk_replace")
    def process_collection(target, values, initiator):
        values[:] = [_make_value(value) for value in values]

    @event.listens_for(SomeObject.collection, "append", retval=True)
    def process_collection(target, value, initiator):
        # make sure bulk_replace didn't already do it
        if initiator is None or initiator.op is not OP_BULK_REPLACE:
            return _make_value(value)
        else:
            return value


:ticket:`3896`



New Features and Improvements - Core
====================================

.. _change_3919:

Pessimistic disconnection detection added to the connection pool
----------------------------------------------------------------

The connection pool documentation has long featured a recipe for using
the :meth:`.ConnectionEvents.engine_connect` engine event to emit a simple
statement on a checked-out connection to test it for liveness.   The
functionality of this recipe has now been added into the connection pool
itself, when used in conjunction with an appropriate dialect.   Using
the new parameter :paramref:`.create_engine.pool_pre_ping`, each connection
checked out will be tested for freshness before being returned::

    engine = create_engine("mysql+pymysql://", pool_pre_ping=True)

While the "pre-ping" approach adds a small amount of latency to the connection
pool checkout, for a typical application that is transactionally-oriented
(which includes most ORM applications), this overhead is minimal, and
eliminates the problem of acquiring a stale connection that will raise
an error, requiring that the application either abandon or retry the operation.

The feature does **not** accommodate for connections dropped within
an ongoing transaction or SQL operation.  If an application must recover
from these as well, it would need to employ its own operation retry logic
to anticipate these errors.


.. seealso::

    :ref:`pool_disconnects_pessimistic`


:ticket:`3919`

.. _change_3907:

The IN / NOT IN operator's empty collection behavior is now configurable; default expression simplified
-------------------------------------------------------------------------------------------------------

An expression such as ``column.in_([])``, which is assumed to be false,
now produces the expression ``1 != 1``
by default, instead of ``column != column``.  This will **change the result**
of a query that is comparing a SQL expression or column that evaluates to
NULL when compared to an empty set, producing a boolean value false or true
(for NOT IN) rather than NULL.  The warning that would emit under
this condition is also removed.  The old behavior is available using the
:paramref:`.create_engine.empty_in_strategy` parameter to
:func:`.create_engine`.

In SQL, the IN and NOT IN operators do not support comparison to a
collection of values that is explicitly empty; meaning, this syntax is
illegal::

    mycolumn IN ()

To work around this, SQLAlchemy and other database libraries detect this
condition and render an alternative expression that evaluates to false, or
in the case of NOT IN, to true, based on the theory that "col IN ()" is always
false since nothing is in "the empty set".    Typically, in order to
produce a false/true constant that is portable across databases and works
in the context of the WHERE clause, a simple tautology such as ``1 != 1`` is
used to evaluate to false and ``1 = 1`` to evaluate to true (a simple constant
"0" or "1" often does not work as the target of a WHERE clause).

SQLAlchemy in its early days began with this approach as well, but soon it
was theorized that the SQL expression ``column IN ()`` would not evaluate to
false if the "column" were NULL; instead, the expression would produce NULL,
since "NULL" means "unknown", and comparisons to NULL in SQL usually produce
NULL.

To simulate this result, SQLAlchemy changed from using ``1 != 1`` to
instead use th expression ``expr != expr`` for empty "IN" and ``expr = expr``
for empty "NOT IN"; that is, instead of using a fixed value we use the
actual left-hand side of the expression.  If the left-hand side of
the expression passed evaluates to NULL, then the comparison overall
also gets the NULL result instead of false or true.

Unfortunately, users eventually complained that this expression had a very
severe performance impact on some query planners.   At that point, a warning
was added when an empty IN expression was encountered, favoring that SQLAlchemy
continues to be "correct" and urging users to avoid code that generates empty
IN predicates in general, since typically they can be safely omitted.  However,
this is of course burdensome in the case of queries that are built up dynamically
from input variables, where an incoming set of values might be empty.

In recent months, the original assumptions of this decision have been
questioned.  The notion that the expression "NULL IN ()" should return NULL was
only theoretical, and could not be tested since databases don't support that
syntax.  However, as it turns out, you can in fact ask a relational database
what value it would return for "NULL IN ()" by simulating the empty set as
follows::

    SELECT NULL IN (SELECT 1 WHERE 1 != 1)

With the above test, we see that the databases themselves can't agree on
the answer.  Postgresql, considered by most to be the most "correct" database,
returns False; because even though "NULL" represents "unknown", the "empty set"
means nothing is present, including all unknown values.  On the
other hand, MySQL and MariaDB return NULL for the above expression, defaulting
to the more common behavior of "all comparisons to NULL return NULL".

SQLAlchemy's SQL architecture is more sophisticated than it was when this
design decision was first made, so we can now allow either behavior to
be invoked at SQL string compilation time.  Previously, the conversion to a
comparison expression were done at construction time, that is, the moment
the :meth:`.ColumnOperators.in_` or :meth:`.ColumnOperators.notin_` operators were invoked.
With the compilation-time behavior, the dialect itself can be instructed
to invoke either approach, that is, the "static" ``1 != 1`` comparison or the
"dynamic" ``expr != expr`` comparison.   The default has been **changed**
to be the "static" comparison, since this agrees with the behavior that
Postgresql would have in any case and this is also what the vast majority
of users prefer.   This will **change the result** of a query that is comparing
a null expression to the empty set, particularly one that is querying
for the negation ``where(~null_expr.in_([]))``, since this now evaluates to true
and not NULL.

The behavior can now be controlled using the flag
:paramref:`.create_engine.empty_in_strategy`, which defaults to the
``"static"`` setting, but may also be set to ``"dynamic"`` or
``"dynamic_warn"``, where the ``"dynamic_warn"`` setting is equivalent to the
previous behavior of emitting ``expr != expr`` as well as a performance
warning.   However, it is anticipated that most users will appreciate the
"static" default.

:ticket:`3907`

.. _change_3953:

Late-expanded IN parameter sets allow IN expressions with cached statements
---------------------------------------------------------------------------

Added a new kind of :func:`.bindparam` called "expanding".  This is
for use in ``IN`` expressions where the list of elements is rendered
into individual bound parameters at statement execution time, rather
than at statement compilation time.  This allows both a single bound
parameter name to be linked to an IN expression of multiple elements,
as well as allows query caching to be used with IN expressions.  The
new feature allows the related features of "select in" loading and
"polymorphic in" loading to make use of the baked query extension
to reduce call overhead::

    stmt = select([table]).where(
        table.c.col.in_(bindparam('foo', expanding=True))
    conn.execute(stmt, {"foo": [1, 2, 3]})

The feature should be regarded as **experimental** within the 1.2 series.


:ticket:`3953`

.. _change_1546:

Support for SQL Comments on Table, Column, includes DDL, reflection
-------------------------------------------------------------------

The Core receives support for string comments associated with tables
and columns.   These are specified via the :paramref:`.Table.comment` and
:paramref:`.Column.comment` arguments::

    Table(
        'my_table', metadata,
        Column('q', Integer, comment="the Q value"),
        comment="my Q table"
    )

Above, DDL will be rendered appropriately upon table create to associate
the above comments with the table/ column within the schema.  When
the above table is autoloaded or inspected with :meth:`.Inspector.get_columns`,
the comments are included.   The table comment is also available independently
using the :meth:`.Inspector.get_table_comment` method.

Current backend support includes MySQL, Postgresql, and Oracle.

:ticket:`1546`


.. _change_2694:

New "autoescape" option for startswith(), endswith()
----------------------------------------------------

The "autoescape" parameter is added to :meth:`.Operators.startswith`,
:meth:`.Operators.endswith`, :meth:`.Operators.contains`.  This parameter
does what "escape" does, except that it also automatically performs a search-
and-replace of any wildcard characters to be escaped by that character, as
these operators already add the wildcard expression on the outside of the
given value.

An expression such as::

    >>> column('x').startswith('total%score', autoescape='/')

Renders as::

    x LIKE :x_1 || '%%' ESCAPE '/'

Where the value of the parameter "x_1" is ``'total/%score'``.

:ticket:`2694`

Key Behavioral Changes - ORM
============================

.. _change_3740:

Percent signs in literal_column() now conditionally escaped
-----------------------------------------------------------

The :obj:`.literal_column` construct now escapes percent sign characters
conditionally, based on whether or not the DBAPI in use makes use of a
percent-sign-sensitive paramstyle or not (e.g. 'format' or 'pyformat').

Previously, it was not possible to produce a :obj:`.literal_column`
construct that stated a single percent sign::

    >>> from sqlalchemy import literal_column
    >>> print(literal_column('some%symbol'))
    some%%symbol

The percent sign is now unaffected for dialects that are not set to
use the 'format' or 'pyformat' paramstyles; dialects such most MySQL
dialects which do state one of these paramstyles will continue to escape
as is appropriate::

    >>> from sqlalchemy import literal_column
    >>> print(literal_column('some%symbol'))
    some%symbol
    >>> from sqlalchemy.dialects import mysql
    >>> print(literal_column('some%symbol').compile(dialect=mysql.dialect()))
    some%%symbol

As part of this change, the doubling that has been present when using
operators like :meth:`.ColumnOperators.contains`,
:meth:`.ColumnOperators.startswith` and :meth:`.ColumnOperators.endswith`
is also refined to only occur when appropriate.

:ticket:`3740`

.. _change_3934:

The after_rollback() Session event now emits before the expiration of objects
-----------------------------------------------------------------------------

The :meth:`.Session.after_rollback` event now has access to the attribute
state of objects before their state has been expired (e.g. the "snapshot
removal").  This allows the event to be consistent with the behavior
of the :meth:`.Session.after_commit` event which also emits before the
"snapshot" has been removed::

    sess = Session()

    user = sess.query(User).filter_by(name='x').first()

    @event.listens_for(sess, "after_rollback")
    def after_rollback(session):
        # 'user.name' is now present, assuming it was already
        # loaded.  previously this would raise upon trying
        # to emit a lazy load.
        print("user name: %s" % user.name)

    @event.listens_for(sess, "after_commit")
    def after_commit(session):
        # 'user.name' is present, assuming it was already
        # loaded.  this is the existing behavior.
        print("user name: %s" % user.name)

    if should_rollback:
        sess.rollback()
    else:
        sess.commit()

Note that the :class:`.Session` will still disallow SQL from being emitted
within this event; meaning that unloaded attributes will still not be
able to load within the scope of the event.

:ticket:`3934`

.. _change_3891:

Fixed issue involving single-table inheritance with ``select_from()``
---------------------------------------------------------------------

The :meth:`.Query.select_from` method now honors the single-table inheritance
column discriminator when generating SQL; previously, only the expressions
in the query column list would be taken into account.

Supposing ``Manager`` is a subclass of ``Employee``.  A query like the following::

    sess.query(Manager.id)

Would generate SQL as::

    SELECT employee.id FROM employee WHERE employee.type IN ('manager')

However, if ``Manager`` were only specified by :meth:`.Query.select_from`
and not in the columns list, the discriminator would not be added::

    sess.query(func.count(1)).select_from(Manager)

would generate::

    SELECT count(1) FROM employee

With the fix, :meth:`.Query.select_from` now works correctly and we get::

    SELECT count(1) FROM employee WHERE employee.type IN ('manager')

Applications that may have been working around this by supplying the
WHERE clause manually may need to be adjusted.

:ticket:`3891`

.. _change_3913:

Previous collection is no longer mutated upon replacement
---------------------------------------------------------

The ORM emits events whenever the members of a mapped collection change.
In the case of assigning a collection to an attribute that would replace
the previous collection, a side effect of this was that the collection
being replaced would also be mutated, which is misleading and unnecessary::

    >>> a1, a2, a3 = Address('a1'), Address('a2'), Address('a3')
    >>> user.addresses = [a1, a2]

    >>> previous_collection = user.addresses

    # replace the collection with a new one
    >>> user.addresses = [a2, a3]

    >>> previous_collection
    [Address('a1'), Address('a2')]

Above, prior to the change, the ``previous_collection`` would have had the
"a1" member removed, corresponding to the member that's no longer in the
new collection.

:ticket:`3913`

.. _change_3896_validates:

A @validates method receives all values on bulk-collection set before comparison
--------------------------------------------------------------------------------

A method that uses ``@validates`` will now receive all members of a collection
during a "bulk set" operation, before comparison is applied against the
existing collection.

Given a mapping as::

    class A(Base):
        __tablename__ = 'a'
        id = Column(Integer, primary_key=True)
        bs = relationship("B")

        @validates('bs')
        def convert_dict_to_b(self, key, value):
            return B(data=value['data'])

    class B(Base):
        __tablename__ = 'b'
        id = Column(Integer, primary_key=True)
        a_id = Column(ForeignKey('a.id'))
        data = Column(String)

Above, we could use the validator as follows, to convert from an incoming
dictionary to an instance of ``B`` upon collection append::

    a1 = A()
    a1.bs.append({"data": "b1"})

However, a collection assignment would fail, since the ORM would assume
incoming objects are already instances of ``B`` as it attempts to compare  them
to the existing members of the collection, before doing collection appends
which actually invoke the validator.  This would make it impossible for bulk
set operations to accomodate non-ORM objects like dictionaries that needed
up-front modification::

    a1 = A()
    a1.bs = [{"data": "b1"}]

The new logic uses the new :meth:`.AttributeEvents.bulk_replace` event to ensure
that all values are sent to the ``@validates`` function up front.

As part of this change, this means that validators will now receive
**all** members of a collection upon bulk set, not just the members that
are new.   Supposing a simple validator such as::

    class A(Base):
        # ...

        @validates('bs')
        def validate_b(self, key, value):
            assert value.data is not None
            return value

Above, if we began with a collection as::

    a1 = A()

    b1, b2 = B(data="one"), B(data="two")
    a1.bs = [b1, b2]

And then, replaced the collection with one that overlaps the first::

    b3 = B(data="three")
    a1.bs = [b2, b3]

Previously, the second assignment would trigger the ``A.validate_b``
method only once, for the ``b3`` object.  The ``b2`` object would be seen
as being already present in the collection and not validated.  With the new
behavior, both ``b2`` and ``b3`` are passed to ``A.validate_b`` before passing
onto the collection.   It is thus important that valiation methods employ
idempotent behavior to suit such a case.

.. seealso::

    :ref:`change_3896_event`

:ticket:`3896`

.. _change_3753:

Use flag_dirty() to mark an object as "dirty" without any attribute changing
----------------------------------------------------------------------------

An exception is now raised if the :func:`.attributes.flag_modified` function
is used to mark an attribute as modified that isn't actually loaded::

    a1 = A(data='adf')
    s.add(a1)

    s.flush()

    # expire, similarly as though we said s.commit()
    s.expire(a1, 'data')

    # will raise InvalidRequestError
    attributes.flag_modified(a1, 'data')

This because the flush process will most likely fail in any case if the
attribute remains un-present by the time flush occurs.    To mark an object
as "modified" without referring to any attribute specifically, so that it
is considered within the flush process for the purpose of custom event handlers
such as :meth:`.SessionEvents.before_flush`, use the new
:func:`.attributes.flag_dirty` function::

    from sqlalchemy.orm import attributes

    attributes.flag_dirty(a1)

:ticket:`3753`

Key Behavioral Changes - Core
=============================


.. _change_3785:

The column-level COLLATE keyword now quotes the collation name
--------------------------------------------------------------

A bug in the :func:`.expression.collate` and :meth:`.ColumnOperators.collate`
functions, used to supply ad-hoc column collations at the statement level,
is fixed, where a case sensitive name would not be quoted::

    stmt = select([mytable.c.x, mytable.c.y]).\
        order_by(mytable.c.somecolumn.collate("fr_FR"))

now renders::

    SELECT mytable.x, mytable.y,
    FROM mytable ORDER BY mytable.somecolumn COLLATE "fr_FR"

Previously, the case sensitive name `"fr_FR"` would not be quoted.   Currently,
manual quoting of the "fr_FR" name is **not** detected, so applications that
are manually quoting the identifier should be adjusted.   Note that this change
does not impact the use of collations at the type level (e.g. specified
on the datatype like :class:`.String` at the table level), where quoting
is already applied.

:ticket:`3785`

Dialect Improvements and Changes - PostgreSQL
=============================================

.. _change_3959:

Support for fields specification in INTERVAL, including full reflection
-----------------------------------------------------------------------

The "fields" specifier in Postgresql's INTERVAL datatype allows specification
of which fields of the interval to store, including such values as "YEAR",
"MONTH", "YEAR TO MONTH", etc.   The :class:`.postgresql.INTERVAL` datatype
now allows these values to be specified::

    from sqlalchemy.dialects.postgresql import INTERVAL

    Table(
        'my_table', metadata,
        Column("some_interval", INTERVAL(fields="DAY TO SECOND"))
    )

Additionally, all INTERVAL datatypes can now be reflected independently
of the "fields" specifier present; the "fields" parameter in the datatype
itself will also be present::

    >>> inspect(engine).get_columns("my_table")
    [{'comment': None,
      'name': u'some_interval', 'nullable': True,
      'default': None, 'autoincrement': False,
      'type': INTERVAL(fields=u'day to second')}]

:ticket:`3959`

Dialect Improvements and Changes - MySQL
========================================

Dialect Improvements and Changes - SQLite
=========================================

Dialect Improvements and Changes - Oracle
=========================================

.. _change_3276:

Oracle foreign key constraint names are now "name normalized"
-------------------------------------------------------------

The names of foreign key constraints as delivered to a
:class:`.ForeignKeyConstraint` object during table reflection as well as
within the :meth:`.Inspector.get_foreign_keys` method will now be
"name normalized", that is, expressed as lower case for a case insensitive
name, rather than the raw UPPERCASE format that Oracle uses::

    >>> insp.get_indexes("addresses")
    [{'unique': False, 'column_names': [u'user_id'],
      'name': u'address_idx', 'dialect_options': {}}]

    >>> insp.get_pk_constraint("addresses")
    {'name': u'pk_cons', 'constrained_columns': [u'id']}

    >>> insp.get_foreign_keys("addresses")
    [{'referred_table': u'users', 'referred_columns': [u'id'],
      'referred_schema': None, 'name': u'user_id_fk',
      'constrained_columns': [u'user_id']}]

Previously, the foreign keys result would look like::

    [{'referred_table': u'users', 'referred_columns': [u'id'],
      'referred_schema': None, 'name': 'USER_ID_FK',
      'constrained_columns': [u'user_id']}]

Where the above could create problems particularly with Alembic autogenerate.

:ticket:`3276`


Dialect Improvements and Changes - SQL Server
=============================================

.. _change_2626:

SQL Server schema names with embedded dots supported
----------------------------------------------------

The SQL Server dialect has a behavior such that a schema name with a dot inside
of it is assumed to be a "database"."owner" identifier pair, which is
necessarily split up into these separate components during table and component
reflection operations, as well as when rendering quoting for the schema name so
that the two symbols are quoted separately.  The schema argument can
now be passed using brackets to manually specify where this split
occurs, allowing database and/or owner names that themselves contain one
or more dots::

    Table(
        "some_table", metadata,
        Column("q", String(50)),
        schema="[MyDataBase.dbo]"
    )

The above table will consider the "owner" to be ``MyDataBase.dbo``, which
will also be quoted upon render, and the "database" as None.  To individually
refer to database name and owner, use two pairs of brackets::

    Table(
        "some_table", metadata,
        Column("q", String(50)),
        schema="[MyDataBase.SomeDB].[MyDB.owner]"
    )

Additionally, the :class:`.quoted_name` construct is now honored when
passed to "schema" by the SQL Server dialect; the given symbol will
not be split on the dot if the quote flag is True and will be interpreted
as the "owner".

.. seealso::

    :ref:`multipart_schema_names`

:ticket:`2626`
