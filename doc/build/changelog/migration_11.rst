==============================
What's New in SQLAlchemy 1.1?
==============================

.. admonition:: About this Document

    This document describes changes between SQLAlchemy version 1.0,
    at the moment the current release series of SQLAlchemy,
    and SQLAlchemy version 1.1, which is the current development
    series of SQLAlchemy.

    As the 1.1 series is under development, issues that are targeted
    at this series can be seen under the
    `1.1 milestone <https://bitbucket.org/zzzeek/sqlalchemy/issues?milestone=1.1>`_.
    Please note that the set of issues within the milestone is not fixed;
    some issues may be moved to later milestones in order to allow
    for a timely release.

    Document last updated: March 23, 2016

Introduction
============

This guide introduces what's new in SQLAlchemy version 1.1,
and also documents changes which affect users migrating
their applications from the 1.0 series of SQLAlchemy to 1.1.

Please carefully review the sections on behavioral changes for
potentially backwards-incompatible changes in behavior.

Platform / Installer Changes
============================

Setuptools is now required for install
--------------------------------------

SQLAlchemy's ``setup.py`` file has for many years supported operation
both with Setuptools installed and without; supporting a "fallback" mode
that uses straight Distutils.  As a Setuptools-less Python environment is
now unheard of, and in order to support the featureset of Setuptools
more fully, in particular to support py.test's integration with it as well
as things like "extras", ``setup.py`` now depends on Setuptools fully.

.. seealso::

	:ref:`installation`

:ticket:`3489`

Enabling / Disabling C Extension builds is only via environment variable
------------------------------------------------------------------------

The C Extensions build by default during install as long as it is possible.
To disable C extension builds, the ``DISABLE_SQLALCHEMY_CEXT`` environment
variable was made available as of SQLAlchemy 0.8.6 / 0.9.4.  The previous
approach of using the ``--without-cextensions`` argument has been removed,
as it relies on deprecated features of setuptools.

.. seealso::

	:ref:`c_extensions`

:ticket:`3500`


New Features and Improvements - ORM
===================================

.. _change_2677:

New Session lifecycle events
----------------------------

The :class:`.Session` has long supported events that allow some degree
of tracking of state changes to objects, including
:meth:`.SessionEvents.before_attach`, :meth:`.SessionEvents.after_attach`,
and :meth:`.SessionEvents.before_flush`.  The Session documentation also
documents major object states at :ref:`session_object_states`.  However,
there has never been system of tracking objects specifically as they
pass through these transitions.  Additionally, the status of "deleted" objects
has historically been murky as the objects act somewhere between
the "persistent" and "detached" states.

To clean up this area and allow the realm of session state transition
to be fully transparent, a new series of events have been added that
are intended to cover every possible way that an object might transition
between states, and additionally the "deleted" status has been given
its own official state name within the realm of session object states.

New State Transition Events
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transitions between all states of an object such as :term:`persistent`,
:term:`pending` and others can now be intercepted in terms of a
session-level event intended to cover a specific transition.
Transitions as objects move into a :class:`.Session`, move out of a
:class:`.Session`, and even all the transitions which occur when the
transaction is rolled back using :meth:`.Session.rollback`
are explicitly present in the interface of :class:`.SessionEvents`.

In total, there are **ten new events**.  A summary of these events is in a
newly written documentation section :ref:`session_lifecycle_events`.


New Object State "deleted" is added, deleted objects no longer "persistent"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :term:`persistent` state of an object in the :class:`.Session` has
always been documented as an object that has a valid database identity;
however in the case of objects that were deleted within a flush, they
have always been in a grey area where they are not really "detached"
from the :class:`.Session` yet, because they can still be restored
within a rollback, but are not really "persistent" because their database
identity has been deleted and they aren't present in the identity map.

To resolve this grey area given the new events, a new object state
:term:`deleted` is introduced.  This state exists between the "persistent" and
"detached" states.  An object that is marked for deletion via
:meth:`.Session.delete` remains in the "persistent" state until a flush
proceeds; at that point, it is removed from the identity map, moves
to the "deleted" state, and the :meth:`.SessionEvents.persistent_to_deleted`
hook is invoked.  If the :class:`.Session` object's transaction is rolled
back, the object is restored as persistent; the
:meth:`.SessionEvents.deleted_to_persistent` transition is called.  Otherwise
if the :class:`.Session` object's transaction is committed,
the :meth:`.SessionEvents.deleted_to_detached` transition is invoked.

Additionally, the :attr:`.InstanceState.persistent` accessor **no longer returns
True** for an object that is in the new "deleted" state; instead, the
:attr:`.InstanceState.deleted` accessor has been enhanced to reliably
report on this new state.   When the object is detached, the :attr:`.InstanceState.deleted`
returns False and the :attr:`.InstanceState.detached` accessor is True
instead.  To determine if an object was deleted either in the current
transaction or in a previous transaction, use the
:attr:`.InstanceState.was_deleted` accessor.

Strong Identity Map is Deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the inspirations for the new series of transition events was to enable
leak-proof tracking of objects as they move in and out of the identity map,
so that a "strong reference" may be maintained mirroring the object
moving in and out of this map.  With this new capability, there is no longer
any need for the :paramref:`.Session.weak_identity_map` parameter and the
corresponding :class:`.StrongIdentityMap` object.  This option has remained
in SQLAlchemy for many years as the "strong-referencing" behavior used to be
the only behavior available, and many applications were written to assume
this behavior.   It has long been recommended that strong-reference tracking
of objects not be an intrinsic job of the :class:`.Session` and instead
be an application-level construct built as needed by the application; the
new event model allows even the exact behavior of the strong identity map
to be replicated.   See :ref:`session_referencing_behavior` for a new
recipe illustrating how to replace the strong identity map.

:ticket:`2677`

.. _change_3499:

Changes regarding "unhashable" types
------------------------------------

The :class:`.Query` object has a well-known behavior of "deduping"
returned rows that contain at least one ORM-mapped entity (e.g., a
full mapped object, as opposed to individual column values). The
primary purpose of this is so that the handling of entities works
smoothly in conjunction with the identity map, including to
accommodate for the duplicate entities normally represented within
joined eager loading, as well as when joins are used for the purposes
of filtering on additional columns.

This deduplication relies upon the hashability of the elements within
the row.  With the introduction of Postgresql's special types like
:class:`.postgresql.ARRAY`, :class:`.postgresql.HSTORE` and
:class:`.postgresql.JSON`, the experience of types within rows being
unhashable and encountering problems here is more prevalent than
it was previously.

In fact, SQLAlchemy has since version 0.8 included a flag on datatypes that
are noted as "unhashable", however this flag was not used consistently
on built in types.  As described in :ref:`change_3499_postgresql`, this
flag is now set consistently for all of Postgresql's "structural" types.

The "unhashable" flag is also set on the :class:`.NullType` type,
as :class:`.NullType` is used to refer to any expression of unknown
type.

Additionally, the treatment of a so-called "unhashable" type is slightly
different than it's been in previous releases; internally we are using
the ``id()`` function to get a "hash value" from these structures, just
as we would any ordinary mapped object.   This replaces the previous
approach which applied a counter to the object.

:ticket:`3499`

.. _change_3321:

Specific checks added for passing mapped classes, instances as SQL literals
---------------------------------------------------------------------------

The typing system now has specific checks for passing of SQLAlchemy
"inspectable" objects in contexts where they would otherwise be handled as
literal values.   Any SQLAlchemy built-in object that is legal to pass as a
SQL value includes a method ``__clause_element__()`` which provides a
valid SQL expression for that object.  For SQLAlchemy objects that
don't provide this, such as mapped classes, mappers, and mapped
instances, a more informative error message is emitted rather than
allowing the DBAPI to receive the object and fail later.  An example
is illustrated below, where a string-based attribute ``User.name`` is
compared to a full instance of ``User()``, rather than against a
string value::

    >>> some_user = User()
    >>> q = s.query(User).filter(User.name == some_user)
    ...
    sqlalchemy.exc.ArgumentError: Object <__main__.User object at 0x103167e90> is not legal as an SQL literal value

The exception is now immediate when the comparison is made between
``User.name == some_user``.  Previously, a comparison like the above
would produce an SQL expression that would only fail once resolved
into a DBAPI execution call; the mapped ``User`` object would
ultimately become a bound parameter that would be rejected by the
DBAPI.

Note that in the above example, the expression fails because
``User.name`` is a string-based (e.g. column oriented) attribute.
The change does *not* impact the usual case of comparing a many-to-one
relationship attribute to an object, which is handled distinctly::

    >>> # Address.user refers to the User mapper, so
    >>> # this is of course still OK!
    >>> q = s.query(Address).filter(Address.user == some_user)


:ticket:`3321`

.. _change_3250:

New options allowing explicit persistence of NULL over a default
----------------------------------------------------------------

Related to the new JSON-NULL support added to Postgresql as part of
:ref:`change_3514`, the base :class:`.TypeEngine` class now supports
a method :meth:`.TypeEngine.evaluates_none` which allows a positive set
of the ``None`` value on an attribute to be persisted as NULL, rather than
omitting the column from the INSERT statement, which has the effect of using
the column-level default.  This allows a mapper-level
configuration of the existing object-level technique of assigning
:func:`.sql.null` to the attribute.

.. seealso::

    :ref:`session_forcing_null`

:ticket:`3250`


.. _change_3582:

Further Fixes to single-table inheritance querying
--------------------------------------------------

Continuing from 1.0's :ref:`migration_3177`, the :class:`.Query` should
no longer inappropriately add the "single inheritance" criteria when the
query is against a subquery expression such as an exists::

    class Widget(Base):
        __tablename__ = 'widget'
        id = Column(Integer, primary_key=True)
        type = Column(String)
        data = Column(String)
        __mapper_args__ = {'polymorphic_on': type}


    class FooWidget(Widget):
        __mapper_args__ = {'polymorphic_identity': 'foo'}

    q = session.query(FooWidget).filter(FooWidget.data == 'bar').exists()

    session.query(q).all()

Produces::

    SELECT EXISTS (SELECT 1
    FROM widget
    WHERE widget.data = :data_1 AND widget.type IN (:type_1)) AS anon_1

The IN clause on the inside is appropriate, in order to limit to FooWidget
objects, however previously the IN clause would also be generated a second
time on the outside of the subquery.

:ticket:`3582`

.. _change_3680:

Improved Session state when a SAVEPOINT is cancelled by the database
--------------------------------------------------------------------

A common case with MySQL is that a SAVEPOINT is cancelled when a deadlock
occurs within the transaction.  The :class:`.Session` has been modfied
to deal with this failure mode slightly more gracefully, such that the
outer, non-savepoint transaction still remains usable::

    s = Session()
    s.begin_nested()

    s.add(SomeObject())

    try:
        # assume the flush fails, flush goes to rollback to the
        # savepoint and that also fails
        s.flush()
    except Exception as err:
        print("Something broke, and our SAVEPOINT vanished too")

    # this is the SAVEPOINT transaction, marked as
    # DEACTIVE so the rollback() call succeeds
    s.rollback()

    # this is the outermost transaction, remains ACTIVE
    # so rollback() or commit() can succeed
    s.rollback()

This issue is a continuation of :ticket:`2696` where we emit a warning
so that the original error can be seen when running on Python 2, even though
the SAVEPOINT exception takes precedence.  On Python 3, exceptions are chained
so both failures are reported individually.


:ticket:`3680`

.. _change_3677:

Erroneous "new instance X conflicts with persistent instance Y" flush errors fixed
----------------------------------------------------------------------------------

The :meth:`.Session.rollback` method is responsible for removing objects
that were INSERTed into the database, e.g. moved from pending to persistent,
within that now rolled-back transaction.   Objects that make this state
change are tracked in a weak-referencing collection, and if an object is
garbage collected from that collection, the :class:`.Session` no longer worries
about it (it would otherwise not scale for operations that insert many new
objects within a transaction).  However, an issue arises if the application
re-loads that same garbage-collected row within the transaction, before the
rollback occurs; if a strong reference to this object remains into the next
transaction, the fact that this object was not inserted and should be
removed would be lost, and the flush would incorrectly raise an error::

    from sqlalchemy import Column, create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class A(Base):
        __tablename__ = 'a'
        id = Column(Integer, primary_key=True)

    e = create_engine("sqlite://", echo=True)
    Base.metadata.create_all(e)

    s = Session(e)

    # persist an object
    s.add(A(id=1))
    s.flush()

    # rollback buffer loses reference to A

    # load it again, rollback buffer knows nothing
    # about it
    a1 = s.query(A).first()

    # roll back the transaction; all state is expired but the
    # "a1" reference remains
    s.rollback()

    # previous "a1" conflicts with the new one because we aren't
    # checking that it never got committed
    s.add(A(id=1))
    s.commit()

The above program would raise::

    FlushError: New instance <User at 0x7f0287eca4d0> with identity key
    (<class 'test.orm.test_transaction.User'>, ('u1',)) conflicts
    with persistent instance <User at 0x7f02889c70d0>

The bug is that when the above exception is raised, the unit of work
is operating upon the original object assuming it's a live row, when in
fact the object is expired and upon testing reveals that it's gone.  The
fix tests this condition now, so in the SQL log we see:

.. sourcecode:: sql

    BEGIN (implicit)

    INSERT INTO a (id) VALUES (?)
    (1,)

    SELECT a.id AS a_id FROM a LIMIT ? OFFSET ?
    (1, 0)

    ROLLBACK

    BEGIN (implicit)

    SELECT a.id AS a_id FROM a WHERE a.id = ?
    (1,)

    INSERT INTO a (id) VALUES (?)
    (1,)

    COMMIT

Above, the unit of work now does a SELECT for the row we're about to report
as a conflict for, sees that it doesn't exist, and proceeds normally.
The expense of this SELECT is only incurred in the case when we would have
erroneously raised an exception in any case.


:ticket:`3677`

.. _change_2349:

passive_deletes feature for joined-inheritance mappings
-------------------------------------------------------

A joined-table inheritance mapping may now allow a DELETE to proceed
as a result of :meth:`.Session.delete`, which only emits DELETE for the
base table, and not the subclass table, allowing configured ON DELETE CASCADE
to take place for the configured foreign keys.  This is configured using
the :paramref:`.orm.mapper.passive_deletes` option::

    from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()


    class A(Base):
        __tablename__ = "a"
        id = Column('id', Integer, primary_key=True)
        type = Column(String)

        __mapper_args__ = {
            'polymorphic_on': type,
            'polymorphic_identity': 'a',
            'passive_deletes': True
        }


    class B(A):
        __tablename__ = 'b'
        b_table_id = Column('b_table_id', Integer, primary_key=True)
        bid = Column('bid', Integer, ForeignKey('a.id', ondelete="CASCADE"))
        data = Column('data', String)

        __mapper_args__ = {
            'polymorphic_identity': 'b'
        }

With the above mapping, the :paramref:`.orm.mapper.passive_deletes` option
is configured on the base mapper; it takes effect for all non-base mappers
that are descendants of the mapper with the option set.  A DELETE for
an object of type ``B`` no longer needs to retrieve the primary key value
of ``b_table_id`` if unloaded, nor does it need to emit a DELETE statement
for the table itself::

    session.delete(some_b)
    session.commit()

Will emit SQL as::

    DELETE FROM a WHERE a.id = %(id)s
    {'id': 1}
    COMMIT

As always, the target database must have foreign key support with
ON DELETE CASCADE enabled.

:ticket:`2349`

.. _change_3630:

Same-named backrefs will not raise an error when applied to concrete inheritance subclasses
-------------------------------------------------------------------------------------------

The following mapping has always been possible without issue::

    class A(Base):
        __tablename__ = 'a'
        id = Column(Integer, primary_key=True)
        b = relationship("B", foreign_keys="B.a_id", backref="a")

    class A1(A):
        __tablename__ = 'a1'
        id = Column(Integer, primary_key=True)
        b = relationship("B", foreign_keys="B.a1_id", backref="a1")
        __mapper_args__ = {'concrete': True}

    class B(Base):
        __tablename__ = 'b'
        id = Column(Integer, primary_key=True)

        a_id = Column(ForeignKey('a.id'))
        a1_id = Column(ForeignKey('a1.id'))

Above, even though class ``A`` and class ``A1`` have a relationship
named ``b``, no conflict warning or error occurs because class ``A1`` is
marked as "concrete".

However, if the relationships were configured the other way, an error
would occur::

    class A(Base):
        __tablename__ = 'a'
        id = Column(Integer, primary_key=True)


    class A1(A):
        __tablename__ = 'a1'
        id = Column(Integer, primary_key=True)
        __mapper_args__ = {'concrete': True}


    class B(Base):
        __tablename__ = 'b'
        id = Column(Integer, primary_key=True)

        a_id = Column(ForeignKey('a.id'))
        a1_id = Column(ForeignKey('a1.id'))

        a = relationship("A", backref="b")
        a1 = relationship("A1", backref="b")

The fix enhances the backref feature so that an error is not emitted,
as well as an additional check within the mapper logic to bypass warning
for an attribute being replaced.

:ticket:`3630`

.. _change_3653:

Hybrid properties and methods now propagate the docstring as well as .info
--------------------------------------------------------------------------

A hybrid method or property will now reflect the ``__doc__`` value
present in the original docstring::

    class A(Base):
        __tablename__ = 'a'
        id = Column(Integer, primary_key=True)

        name = Column(String)

        @hybrid_property
        def some_name(self):
            """The name field"""
            return self.name

The above value of ``A.some_name.__doc__`` is now honored::

    >>> A.some_name.__doc__
    The name field

However, to accomplish this, the mechanics of hybrid properties necessarily
becomes more complex.  Previously, the class-level accessor for a hybrid
would be a simple pass-thru, that is, this test would succeed::

    >>> assert A.name is A.some_name

With the change, the expression returned by ``A.some_name`` is wrapped inside
of its own ``QueryableAttribute`` wrapper::

    >>> A.some_name
    <sqlalchemy.orm.attributes.hybrid_propertyProxy object at 0x7fde03888230>

A lot of testing went into making sure this wrapper works correctly, including
for elaborate schemes like that of the
`Custom Value Object <http://techspot.zzzeek.org/2011/10/21/hybrids-and-value-agnostic-types/>`_
recipe, however we'll be looking to see that no other regressions occur for
users.

As part of this change, the :attr:`.hybrid_property.info` collection is now
also propagated from the hybrid descriptor itself, rather than from the underlying
expression.  That is, accessing ``A.some_name.info`` now returns the same
dictionary that you'd get from ``inspect(A).all_orm_descriptors['some_name'].info``::

    >>> A.some_name.info['foo'] = 'bar'
    >>> from sqlalchemy import inspect
    >>> inspect(A).all_orm_descriptors['some_name'].info
    {'foo': 'bar'}

Note that this ``.info`` dictionary is **separate** from that of a mapped attribute
which the hybrid descriptor may be proxying directly; this is a behavioral
change from 1.0.   The wrapper will still proxy other useful attributes
of a mirrored attribute such as :attr:`.QueryableAttribute.property` and
:attr:`.QueryableAttribute.class_`.

:ticket:`3653`

.. _change_3601:

Session.merge resolves pending conflicts the same as persistent
---------------------------------------------------------------

The :meth:`.Session.merge` method will now track the identities of objects given
within a graph to maintain primary key uniqueness before emitting an INSERT.
When duplicate objects of the same identity are encountered, non-primary-key
attributes are **overwritten** as the objects are encountered, which is
essentially non-deterministic.   This behavior matches that of how persistent
objects, that is objects that are already located in the database via
primary key, are already treated, so this behavior is more internally
consistent.

Given::

    u1 = User(id=7, name='x')
    u1.orders = [
        Order(description='o1', address=Address(id=1, email_address='a')),
        Order(description='o2', address=Address(id=1, email_address='b')),
        Order(description='o3', address=Address(id=1, email_address='c'))
    ]

    sess = Session()
    sess.merge(u1)

Above, we merge a ``User`` object with three new ``Order`` objects, each referring to
a distinct ``Address`` object, however each is given the same primary key.
The current behavior of :meth:`.Session.merge` is to look in the identity
map for this ``Address`` object, and use that as the target.   If the object
is present, meaning that the database already has a row for ``Address`` with
primary key "1", we can see that the ``email_address`` field of the ``Address``
will be overwritten three times, in this case with the values a, b and finally
c.

However, if the ``Address`` row for primary key "1" were not present, :meth:`.Session.merge`
would instead create three separate ``Address`` instances, and we'd then get
a primary key conflict upon INSERT.  The new behavior is that the proposed
primary key for these ``Address`` objects are tracked in a separate dictionary
so that we merge the state of the three proposed ``Address`` objects onto
one ``Address`` object to be inserted.

It may have been preferable if the original case emitted some kind of warning
that conflicting data were present in a single merge-tree, however the
non-deterministic merging of values has been the behavior for many
years for the persistent case; it now matches for the pending case.   A
feature that warns for conflicting values could still be feasible for both
cases but would add considerable performance overhead as each column value
would have to be compared during the merge.


:ticket:`3601`

.. _change_3662:

Improvements to the Query.correlate method with polymoprhic entities
--------------------------------------------------------------------

In recent SQLAlchemy versions, the SQL generated by many forms of
"polymorphic" queries has a more "flat" form than it used to, where
a JOIN of several tables is no longer bundled into a subquery unconditionally.
To accommodate this, the :meth:`.Query.correlate` method now extracts the
individual tables from such a polymorphic selectable and ensures that all
are part of the "correlate" for the subquery.  Assuming the
``Person/Manager/Engineer->Company`` setup from the mapping documentation,
using with_polymorphic::

    sess.query(Person.name)
                .filter(
                    sess.query(Company.name).
                    filter(Company.company_id == Person.company_id).
                    correlate(Person).as_scalar() == "Elbonia, Inc.")

The above query now produces::

    SELECT people.name AS people_name
    FROM people
    LEFT OUTER JOIN engineers ON people.person_id = engineers.person_id
    LEFT OUTER JOIN managers ON people.person_id = managers.person_id
    WHERE (SELECT companies.name
    FROM companies
    WHERE companies.company_id = people.company_id) = ?

Before the fix, the call to ``correlate(Person)`` would inadvertently
attempt to correlate to the join of ``Person``, ``Engineer`` and ``Manager``
as a single unit, so ``Person`` wouldn't be correlated::

    -- old, incorrect query
    SELECT people.name AS people_name
    FROM people
    LEFT OUTER JOIN engineers ON people.person_id = engineers.person_id
    LEFT OUTER JOIN managers ON people.person_id = managers.person_id
    WHERE (SELECT companies.name
    FROM companies, people
    WHERE companies.company_id = people.company_id) = ?

Using correlated subqueries against polymorphic mappings still has some
unpolished edges.  If for example ``Person`` is polymorphically linked
to a so-called "concrete polymorphic union" query, the above subquery
may not correctly refer to this subquery.  In all cases, a way to refer
to the "polyorphic" entity fully is to create an :func:`.aliased` object
from it first::

    # works with all SQLAlchemy versions and all types of polymorphic
    # aliasing.

    paliased = aliased(Person)
    sess.query(paliased.name)
                .filter(
                    sess.query(Company.name).
                    filter(Company.company_id == paliased.company_id).
                    correlate(paliased).as_scalar() == "Elbonia, Inc.")

The :func:`.aliased` construct guarantees that the "polymorphic selectable"
is wrapped in a subquery.  By referring to it explicitly in the correlated
subquery, the polymorphic form is correctly used.

:ticket:`3662`

.. _change_3081:

Stringify of Query will consult the Session for the correct dialect
-------------------------------------------------------------------

Calling ``str()`` on a :class:`.Query` object will consult the :class:`.Session`
for the correct "bind" to use, in order to render the SQL that would be
passed to the database.  In particular this allows a :class:`.Query` that
refers to dialect-specific SQL constructs to be renderable, assuming the
:class:`.Query` is associated with an appropriate :class:`.Session`.
Previously, this behavior would only take effect if the :class:`.MetaData`
to which the mappings were associated were itself bound to the target
:class:`.Engine`.

If neither the underlying :class:`.MetaData` nor the :class:`.Session` are
associated with any bound :class:`.Engine`, then the fallback to the
"default" dialect is used to generate the SQL string.

.. seealso::

    :ref:`change_3631`

:ticket:`3081`

.. _change_3431:

Joined eager loading where the same entity is present multiple times in one row
-------------------------------------------------------------------------------

A fix has been made to the case has been made whereby an attribute will be
loaded via joined eager loading, even if the entity was already loaded from the
row on a different "path" that doesn't include the attribute.  This is a
deep use case that's hard to reproduce, but the general idea is as follows::

    class A(Base):
        __tablename__ = 'a'
        id = Column(Integer, primary_key=True)
        b_id = Column(ForeignKey('b.id'))
        c_id = Column(ForeignKey('c.id'))

        b = relationship("B")
        c = relationship("C")


    class B(Base):
        __tablename__ = 'b'
        id = Column(Integer, primary_key=True)
        c_id = Column(ForeignKey('c.id'))

        c = relationship("C")


    class C(Base):
        __tablename__ = 'c'
        id = Column(Integer, primary_key=True)
        d_id = Column(ForeignKey('d.id'))
        d = relationship("D")


    class D(Base):
        __tablename__ = 'd'
        id = Column(Integer, primary_key=True)


    c_alias_1 = aliased(C)
    c_alias_2 = aliased(C)

    q = s.query(A)
    q = q.join(A.b).join(c_alias_1, B.c).join(c_alias_1.d)
    q = q.options(contains_eager(A.b).contains_eager(B.c, alias=c_alias_1).contains_eager(C.d))
    q = q.join(c_alias_2, A.c)
    q = q.options(contains_eager(A.c, alias=c_alias_2))

The above query emits SQL like this::

    SELECT
        d.id AS d_id,
        c_1.id AS c_1_id, c_1.d_id AS c_1_d_id,
        b.id AS b_id, b.c_id AS b_c_id,
        c_2.id AS c_2_id, c_2.d_id AS c_2_d_id,
        a.id AS a_id, a.b_id AS a_b_id, a.c_id AS a_c_id
    FROM
        a
        JOIN b ON b.id = a.b_id
        JOIN c AS c_1 ON c_1.id = b.c_id
        JOIN d ON d.id = c_1.d_id
        JOIN c AS c_2 ON c_2.id = a.c_id

We can see that the ``c`` table is selected from twice; once in the context
of ``A.b.c -> c_alias_1`` and another in the context of ``A.c -> c_alias_2``.
Also, we can see that it is quite possible that the ``C`` identity for a
single row is the **same** for both ``c_alias_1`` and ``c_alias_2``, meaning
two sets of columns in one row result in only one new object being added
to the identity map.

The query options above only call for the attribute ``C.d`` to be loaded
in the context of ``c_alias_1``, and not ``c_alias_2``.  So whether or not
the final ``C`` object we get in the identity map has the ``C.d`` attribute
loaded depends on how the mappings are traversed, which while not completely
random, is essentially non-deterministic.   The fix is that even if the
loader for ``c_alias_1`` is processed after that of ``c_alias_2`` for a
single row where they both refer to the same identity, the ``C.d``
element will still be loaded.  Previously, the loader did not seek to
modify the load of an entity that was already loaded via a different path.
The loader that reaches the entity first has always been non-deterministic,
so this fix may be detectable as a behavioral change in some situations and
not others.

The fix includes tests for two variants of the "multiple paths to one entity"
case, and the fix should hopefully cover all other scenarios of this nature.

:ticket:`3431`

.. _change_3641:

Columns no longer added redundantly with DISTINCT + ORDER BY
------------------------------------------------------------

A query such as the following will now augment only those columns
that are missing from the SELECT list, without duplicates::

    q = session.query(User.id, User.name.label('name')).\
        distinct().\
        order_by(User.id, User.name, User.fullname)

Produces::

    SELECT DISTINCT user.id AS a_id, user.name AS name,
     user.fullname AS a_fullname
    FROM a ORDER BY user.id, user.name, user.fullname

Previously, it would produce::

    SELECT DISTINCT user.id AS a_id, user.name AS name, user.name AS a_name,
      user.fullname AS a_fullname
    FROM a ORDER BY user.id, user.name, user.fullname

Where above, the ``user.name`` column is added unnecessarily.  The results
would not be affected, as the additional columns are not included in the
result in any case, but the columns are unnecessary.

Additionally, when the Postgresql DISTINCT ON format is used by passing
expressions to :meth:`.Query.distinct`, the above "column adding" logic
is disabled entirely.

When the query is being bundled into a subquery for the purposes of
joined eager loading, the "augment column list" rules are are necessarily
more aggressive so that the ORDER BY can still be satisifed, so this case
remains unchanged.

:ticket:`3641`

New MutableList and MutableSet helpers added to the mutation tracking extension
-------------------------------------------------------------------------------

New helper classes :class:`.MutableList` and :class:`.MutableSet` have been
added to the :ref:`mutable_toplevel` extension, to complement the existing
:class:`.MutableDict` helper.

:ticket:`3297`

.. _change_3512:

New "raise" loader strategy
---------------------------

To assist with the use case of preventing unwanted lazy loads from occurring
after a series of objects are loaded, the new "lazy='raise'" strategy and
corresponding loader option :func:`.orm.raiseload` may be applied to a
relationship attribute which will cause it to raise ``InvalidRequestError``
when a non-eagerly-loaded attribute is accessed for read::

    >>> from sqlalchemy.orm import raiseload
    >>> a1 = s.query(A).options(raiseload(A.bs)).first()
    >>> a1.bs
    Traceback (most recent call last):
    ...
    sqlalchemy.exc.InvalidRequestError: 'A.bs' is not available due to lazy='raise'

:ticket:`3512`

.. _change_3394:

Mapper.order_by is deprecated
-----------------------------

This old parameter from the very first versions of SQLAlchemy was part of
the original design of the ORM which featured the :class:`.Mapper` object
as a public-facing query structure.   This role has long since been replaced
by the :class:`.Query` object, where we use :meth:`.Query.order_by` to
indicate the ordering of results in a way that works consistently for any
combination of SELECT statements, entities and SQL expressions.   There are
many areas in which :paramref:`.Mapper.order_by` doesn't work as expected
(or what would be expected is not clear), such as when queries are combined
into unions; these cases are not supported.


:ticket:`3394`

New Features and Improvements - Core
====================================

.. _change_2551:

CTE Support for INSERT, UPDATE, DELETE
--------------------------------------

One of the most widely requested features is support for common table
expressions (CTE) that work with INSERT, UPDATE, DELETE, and is now implemented.
An INSERT/UPDATE/DELETE can both draw from a WITH clause that's stated at the
top of the SQL, as well as can be used as a CTE itself in the context of
a larger statement.

As part of this change, an INSERT from SELECT that includes a CTE will now
render the CTE at the top of the entire statement, rather than nested
in the SELECT statement as was the case in 1.0.

Below is an example that renders UPDATE, INSERT and SELECT all in one
statement::

    >>> from sqlalchemy import table, column, select, literal, exists
    >>> orders = table(
    ...     'orders',
    ...     column('region'),
    ...     column('amount'),
    ...     column('product'),
    ...     column('quantity')
    ... )
    >>>
    >>> upsert = (
    ...     orders.update()
    ...     .where(orders.c.region == 'Region1')
    ...     .values(amount=1.0, product='Product1', quantity=1)
    ...     .returning(*(orders.c._all_columns)).cte('upsert'))
    >>>
    >>> insert = orders.insert().from_select(
    ...     orders.c.keys(),
    ...     select([
    ...         literal('Region1'), literal(1.0),
    ...         literal('Product1'), literal(1)
    ...     ]).where(~exists(upsert.select()))
    ... )
    >>>
    >>> print(insert)  # note formatting added for clarity
    WITH upsert AS
    (UPDATE orders SET amount=:amount, product=:product, quantity=:quantity
     WHERE orders.region = :region_1
     RETURNING orders.region, orders.amount, orders.product, orders.quantity
    )
    INSERT INTO orders (region, amount, product, quantity)
    SELECT
        :param_1 AS anon_1, :param_2 AS anon_2,
        :param_3 AS anon_3, :param_4 AS anon_4
    WHERE NOT (
        EXISTS (
            SELECT upsert.region, upsert.amount,
                   upsert.product, upsert.quantity
            FROM upsert))

:ticket:`2551`

.. _change_2857:

Support for the SQL LATERAL keyword
------------------------------------

The LATERAL keyword is currently known to only be supported by Postgresql 9.3
and greater, however as it is part of the SQL standard support for this keyword
is added to Core.   The implementation of :meth:`.Select.lateral` employs
special logic beyond just rendering the LATERAL keyword to allow for
correlation of tables that are derived from the same FROM clause as the
selectable, e.g. lateral correlation::

    >>> from sqlalchemy import table, column, select, true
    >>> people = table('people', column('people_id'), column('age'), column('name'))
    >>> books = table('books', column('book_id'), column('owner_id'))
    >>> subq = select([books.c.book_id]).\
    ...      where(books.c.owner_id == people.c.people_id).lateral("book_subq")
    >>> print(select([people]).select_from(people.join(subq, true())))
    SELECT people.people_id, people.age, people.name
    FROM people JOIN LATERAL (SELECT books.book_id AS book_id
    FROM books WHERE books.owner_id = people.people_id)
    AS book_subq ON true

.. seealso::

    :ref:`lateral_selects`

    :class:`.Lateral`

    :meth:`.Select.lateral`


:ticket:`2857`

.. _change_3216:

The ``.autoincrement`` directive is no longer implicitly enabled for a composite primary key column
---------------------------------------------------------------------------------------------------

SQLAlchemy has always had the convenience feature of enabling the backend database's
"autoincrement" feature for a single-column integer primary key; by "autoincrement"
we mean that the database column will include whatever DDL directives the
database provides in order to indicate an auto-incrementing integer identifier,
such as the SERIAL keyword on Postgresql or AUTO_INCREMENT on MySQL, and additionally
that the dialect will recieve these generated values from the execution
of a :meth:`.Table.insert` construct using techniques appropriate to that
backend.

What's changed is that this feature no longer turns on automatically for a
*composite* primary key; previously, a table definition such as::

    Table(
        'some_table', metadata,
        Column('x', Integer, primary_key=True),
        Column('y', Integer, primary_key=True)
    )

Would have "autoincrement" semantics applied to the ``'x'`` column, only
because it's first in the list of primary key columns.  In order to
disable this, one would have to turn off ``autoincrement`` on all columns::

    # old way
    Table(
        'some_table', metadata,
        Column('x', Integer, primary_key=True, autoincrement=False),
        Column('y', Integer, primary_key=True, autoincrement=False)
    )

With the new behavior, the composite primary key will not have autoincrement
semantics unless a column is marked explcitly with ``autoincrement=True``::

    # column 'y' will be SERIAL/AUTO_INCREMENT/ auto-generating
    Table(
        'some_table', metadata,
        Column('x', Integer, primary_key=True),
        Column('y', Integer, primary_key=True, autoincrement=True)
    )

In order to anticipate some potential backwards-incompatible scenarios,
the :meth:`.Table.insert` construct will perform more thorough checks
for missing primary key values on composite primary key columns that don't
have autoincrement set up; given a table such as::

    Table(
        'b', metadata,
        Column('x', Integer, primary_key=True),
        Column('y', Integer, primary_key=True)
    )

An INSERT emitted with no values for this table will produce the exception::

    CompileError: Column 'b.x' is marked as a member of the primary
    key for table 'b', but has no Python-side or server-side default
    generator indicated, nor does it indicate 'autoincrement=True',
    and no explicit value is passed.  Primary key columns may not
    store NULL. Note that as of SQLAlchemy 1.1, 'autoincrement=True'
    must be indicated explicitly for composite (e.g. multicolumn)
    primary keys if AUTO_INCREMENT/SERIAL/IDENTITY behavior is
    expected for one of the columns in the primary key. CREATE TABLE
    statements are impacted by this change as well on most backends.

For a column that is receiving primary key values from a server-side
default or something less common such as a trigger, the presence of a
value generator can be indicated using :class:`.FetchedValue`::

    Table(
        'b', metadata,
        Column('x', Integer, primary_key=True, server_default=FetchedValue()),
        Column('y', Integer, primary_key=True, server_default=FetchedValue())
    )

For the very unlikely case where a composite primary key is actually intended
to store NULL in one or more of its columns (only supported on SQLite and MySQL),
specify the column with ``nullable=True``::

    Table(
        'b', metadata,
        Column('x', Integer, primary_key=True),
        Column('y', Integer, primary_key=True, nullable=True)
    )

In a related change, the ``autoincrement`` flag may be set to True
on a column that has a client-side or server-side default.  This typically
will not have much impact on the behavior of the column during an INSERT.


.. seealso::

    :ref:`change_mysql_3216`

:ticket:`3216`

.. _change_1957:

Core and ORM support for FULL OUTER JOIN
----------------------------------------

The new flag :paramref:`.FromClause.outerjoin.full`, available at the Core
and ORM level, instructs the compiler to render ``FULL OUTER JOIN``
where it would normally render ``LEFT OUTER JOIN``::

    stmt = select([t1]).select_from(t1.outerjoin(t2, full=True))

The flag also works at the ORM level::

    q = session.query(MyClass).outerjoin(MyOtherClass, full=True)

:ticket:`1957`

.. _change_3501:

ResultSet column matching enhancements; positional column setup for textual SQL
-------------------------------------------------------------------------------

A series of improvements were made to the :class:`.ResultProxy` system
in the 1.0 series as part of :ticket:`918`, which reorganizes the internals
to match cursor-bound result columns with table/ORM metadata positionally,
rather than by matching names, for compiled SQL constructs that contain full
information about the result rows to be returned.   This allows a dramatic savings
on Python overhead as well as much greater accuracy in linking ORM and Core
SQL expressions to result rows.  In 1.1, this reorganization has been taken
further internally, and also has been made available to pure-text SQL
constructs via the use of the recently added :meth:`.TextClause.columns` method.

TextAsFrom.columns() now works positionally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :meth:`.TextClause.columns` method, added in 0.9, accepts column-based arguments
positionally; in 1.1, when all columns are passed positionally, the correlation
of these columns to the ultimate result set is also performed positionally.
The key advantage here is that textual SQL can now be linked to an ORM-
level result set without the need to deal with ambiguous or duplicate column
names, or with having to match labeling schemes to ORM-level labeling schemes.  All
that's needed now is the same ordering of columns within the textual SQL
and the column arguments passed to :meth:`.TextClause.columns`::


    from sqlalchemy import text
    stmt = text("SELECT users.id, addresses.id, users.id, "
         "users.name, addresses.email_address AS email "
         "FROM users JOIN addresses ON users.id=addresses.user_id "
         "WHERE users.id = 1").columns(
            User.id,
            Address.id,
            Address.user_id,
            User.name,
            Address.email_address
         )

    query = session.query(User).from_statement(text).\
        options(contains_eager(User.addresses))
    result = query.all()

Above, the textual SQL contains the column "id" three times, which would
normally be ambiguous.  Using the new feature, we can apply the mapped
columns from the ``User`` and ``Address`` class directly, even linking
the ``Address.user_id`` column to the ``users.id`` column in textual SQL
for fun, and the :class:`.Query` object will receive rows that are correctly
targetable as needed, including for an eager load.

This change is **backwards incompatible** with code that passes the columns
to the method with a different ordering than is present in the textual statement.
It is hoped that this impact will be low due to the fact that this
method has always been documented illustrating the columns being passed in the same order as that of the
textual SQL statement, as would seem intuitive, even though the internals
weren't checking for this.  The method itself was only added as of 0.9 in
any case and may not yet have widespread use.  Notes on exactly how to handle
this behavioral change for applications using it are at :ref:`behavior_change_3501`.

.. seealso::

    :ref:`sqlexpression_text_columns` - in the Core tutorial

    :ref:`behavior_change_3501` - backwards compatibility remarks

Positional matching is trusted over name-based matching for Core/ORM SQL constructs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Another aspect of this change is that the rules for matching columns have also been modified
to rely upon "positional" matching more fully for compiled SQL constructs
as well.   Given a statement like the following::

    ua = users.alias('ua')
    stmt = select([users.c.user_id, ua.c.user_id])

The above statement will compile to::

    SELECT users.user_id, ua.user_id FROM users, users AS ua

In 1.0, the above statement when executed would be matched to its original
compiled construct using positional matching, however because the statement
contains the ``'user_id'`` label duplicated, the "ambiguous column" rule
would still get involved and prevent the columns from being fetched from a row.
As of 1.1, the "ambiguous column" rule does not affect an exact match from
a column construct to the SQL column, which is what the ORM uses to
fetch columns::

    result = conn.execute(stmt)
    row = result.first()

    # these both match positionally, so no error
    user_id = row[users.c.user_id]
    ua_id = row[ua.c.user_id]

    # this still raises, however
    user_id = row['user_id']

Much less likely to get an "ambiguous column" error message
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As part of this change, the wording of the error message ``Ambiguous column
name '<name>' in result set! try 'use_labels' option on select statement.``
has been dialed back; as this message should now be extremely rare when using
the ORM or Core compiled SQL constructs, it merely states
``Ambiguous column name '<name>' in result set column descriptions``, and
only when a result column is retrieved using the string name that is actually
ambiguous, e.g. ``row['user_id']`` in the above example.  It also now refers
to the actual ambiguous name from the rendered SQL statement itself,
rather than indicating the key or name that was local to the construct being
used for the fetch.

:ticket:`3501`

.. _change_3292:

Support for Python's native ``enum`` type and compatible forms
---------------------------------------------------------------

The :class:`.Enum` type can now be constructed using any
PEP-435 compliant enumerated type.   When using this mode, input values
and return values are the actual enumerated objects, not the
string values::

    import enum
    from sqlalchemy import Table, MetaData, Column, Enum, create_engine


    class MyEnum(enum.Enum):
        one = "one"
        two = "two"
        three = "three"


    t = Table(
        'data', MetaData(),
        Column('value', Enum(MyEnum))
    )

    e = create_engine("sqlite://")
    t.create(e)

    e.execute(t.insert(), {"value": MyEnum.two})
    assert e.scalar(t.select()) is MyEnum.two


:ticket:`3292`

.. _change_gh_231:

Negative integer indexes accommodated by Core result rows
---------------------------------------------------------

The :class:`.RowProxy` object now accomodates single negative integer indexes
like a regular Python sequence, both in the pure Python and C-extension
version.  Previously, negative values would only work in slices::

    >>> from sqlalchemy import create_engine
    >>> e = create_engine("sqlite://")
    >>> row = e.execute("select 1, 2, 3").first()
    >>> row[-1], row[-2], row[1], row[-2:2]
    3 2 2 (2,)

.. _change_3095:

The ``Enum`` type now does in-Python validation of values
---------------------------------------------------------

To accomodate for Python native enumerated objects, as well as for edge
cases such as that of where a non-native ENUM type is used within an ARRAY
and a CHECK contraint is infeasible, the :class:`.Enum` datatype now adds
in-Python validation of input values::


    >>> from sqlalchemy import Table, MetaData, Column, Enum, create_engine
    >>> t = Table(
    ...     'data', MetaData(),
    ...     Column('value', Enum("one", "two", "three"))
    ... )
    >>> e = create_engine("sqlite://")
    >>> t.create(e)
    >>> e.execute(t.insert(), {"value": "four"})
    Traceback (most recent call last):
      ...
    sqlalchemy.exc.StatementError: (exceptions.LookupError)
    "four" is not among the defined enum values
    [SQL: u'INSERT INTO data (value) VALUES (?)']
    [parameters: [{'value': 'four'}]]

For simplicity and consistency, this validation is now turned on in all cases,
whether or not the enumerated type uses a database-native form, whether
or not the CHECK constraint is in use, as well as whether or not a
PEP-435 enumerated type or plain list of string values is used.  The
check also occurs on the result-handling side as well, when values coming
from the database are returned.

This validation is in addition to the existing behavior of creating a
CHECK constraint when a non-native enumerated type is used.  The creation of
this CHECK constraint can now be disabled using the new
:paramref:`.Enum.create_constraint` flag.

:ticket:`3095`

.. _change_2837:

Large parameter and row values are now truncated in logging and exception displays
----------------------------------------------------------------------------------

A large value present as a bound parameter for an SQL statement, as well as a
large value present in a result row, will now be truncated during display
within logging, exception reporting, as well as ``repr()`` of the row itself::

    >>> from sqlalchemy import create_engine
    >>> import random
    >>> e = create_engine("sqlite://", echo='debug')
    >>> some_value = ''.join(chr(random.randint(52, 85)) for i in range(5000))
    >>> row = e.execute("select ?", [some_value]).first()
    ... (lines are wrapped for clarity) ...
    2016-02-17 13:23:03,027 INFO sqlalchemy.engine.base.Engine select ?
    2016-02-17 13:23:03,027 INFO sqlalchemy.engine.base.Engine
    ('E6@?>9HPOJB<<BHR:@=TS:5ILU=;JLM<4?B9<S48PTNG9>:=TSTLA;9K;9FPM4M8M@;NM6GU
    LUAEBT9QGHNHTHR5EP75@OER4?SKC;D:TFUMD:M>;C6U:JLM6R67GEK<A6@S@C@J7>4=4:P
    GJ7HQ6 ... (4702 characters truncated) ... J6IK546AJMB4N6S9L;;9AKI;=RJP
    HDSSOTNBUEEC9@Q:RCL:I@5?FO<9K>KJAGAO@E6@A7JI8O:J7B69T6<8;F:S;4BEIJS9HM
    K:;5OLPM@JR;R:J6<SOTTT=>Q>7T@I::OTDC:CC<=NGP6C>BC8N',)
    2016-02-17 13:23:03,027 DEBUG sqlalchemy.engine.base.Engine Col ('?',)
    2016-02-17 13:23:03,027 DEBUG sqlalchemy.engine.base.Engine
    Row (u'E6@?>9HPOJB<<BHR:@=TS:5ILU=;JLM<4?B9<S48PTNG9>:=TSTLA;9K;9FPM4M8M@;
    NM6GULUAEBT9QGHNHTHR5EP75@OER4?SKC;D:TFUMD:M>;C6U:JLM6R67GEK<A6@S@C@J7
    >4=4:PGJ7HQ ... (4703 characters truncated) ... J6IK546AJMB4N6S9L;;9AKI;=
    RJPHDSSOTNBUEEC9@Q:RCL:I@5?FO<9K>KJAGAO@E6@A7JI8O:J7B69T6<8;F:S;4BEIJS9HM
    K:;5OLPM@JR;R:J6<SOTTT=>Q>7T@I::OTDC:CC<=NGP6C>BC8N',)
    >>> print(row)
    (u'E6@?>9HPOJB<<BHR:@=TS:5ILU=;JLM<4?B9<S48PTNG9>:=TSTLA;9K;9FPM4M8M@;NM6
    GULUAEBT9QGHNHTHR5EP75@OER4?SKC;D:TFUMD:M>;C6U:JLM6R67GEK<A6@S@C@J7>4
    =4:PGJ7HQ ... (4703 characters truncated) ... J6IK546AJMB4N6S9L;;9AKI;
    =RJPHDSSOTNBUEEC9@Q:RCL:I@5?FO<9K>KJAGAO@E6@A7JI8O:J7B69T6<8;F:S;4BEIJS9H
    MK:;5OLPM@JR;R:J6<SOTTT=>Q>7T@I::OTDC:CC<=NGP6C>BC8N',)


:ticket:`2837`

.. _change_2528:

A UNION or similar of SELECTs with LIMIT/OFFSET/ORDER BY now parenthesizes the embedded selects
-----------------------------------------------------------------------------------------------

An issue that, like others, was long driven by SQLite's lack of capabilities
has now been enhanced to work on all supporting backends.   We refer to a query that
is a UNION of SELECT statements that themselves contain row-limiting or ordering
features which include LIMIT, OFFSET, and/or ORDER BY::

    (SELECT x FROM table1 ORDER BY y LIMIT 1) UNION
    (SELECT x FROM table2 ORDER BY y LIMIT 2)

The above query requires parenthesis within each sub-select in order to
group the sub-results correctly.  Production of the above statement in
SQLAlchemy Core looks like::

    stmt1 = select([table1.c.x]).order_by(table1.c.y).limit(1)
    stmt2 = select([table1.c.x]).order_by(table2.c.y).limit(2)

    stmt = union(stmt1, stmt2)

Previously, the above construct would not produce parenthesization for the
inner SELECT statements, producing a query that fails on all backends.

The above formats will **continue to fail on SQLite**; additionally, the format
that includes ORDER BY but no LIMIT/SELECT will **continue to fail on Oracle**.
This is not a backwards-incompatible change, because the queries fail without
the parentheses as well; with the fix, the queries at least work on all other
databases.

In all cases, in order to produce a UNION of limited SELECT statements that
also works on SQLite and in all cases on Oracle, the
subqueries must be a SELECT of an ALIAS::

    stmt1 = select([table1.c.x]).order_by(table1.c.y).limit(1).alias().select()
    stmt2 = select([table2.c.x]).order_by(table2.c.y).limit(2).alias().select()

    stmt = union(stmt1, stmt2)

This workaround works on all SQLAlchemy versions.  In the ORM, it looks like::

    stmt1 = session.query(Model1).order_by(Model1.y).limit(1).subquery().select()
    stmt2 = session.query(Model2).order_by(Model2.y).limit(1).subquery().select()

    stmt = session.query(Model1).from_statement(stmt1.union(stmt2))

The behavior here has many parallels to the "join rewriting" behavior
introduced in SQLAlchemy 0.9 in :ref:`feature_joins_09`; however in this case
we have opted not to add new rewriting behavior to accommodate this
case for SQLite.
The existing rewriting behavior is very complicated already, and the case of
UNIONs with parenthesized SELECT statements is much less common than the
"right-nested-join" use case of that feature.

:ticket:`2528`

.. _change_3619:

JSON support added to Core
--------------------------

As MySQL now has a JSON datatype in addition to the Postgresql JSON datatype,
the core now gains a :class:`sqlalchemy.types.JSON` datatype that is the basis
for both of these.  Using this type allows access to the "getitem" operator
as well as the "getpath" operator in a way that is agnostic across Postgresql
and MySQL.

The new datatype also has a series of improvements to the handling of
NULL values as well as expression handling.

.. seealso::

    :ref:`change_3547`

    :class:`.types.JSON`

    :class:`.postgresql.JSON`

    :class:`.mysql.JSON`

:ticket:`3619`

.. _change_3514:

JSON "null" is inserted as expected with ORM operations, regardless of column default present
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`.types.JSON` type and its descendant types :class:`.postgresql.JSON`
and :class:`.mysql.JSON` have a flag :paramref:`.types.JSON.none_as_null` which
when set to True indicates that the Python value ``None`` should translate
into an SQL NULL rather than a JSON NULL value.  This flag defaults to False,
which means that the column should *never* insert SQL NULL or fall back
to a default unless the :func:`.null` constant were used.  However, this would
fail in the ORM under two circumstances; one is when the column also contained
a default or server_default value, a positive value of ``None`` on the mapped
attribute would still result in the column-level default being triggered,
replacing the ``None`` value::

    obj = MyObject(json_value=None)
    session.add(obj)
    session.commit()   # would fire off default / server_default, not encode "'none'"

The other is when the :meth:`.Session.bulk_insert_mappings`
method were used, ``None`` would be ignored in all cases::

    session.bulk_insert_mappings(
        MyObject,
        [{"json_value": None}])  # would insert SQL NULL and/or trigger defaults

The :class:`.types.JSON` type now implements the
:attr:`.TypeEngine.should_evaluate_none` flag,
indicating that ``None`` should not be ignored here; it is configured
automatically based on the value of :paramref:`.types.JSON.none_as_null`.
Thanks to :ticket:`3061`, we can differentiate when the value ``None`` is actively
set by the user versus when it was never set at all.

If the attribute is not set at all, then column level defaults *will*
fire off and/or SQL NULL will be inserted as expected, as was the behavior
previously.  Below, the two variants are illustrated::

    obj = MyObject(json_value=None)
    session.add(obj)
    session.commit()   # *will not* fire off column defaults, will insert JSON 'null'

    obj = MyObject()
    session.add(obj)
    session.commit()   # *will* fire off column defaults, and/or insert SQL NULL

The feature applies as well to the new base :class:`.types.JSON` type
and its descendant types.

:ticket:`3514`

.. _change_3514_jsonnull:

New JSON.NULL Constant Added
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To ensure that an application can always have full control at the value level
of whether a :class:`.types.JSON`, :class:`.postgresql.JSON`, :class:`.mysql.JSON`,
or :class:`.postgresql.JSONB` column
should receive an SQL NULL or JSON ``"null"`` value, the constant
:attr:`.types.JSON.NULL` has been added, which in conjunction with
:func:`.null` can be used to determine fully between SQL NULL and
JSON ``"null"``, regardless of what :paramref:`.types.JSON.none_as_null` is set
to::

    from sqlalchemy import null
    from sqlalchemy.dialects.postgresql import JSON

    obj1 = MyObject(json_value=null())  # will *always* insert SQL NULL
    obj2 = MyObject(json_value=JSON.NULL)  # will *always* insert JSON string "null"

    session.add_all([obj1, obj2])
    session.commit()

The feature applies as well to the new base :class:`.types.JSON` type
and its descendant types.

:ticket:`3514`

.. _change_3516:

Array support added to Core; new ANY and ALL operators
------------------------------------------------------

Along with the enhancements made to the Postgresql :class:`.postgresql.ARRAY`
type described in :ref:`change_3503`, the base class of :class:`.postgresql.ARRAY`
itself has been moved to Core in a new class :class:`.types.ARRAY`.

Arrays are part of the SQL standard, as are several array-oriented functions
such as ``array_agg()`` and ``unnest()``.  In support of these constructs
for not just PostgreSQL but also potentially for other array-capable backends
in the future such as DB2, the majority of array logic for SQL expressions
is now in Core.   The :class:`.types.ARRAY` type still **only works on
Postgresql**, however it can be used directly, supporting special array
use cases such as indexed access, as well as support for the ANY and ALL::

    mytable = Table("mytable", metadata,
            Column("data", ARRAY(Integer, dimensions=2))
        )

    expr = mytable.c.data[5][6]

    expr = mytable.c.data[5].any(12)

In support of ANY and ALL, the :class:`.types.ARRAY` type retains the same
:meth:`.types.ARRAY.Comparator.any` and :meth:`.types.ARRAY.Comparator.all` methods
from the PostgreSQL type, but also exports these operations to new
standalone operator functions :func:`.sql.expression.any_` and
:func:`.sql.expression.all_`.  These two functions work in more
of the traditional SQL way, allowing a right-side expression form such
as::

    from sqlalchemy import any_, all_

    select([mytable]).where(12 == any_(mytable.c.data[5]))

For the PostgreSQL-specific operators "contains", "contained_by", and
"overlaps", one should continue to use the :class:`.postgresql.ARRAY`
type directly, which provides all functionality of the :class:`.types.ARRAY`
type as well.

The :func:`.sql.expression.any_` and :func:`.sql.expression.all_` operators
are open-ended at the Core level, however their interpretation by backend
databases is limited.  On the Postgresql backend, the two operators
**only accept array values**.  Whereas on the MySQL backend, they
**only accept subquery values**.  On MySQL, one can use an expression
such as::

    from sqlalchemy import any_, all_

    subq = select([mytable.c.value])
    select([mytable]).where(12 > any_(subq))


:ticket:`3516`

.. _change_3132:

New Function features, "WITHIN GROUP", array_agg and set aggregate functions
----------------------------------------------------------------------------

With the new :class:`.types.ARRAY` type we can also implement a pre-typed
function for the ``array_agg()`` SQL function that returns an array,
which is now available using :class:`.array_agg`::

    from sqlalchemy import func
    stmt = select([func.array_agg(table.c.value)])

A Postgresql element for an aggregate ORDER BY is also added via
:class:`.postgresql.aggregate_order_by`::

    from sqlalchemy.dialects.postgresql import aggregate_order_by
    expr = func.array_agg(aggregate_order_by(table.c.a, table.c.b.desc()))
    stmt = select([expr])

Producing::

    SELECT array_agg(table1.a ORDER BY table1.b DESC) AS array_agg_1 FROM table1

The PG dialect itself also provides an :func:`.postgresql.array_agg` wrapper to
ensure the :class:`.postgresql.ARRAY` type::

    from sqlalchemy.dialects.postgresql import array_agg
    stmt = select([array_agg(table.c.value).contains('foo')])


Additionally, functions like ``percentile_cont()``, ``percentile_disc()``,
``rank()``, ``dense_rank()`` and others that require an ordering via
``WITHIN GROUP (ORDER BY <expr>)`` are now available via the
:meth:`.FunctionElement.within_group` modifier::

    from sqlalchemy import func
    stmt = select([
        department.c.id,
        func.percentile_cont(0.5).within_group(
            department.c.salary.desc()
        )
    ])

The above statement would produce SQL similar to::

  SELECT department.id, percentile_cont(0.5)
  WITHIN GROUP (ORDER BY department.salary DESC)

Placeholders with correct return types are now provided for these functions,
and include :class:`.percentile_cont`, :class:`.percentile_disc`,
:class:`.rank`, :class:`.dense_rank`, :class:`.mode`, :class:`.percent_rank`,
and :class:`.cume_dist`.

:ticket:`3132` :ticket:`1370`

.. _change_2919:

TypeDecorator now works with Enum, Boolean, "schema" types automatically
------------------------------------------------------------------------

The :class:`.SchemaType` types include types such as :class:`.Enum`
and :class:`.Boolean` which, in addition to corresponding to a database
type, also generate either a CHECK constraint or in the case of Postgresql
ENUM a new CREATE TYPE statement, will now work automatically with
:class:`.TypeDecorator` recipes.  Previously, a :class:`.TypeDecorator` for
an :class:`.postgresql.ENUM` had to look like this::

    # old way
    class MyEnum(TypeDecorator, SchemaType):
        impl = postgresql.ENUM('one', 'two', 'three', name='myenum')

        def _set_table(self, table):
            self.impl._set_table(table)

The :class:`.TypeDecorator` now propagates those additional events so it
can be done like any other type::

    # new way
    class MyEnum(TypeDecorator):
        impl = postgresql.ENUM('one', 'two', 'three', name='myenum')


:ticket:`2919`

.. _change_2685:

Multi-Tenancy Schema Translation for Table objects
--------------------------------------------------

To support the use case of an application that uses the same set of
:class:`.Table` objects in many schemas, such as schema-per-user, a new
execution option :paramref:`.Connection.execution_options.schema_translate_map`
is added.  Using this mapping, a set of :class:`.Table`
objects can be made on a per-connection basis to refer to any set of schemas
instead of the :paramref:`.Table.schema` to which they were assigned.  The
translation works for DDL and SQL generation, as well as with the ORM.

For example, if the ``User`` class were assigned the schema "per_user"::

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)

        __table_args__ = {'schema': 'per_user'}

On each request, the :class:`.Session` can be set up to refer to a
different schema each time::

    session = Session()
    session.connection(execution_options={
        "schema_translate_map": {"per_user": "account_one"}})

    # will query from the ``account_one.user`` table
    session.query(User).get(5)

.. seealso::

    :ref:`schema_translating`

:ticket:`2685`

.. _change_3631:

"Friendly" stringification of Core SQL constructs without a dialect
-------------------------------------------------------------------

Calling ``str()`` on a Core SQL construct will now produce a string
in more cases than before, supporting various SQL constructs not normally
present in default SQL such as RETURNING, array indexes, and non-standard
datatypes::

    >>> from sqlalchemy import table, column
    t>>> t = table('x', column('a'), column('b'))
    >>> print(t.insert().returning(t.c.a, t.c.b))
    INSERT INTO x (a, b) VALUES (:a, :b) RETURNING x.a, x.b

The ``str()`` function now calls upon an entirely separate dialect / compiler
intended just for plain string printing without a specific dialect set up,
so as more "just show me a string!" cases come up, these can be added
to this dialect/compiler without impacting behaviors on real dialects.

.. seealso::

    :ref:`change_3081`

:ticket:`3631`

.. _change_3531:

The type_coerce function is now a persistent SQL element
--------------------------------------------------------

The :func:`.expression.type_coerce` function previously would return
an object either of type :class:`.BindParameter` or :class:`.Label`, depending
on the input.  An effect this would have was that in the case where expression
transformations were used, such as the conversion of an element from a
:class:`.Column` to a :class:`.BindParameter` that's critical to ORM-level
lazy loading, the type coercion information would not be used since it would
have been lost already.

To improve this behavior, the function now returns a persistent
:class:`.TypeCoerce` container around the given expression, which itself
remains unaffected; this construct is evaluated explicitly by the
SQL compiler.  This allows for the coercion of the inner expression
to be maintained no matter how the statement is modified, including if
the contained element is replaced with a different one, as is common
within the ORM's lazy loading feature.

The test case illustrating the effect makes use of a heterogeneous
primaryjoin condition in conjunction with custom types and lazy loading.
Given a custom type that applies a CAST as a "bind expression"::

    class StringAsInt(TypeDecorator):
        impl = String

        def column_expression(self, col):
            return cast(col, Integer)

        def bind_expression(self, value):
            return cast(value, String)

Then, a mapping where we are equating a string "id" column on one
table to an integer "id" column on the other::

    class Person(Base):
        __tablename__ = 'person'
        id = Column(StringAsInt, primary_key=True)

        pets = relationship(
            'Pets',
            primaryjoin=(
                'foreign(Pets.person_id)'
                '==cast(type_coerce(Person.id, Integer), Integer)'
            )
        )

    class Pets(Base):
        __tablename__ = 'pets'
        id = Column('id', Integer, primary_key=True)
        person_id = Column('person_id', Integer)

Above, in the :paramref:`.relationship.primaryjoin` expression, we are
using :func:`.type_coerce` to handle bound parameters passed via
lazyloading as integers, since we already know these will come from
our ``StringAsInt`` type which maintains the value as an integer in
Python. We are then using :func:`.cast` so that as an SQL expression,
the VARCHAR "id"  column will be CAST to an integer for a regular non-
converted join as with :meth:`.Query.join` or :func:`.orm.joinedload`.
That is, a joinedload of ``.pets`` looks like::

    SELECT person.id AS person_id, pets_1.id AS pets_1_id,
           pets_1.person_id AS pets_1_person_id
    FROM person
    LEFT OUTER JOIN pets AS pets_1
    ON pets_1.person_id = CAST(person.id AS INTEGER)

Without the CAST in the ON clause of the join, strongly-typed databases
such as Postgresql will refuse to implicitly compare the integer and fail.

The lazyload case of ``.pets`` relies upon replacing
the ``Person.id`` column at load time with a bound parameter, which receives
a Python-loaded value.  This replacement is specifically where the intent
of our :func:`.type_coerce` function would be lost.  Prior to the change,
this lazy load comes out as::

    SELECT pets.id AS pets_id, pets.person_id AS pets_person_id
    FROM pets
    WHERE pets.person_id = CAST(CAST(%(param_1)s AS VARCHAR) AS INTEGER)
    {'param_1': 5}

Where above, we see that our in-Python value of ``5`` is CAST first
to a VARCHAR, then back to an INTEGER in SQL; a double CAST which works,
but is nevertheless not what we asked for.

With the change, the :func:`.type_coerce` function maintains a wrapper
even after the column is swapped out for a bound parameter, and the query now
looks like::

    SELECT pets.id AS pets_id, pets.person_id AS pets_person_id
    FROM pets
    WHERE pets.person_id = CAST(%(param_1)s AS INTEGER)
    {'param_1': 5}

Where our outer CAST that's in our primaryjoin still takes effect, but the
needless CAST that's in part of the ``StringAsInt`` custom type is removed
as intended by the :func:`.type_coerce` function.


:ticket:`3531`


Key Behavioral Changes - ORM
============================


Key Behavioral Changes - Core
=============================

.. _behavior_change_3501:

TextClause.columns() will match columns positionally, not by name, when passed positionally
-------------------------------------------------------------------------------------------

The new behavior of the :meth:`.TextClause.columns` method, which itself
was recently added as of the 0.9 series, is that when
columns are passed positionally without any additional keyword arguments,
they are linked to the ultimate result set
columns positionally, and no longer on name.   It is hoped that the impact
of this change will be low due to the fact that the method has always been documented
illustrating the columns being passed in the same order as that of the
textual SQL statement, as would seem intuitive, even though the internals
weren't checking for this.

An application that is using this method by passing :class:`.Column` objects
to it positionally must ensure that the position of those :class:`.Column`
objects matches the position in which these columns are stated in the
textual SQL.

E.g., code like the following::

    stmt = text("SELECT id, name, description FROM table")

    # no longer matches by name
    stmt = stmt.columns(my_table.c.name, my_table.c.description, my_table.c.id)

Would no longer work as expected; the order of the columns given is now
significant::

    # correct version
    stmt = stmt.columns(my_table.c.id, my_table.c.name, my_table.c.description)

Possibly more likely, a statement that worked like this::

    stmt = text("SELECT * FROM table")
    stmt = stmt.columns(my_table.c.id, my_table.c.name, my_table.c.description)

is now slightly risky, as the "*" specification will generally deliver columns
in the order in which they are present in the table itself.  If the structure
of the table changes due to schema changes, this ordering may no longer be the same.
Therefore when using :meth:`.TextClause.columns`, it's advised to list out
the desired columns explicitly in the textual SQL, though it's no longer
necessary to worry about the names themselves in the textual SQL.

.. seealso::

    :ref:`change_3501`

Dialect Improvements and Changes - Postgresql
=============================================

.. _change_3499_postgresql:

ARRAY and JSON types now correctly specify "unhashable"
-------------------------------------------------------

As described in :ref:`change_3499`, the ORM relies upon being able to
produce a hash function for column values when a query's selected entities
mixes full ORM entities with column expressions.   The ``hashable=False``
flag is now correctly set on all of PG's "data structure" types, including
:class:`.postgresql.ARRAY` and :class:`.postgresql.JSON`.
The :class:`.JSONB` and :class:`.HSTORE`
types already included this flag.  For :class:`.postgresql.ARRAY`,
this is conditional based on the :paramref:`.postgresql.ARRAY.as_tuple`
flag, however it should no longer be necessary to set this flag
in order to have an array value present in a composed ORM row.

.. seealso::

    :ref:`change_3499`

    :ref:`change_3503`

:ticket:`3499`

.. _change_3503:

Correct SQL Types are Established from Indexed Access of ARRAY, JSON, HSTORE
-----------------------------------------------------------------------------

For all three of :class:`~.postgresql.ARRAY`, :class:`~.postgresql.JSON` and :class:`.HSTORE`,
the SQL type assigned to the expression returned by indexed access, e.g.
``col[someindex]``, should be correct in all cases.

This includes:

* The SQL type assigned to indexed access of an :class:`~.postgresql.ARRAY` takes into
  account the number of dimensions configured.   An :class:`~.postgresql.ARRAY` with three
  dimensions will return an SQL expression with a type of :class:`~.postgresql.ARRAY` of
  one less dimension.  Given a column with type ``ARRAY(Integer, dimensions=3)``,
  we can now perform this expression::

      int_expr = col[5][6][7]   # returns an Integer expression object

  Previously, the indexed access to ``col[5]`` would return an expression of
  type :class:`.Integer` where we could no longer perform indexed access
  for the remaining dimensions, unless we used :func:`.cast` or :func:`.type_coerce`.

* The :class:`~.postgresql.JSON` and :class:`~.postgresql.JSONB` types now mirror what Postgresql
  itself does for indexed access.  This means that all indexed access for
  a :class:`~.postgresql.JSON` or :class:`~.postgresql.JSONB` type returns an expression that itself
  is *always* :class:`~.postgresql.JSON` or :class:`~.postgresql.JSONB` itself, unless the
  :attr:`~.postgresql.JSON.Comparator.astext` modifier is used.   This means that whether
  the indexed access of the JSON structure ultimately refers to a string,
  list, number, or other JSON structure, Postgresql always considers it
  to be JSON itself unless it is explicitly cast differently.   Like
  the :class:`~.postgresql.ARRAY` type, this means that it is now straightforward
  to produce JSON expressions with multiple levels of indexed access::

    json_expr = json_col['key1']['attr1'][5]

* The "textual" type that is returned by indexed access of :class:`.HSTORE`
  as well as the "textual" type that is returned by indexed access of
  :class:`~.postgresql.JSON` and :class:`~.postgresql.JSONB` in conjunction with the
  :attr:`~.postgresql.JSON.Comparator.astext` modifier is now configurable; it defaults
  to :class:`.Text` in both cases but can be set to a user-defined
  type using the :paramref:`.postgresql.JSON.astext_type` or
  :paramref:`.postgresql.HSTORE.text_type` parameters.

.. seealso::

  :ref:`change_3503_cast`

:ticket:`3499`
:ticket:`3487`

.. _change_3503_cast:

The JSON cast() operation now requires ``.astext`` is called explicitly
------------------------------------------------------------------------

As part of the changes in :ref:`change_3503`, the workings of the
:meth:`.ColumnElement.cast` operator on :class:`.postgresql.JSON` and
:class:`.postgresql.JSONB` no longer implictly invoke the
:attr:`.postgresql.JSON.Comparator.astext` modifier; Postgresql's JSON/JSONB types
support CAST operations to each other without the "astext" aspect.

This means that in most cases, an application that was doing this::

    expr = json_col['somekey'].cast(Integer)

Will now need to change to this::

    expr = json_col['somekey'].astext.cast(Integer)


.. _change_2729:

ARRAY with ENUM will now emit CREATE TYPE for the ENUM
------------------------------------------------------

A table definition like the following will now emit CREATE TYPE
as expected::

    enum = Enum(
        'manager', 'place_admin', 'carwash_admin',
        'parking_admin', 'service_admin', 'tire_admin',
        'mechanic', 'carwasher', 'tire_mechanic', name="work_place_roles")

    class WorkPlacement(Base):
        __tablename__ = 'work_placement'
        id = Column(Integer, primary_key=True)
        roles = Column(ARRAY(enum))


    e = create_engine("postgresql://scott:tiger@localhost/test", echo=True)
    Base.metadata.create_all(e)

emits::

    CREATE TYPE work_place_roles AS ENUM (
        'manager', 'place_admin', 'carwash_admin', 'parking_admin',
        'service_admin', 'tire_admin', 'mechanic', 'carwasher',
        'tire_mechanic')

    CREATE TABLE work_placement (
        id SERIAL NOT NULL,
        roles work_place_roles[],
        PRIMARY KEY (id)
    )


:ticket:`2729`

Support for PyGreSQL
--------------------

The `PyGreSQL <https://pypi.python.org/pypi/PyGreSQL>`_ DBAPI is now supported.

.. seealso::

    :ref:`dialect-postgresql-pygresql`

The "postgres" module is removed
---------------------------------

The ``sqlalchemy.dialects.postgres`` module, long deprecated, is
removed; this has emitted a warning for many years and projects
should be calling upon ``sqlalchemy.dialects.postgresql``.
Engine URLs of the form ``postgres://`` will still continue to function,
however.

Dialect Improvements and Changes - MySQL
=============================================

.. _change_3547:

MySQL JSON Support
------------------

A new type :class:`.mysql.JSON` is added to the MySQL dialect supporting
the JSON type newly added to MySQL 5.7.   This type provides both persistence
of JSON as well as rudimentary indexed-access using the ``JSON_EXTRACT``
function internally.  An indexable JSON column that works across MySQL
and Postgresql can be achieved by using the :class:`.types.JSON` datatype
common to both MySQL and Postgresql.

.. seealso::

    :ref:`change_3619`

:ticket:`3547`

.. _change_3332:

Added support for AUTOCOMMIT "isolation level"
----------------------------------------------

The MySQL dialect now accepts the value "AUTOCOMMIT" for the
:paramref:`.create_engine.isolation_level` and
:paramref:`.Connection.execution_options.isolation_level`
parameters::

    connection = engine.connect()
    connection = connection.execution_options(
        isolation_level="AUTOCOMMIT"
    )

The isolation level makes use of the various "autocommit" attributes
provided by most MySQL DBAPIs.

:ticket:`3332`

.. _change_mysql_3216:

No more generation of an implicit KEY for composite primary key w/ AUTO_INCREMENT
---------------------------------------------------------------------------------

The MySQL dialect had the behavior such that if a composite primary key
on an InnoDB table featured AUTO_INCREMENT on one of its columns which was
not the first column, e.g.::

    t = Table(
        'some_table', metadata,
        Column('x', Integer, primary_key=True, autoincrement=False),
        Column('y', Integer, primary_key=True, autoincrement=True),
        mysql_engine='InnoDB'
    )

DDL such as the following would be generated::

    CREATE TABLE some_table (
        x INTEGER NOT NULL,
        y INTEGER NOT NULL AUTO_INCREMENT,
        PRIMARY KEY (x, y),
        KEY idx_autoinc_y (y)
    )ENGINE=InnoDB

Note the above "KEY" with an auto-generated name; this is a change that
found its way into the dialect many years ago in response to the issue that
the AUTO_INCREMENT would otherwise fail on InnoDB without this additional KEY.

This workaround has been removed and replaced with the much better system
of just stating the AUTO_INCREMENT column *first* within the primary key::

    CREATE TABLE some_table (
        x INTEGER NOT NULL,
        y INTEGER NOT NULL AUTO_INCREMENT,
        PRIMARY KEY (y, x)
    )ENGINE=InnoDB

Along with the change :ref:`change_3216`, composite primary keys with
or without auto increment are now easier to specify;
:paramref:`.Column.autoincrement`
now defaults to the value ``"auto"`` and the ``autoincrement=False``
directives are no longer needed::

    t = Table(
        'some_table', metadata,
        Column('x', Integer, primary_key=True),
        Column('y', Integer, primary_key=True, autoincrement=True),
        mysql_engine='InnoDB'
    )



Dialect Improvements and Changes - SQLite
=============================================

.. _change_3634:

Right-nested join workaround lifted for SQLite version 3.7.16
-------------------------------------------------------------

In version 0.9, the feature introduced by :ref:`feature_joins_09` went
through lots of effort to support rewriting of joins on SQLite to always
use subqueries in order to achieve a "right-nested-join" effect, as
SQLite has not supported this syntax for many years.  Ironically,
the version of SQLite noted in that migration note, 3.7.15.2, was the *last*
version of SQLite to actually have this limitation!   The next release was
3.7.16 and support for right nested joins was quietly added.   In 1.1, the work
to identify the specific SQLite version and source commit where this change
was made was done (SQlite's changelog refers to it with the cryptic phrase "Enhance
the query optimizer to exploit transitive join constraints" without linking
to any issue number, change number, or further explanation), and the workarounds
present in this change are now lifted for SQLite when the DBAPI reports
that version 3.7.16 or greater is in effect.

:ticket:`3634`

.. _change_3633:

Dotted column names workaround lifted for SQLite version 3.10.0
---------------------------------------------------------------

The SQLite dialect has long had a workaround for an issue where the database
driver does not report the correct column names for some SQL result sets, in
particular when UNION is used.  The workaround is detailed at
:ref:`sqlite_dotted_column_names`, and requires that SQLAlchemy assume that any
column name with a dot in it is actually a ``tablename.columnname`` combination
delivered via this buggy behavior, with an option to turn it off via the
``sqlite_raw_colnames`` execution option.

As of SQLite version 3.10.0, the bug in UNION and other queries has been fixed;
like the change described in :ref:`change_3634`, SQLite's changelog only
identifies it cryptically as "Added the colUsed field to sqlite3_index_info for
use by the sqlite3_module.xBestIndex method", however SQLAlchemy's translation
of these dotted column names is no longer required with this version, so is
turned off when version 3.10.0 or greater is detected.

Overall, the SQLAlchemy :class:`.ResultProxy` as of the 1.0 series relies much
less on column names in result sets when delivering results for Core and ORM
SQL constructs, so the importance of this issue was already lessened in any
case.

:ticket:`3633`

.. _change_sqlite_schemas:

Improved Support for Remote Schemas
-----------------------------------
The SQLite dialect now implements :meth:`.Inspector.get_schema_names`
and additionally has improved support for tables and indexes that are
created and reflected from a remote schema, which in SQLite is a
dataase that is assigned a name via the ``ATTACH`` statement; previously,
the``CREATE INDEX`` DDL didn't work correctly for a schema-bound table
and the :meth:`.Inspector.get_foreign_keys` method will now indicate the
given schema in the results.  Cross-schema foreign keys aren't supported.

.. _change_3629:

Reflection of the name of PRIMARY KEY constraints
--------------------------------------------------

The SQLite backend now takes advantage of the "sqlite_master" view
of SQLite in order to extract the name of the primary key constraint
of a table from the original DDL, in the same way that is achieved for
foreign key constraints in recent SQLAlchemy versions.

:ticket:`3629`

Dialect Improvements and Changes - SQL Server
=============================================

.. _change_3534:

Added transaction isolation level support for SQL Server
--------------------------------------------------------

All SQL Server dialects support transaction isolation level settings
via the :paramref:`.create_engine.isolation_level` and
:paramref:`.Connection.execution_options.isolation_level`
parameters.  The four standard levels are supported as well as
``SNAPSHOT``::

    engine = create_engine(
        "mssql+pyodbc://scott:tiger@ms_2008",
        isolation_level="REPEATABLE READ"
    )

.. seealso::

    :ref:`mssql_isolation_level`

:ticket:`3534`

.. _change_3504:

String / varlength types no longer represent "max" explicitly on reflection
---------------------------------------------------------------------------

When reflecting a type such as :class:`.String`, :class:`.Text`, etc.
which includes a length, an "un-lengthed" type under SQL Server would
copy the "length" parameter as the value ``"max"``::

    >>> from sqlalchemy import create_engine, inspect
    >>> engine = create_engine('mssql+pyodbc://scott:tiger@ms_2008', echo=True)
    >>> engine.execute("create table s (x varchar(max), y varbinary(max))")
    >>> insp = inspect(engine)
    >>> for col in insp.get_columns("s"):
    ...     print(col['type'].__class__, col['type'].length)
    ...
    <class 'sqlalchemy.sql.sqltypes.VARCHAR'> max
    <class 'sqlalchemy.dialects.mssql.base.VARBINARY'> max

The "length" parameter in the base types is expected to be an integer value
or None only; None indicates unbounded length which the SQL Server dialect
interprets as "max".   The fix then is so that these lengths come
out as None, so that the type objects work in non-SQL Server contexts::

    >>> for col in insp.get_columns("s"):
    ...     print(col['type'].__class__, col['type'].length)
    ...
    <class 'sqlalchemy.sql.sqltypes.VARCHAR'> None
    <class 'sqlalchemy.dialects.mssql.base.VARBINARY'> None

Applications which may have been relying on a direct comparison of the "length"
value to the string "max" should consider the value of ``None`` to mean
the same thing.

:ticket:`3504`

.. _change_3434:

The legacy_schema_aliasing flag is now set to False
---------------------------------------------------

SQLAlchemy 1.0.5 introduced the ``legacy_schema_aliasing`` flag to the
MSSQL dialect, allowing so-called "legacy mode" aliasing to be turned off.
This aliasing attempts to turn schema-qualified tables into aliases;
given a table such as::

    account_table = Table(
        'account', metadata,
        Column('id', Integer, primary_key=True),
        Column('info', String(100)),
        schema="customer_schema"
    )

The legacy mode of behavior will attempt to turn a schema-qualified table
name into an alias::

    >>> eng = create_engine("mssql+pymssql://mydsn", legacy_schema_aliasing=True)
    >>> print(account_table.select().compile(eng))
    SELECT account_1.id, account_1.info
    FROM customer_schema.account AS account_1

However, this aliasing has been shown to be unnecessary and in many cases
produces incorrect SQL.

In SQLAlchemy 1.1, the ``legacy_schema_aliasing`` flag now defaults to
False, disabling this mode of behavior and allowing the MSSQL dialect to behave
normally with schema-qualified tables.  For applications which may rely
on this behavior, set the flag back to True.


:ticket:`3434`

Dialect Improvements and Changes - Oracle
=============================================
