.. _ormtutorial_toplevel:

==========================
Object Relational Tutorial
==========================

The SQLAlchemy Object Relational Mapper presents a method of associating
user-defined Python classes with database tables, and instances of those
classes (objects) with rows in their corresponding tables. It includes a
system that transparently synchronizes all changes in state between objects
and their related rows, called a :term:`unit of work`, as well as a system
for expressing database queries in terms of the user defined classes and their
defined relationships between each other.

The ORM is in contrast to the SQLAlchemy Expression Language, upon which the
ORM is constructed. Whereas the SQL Expression Language, introduced in
:ref:`sqlexpression_toplevel`, presents a system of representing the primitive
constructs of the relational database directly without opinion, the ORM
presents a high level and abstracted pattern of usage, which itself is an
example of applied usage of the Expression Language.

While there is overlap among the usage patterns of the ORM and the Expression
Language, the similarities are more superficial than they may at first appear.
One approaches the structure and content of data from the perspective of a
user-defined :term:`domain model` which is transparently
persisted and refreshed from its underlying storage model. The other
approaches it from the perspective of literal schema and SQL expression
representations which are explicitly composed into messages consumed
individually by the database.

A successful application may be constructed using the Object Relational Mapper
exclusively. In advanced situations, an application constructed with the ORM
may make occasional usage of the Expression Language directly in certain areas
where specific database interactions are required.

The following tutorial is in doctest format, meaning each ``>>>`` line
represents something you can type at a Python command prompt, and the
following text represents the expected return value.

Version Check
=============

A quick check to verify that we are on at least **version 0.9** of SQLAlchemy::

    >>> import sqlalchemy
    >>> sqlalchemy.__version__ # doctest:+SKIP
    0.9.0

Connecting
==========

For this tutorial we will use an in-memory-only SQLite database. To connect we
use :func:`~sqlalchemy.create_engine`::

    >>> from sqlalchemy import create_engine
    >>> engine = create_engine('sqlite:///:memory:', echo=True)

The ``echo`` flag is a shortcut to setting up SQLAlchemy logging, which is
accomplished via Python's standard ``logging`` module. With it enabled, we'll
see all the generated SQL produced. If you are working through this tutorial
and want less output generated, set it to ``False``. This tutorial will format
the SQL behind a popup window so it doesn't get in our way; just click the
"SQL" links to see what's being generated.

The return value of :func:`.create_engine` is an instance of
:class:`.Engine`, and it represents the core interface to the
database, adapted through a :term:`dialect` that handles the details
of the database and :term:`DBAPI` in use.  In this case the SQLite
dialect will interpret instructions to the Python built-in ``sqlite3``
module.

.. sidebar:: Lazy Connecting

    The :class:`.Engine`, when first returned by :func:`.create_engine`,
    has not actually tried to connect to the database yet; that happens
    only the first time it is asked to perform a task against the database.

The first time a method like :meth:`.Engine.execute` or :meth:`.Engine.connect`
is called, the :class:`.Engine` establishes a real :term:`DBAPI` connection to the
database, which is then used to emit the SQL.  When using the ORM, we typically
don't use the :class:`.Engine` directly once created; instead, it's used
behind the scenes by the ORM as we'll see shortly.

.. seealso::

    :ref:`database_urls` - includes examples of :func:`.create_engine`
    connecting to several kinds of databases with links to more information.

Declare a Mapping
=================

When using the ORM, the configurational process starts by describing the database
tables we'll be dealing with, and then by defining our own classes which will
be mapped to those tables.   In modern SQLAlchemy,
these two tasks are usually performed together,
using a system known as :ref:`declarative_toplevel`, which allows us to create
classes that include directives to describe the actual database table they will
be mapped to.

Classes mapped using the Declarative system are defined in terms of a base class which
maintains a catalog of classes and
tables relative to that base - this is known as the **declarative base class**.  Our
application will usually have just one instance of this base in a commonly
imported module.   We create the base class using the :func:`.declarative_base`
function, as follows::

    >>> from sqlalchemy.ext.declarative import declarative_base

    >>> Base = declarative_base()

Now that we have a "base", we can define any number of mapped classes in terms
of it.  We will start with just a single table called ``users``, which will store
records for the end-users using our application.
A new class called ``User`` will be the class to which we map this table.  Within
the class, we define details about the table to which we'll be mapping, primarily
the table name, and names and datatypes of columns::

    >>> from sqlalchemy import Column, Integer, String
    >>> class User(Base):
    ...     __tablename__ = 'users'
    ...
    ...     id = Column(Integer, primary_key=True)
    ...     name = Column(String)
    ...     fullname = Column(String)
    ...     password = Column(String)
    ...
    ...     def __repr__(self):
    ...        return "<User(name='%s', fullname='%s', password='%s')>" % (
    ...                             self.name, self.fullname, self.password)

.. sidebar:: Tip

    The ``User`` class defines a ``__repr__()`` method,
    but note that is **optional**; we only implement it in
    this tutorial so that our examples show nicely
    formatted ``User`` objects.

A class using Declarative at a minimum
needs a ``__tablename__`` attribute, and at least one
:class:`.Column` which is part of a primary key [#]_.  SQLAlchemy never makes any
assumptions by itself about the table to which
a class refers, including that it has no built-in conventions for names,
datatypes, or constraints.   But this doesn't mean
boilerplate is required; instead, you're encouraged to create your
own automated conventions using helper functions and mixin classes, which
is described in detail at :ref:`declarative_mixins`.

When our class is constructed, Declarative replaces all the :class:`.Column`
objects with special Python accessors known as :term:`descriptors`; this is a
process known as :term:`instrumentation`.   The "instrumented" mapped class
will provide us with the means to refer to our table in a SQL context as well
as to persist and load the values of columns from the database.

Outside of what the mapping process does to our class, the class remains
otherwise mostly a normal Python class, to which we can define any
number of ordinary attributes and methods needed by our application.

.. [#] For information on why a primary key is required, see
   :ref:`faq_mapper_primary_key`.


Create a Schema
===============

With our ``User`` class constructed via the Declarative system, we have defined information about
our table, known as :term:`table metadata`.   The object used by SQLAlchemy to represent
this information for a specific table is called the :class:`.Table` object, and here Declarative has made
one for us.  We can see this object by inspecting the ``__table__`` attribute::

    >>> User.__table__ # doctest: +NORMALIZE_WHITESPACE
    Table('users', MetaData(bind=None),
                Column('id', Integer(), table=<users>, primary_key=True, nullable=False),
                Column('name', String(), table=<users>),
                Column('fullname', String(), table=<users>),
                Column('password', String(), table=<users>), schema=None)

.. sidebar:: Classical Mappings

    The Declarative system, though highly recommended,
    is not required in order to use SQLAlchemy's ORM.
    Outside of Declarative, any
    plain Python class can be mapped to any :class:`.Table`
    using the :func:`.mapper` function directly; this
    less common usage is described at :ref:`classical_mapping`.

When we declared our class, Declarative used a Python metaclass in order to
perform additional activities once the class declaration was complete; within
this phase, it then created a :class:`.Table` object according to our
specifications, and associated it with the class by constructing
a :class:`.Mapper` object.  This object is a behind-the-scenes object we normally
don't need to deal with directly (though it can provide plenty of information
about our mapping when we need it).

The :class:`.Table` object is a member of a larger collection
known as :class:`.MetaData`.  When using Declarative,
this object is available using the ``.metadata``
attribute of our declarative base class.

The :class:`.MetaData`
is a :term:`registry` which includes the ability to emit a limited set
of schema generation commands to the database.  As our SQLite database
does not actually have a ``users`` table present, we can use :class:`.MetaData`
to issue CREATE TABLE statements to the database for all tables that don't yet exist.
Below, we call the :meth:`.MetaData.create_all` method, passing in our :class:`.Engine`
as a source of database connectivity.  We will see that special commands are
first emitted to check for the presence of the ``users`` table, and following that
the actual ``CREATE TABLE`` statement:

.. sourcecode:: python+sql

    >>> Base.metadata.create_all(engine) # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
    {opensql}PRAGMA table_info("users")
    ()
    CREATE TABLE users (
        id INTEGER NOT NULL,
        name VARCHAR,
        fullname VARCHAR,
        password VARCHAR,
        PRIMARY KEY (id)
    )
    ()
    COMMIT

.. topic:: Minimal Table Descriptions vs. Full Descriptions

    Users familiar with the syntax of CREATE TABLE may notice that the
    VARCHAR columns were generated without a length; on SQLite and Postgresql,
    this is a valid datatype, but on others, it's not allowed. So if running
    this tutorial on one of those databases, and you wish to use SQLAlchemy to
    issue CREATE TABLE, a "length" may be provided to the :class:`~sqlalchemy.types.String` type as
    below::

        Column(String(50))

    The length field on :class:`~sqlalchemy.types.String`, as well as similar precision/scale fields
    available on :class:`~sqlalchemy.types.Integer`, :class:`~sqlalchemy.types.Numeric`, etc. are not referenced by
    SQLAlchemy other than when creating tables.

    Additionally, Firebird and Oracle require sequences to generate new
    primary key identifiers, and SQLAlchemy doesn't generate or assume these
    without being instructed. For that, you use the :class:`~sqlalchemy.schema.Sequence` construct::

        from sqlalchemy import Sequence
        Column(Integer, Sequence('user_id_seq'), primary_key=True)

    A full, foolproof :class:`~sqlalchemy.schema.Table` generated via our declarative
    mapping is therefore::

        class User(Base):
            __tablename__ = 'users'
            id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
            name = Column(String(50))
            fullname = Column(String(50))
            password = Column(String(12))

            def __repr__(self):
                return "<User(name='%s', fullname='%s', password='%s')>" % (
                                        self.name, self.fullname, self.password)

    We include this more verbose table definition separately
    to highlight the difference between a minimal construct geared primarily
    towards in-Python usage only, versus one that will be used to emit CREATE
    TABLE statements on a particular set of backends with more stringent
    requirements.

Create an Instance of the Mapped Class
======================================

With mappings complete, let's now create and inspect a ``User`` object::

    >>> ed_user = User(name='ed', fullname='Ed Jones', password='edspassword')
    >>> ed_user.name
    'ed'
    >>> ed_user.password
    'edspassword'
    >>> str(ed_user.id)
    'None'


.. sidebar:: the ``__init__()`` method

    Our ``User`` class, as defined using the Declarative system, has
    been provided with a constructor (e.g. ``__init__()`` method) which automatically
    accepts keyword names that match the columns we've mapped.    We are free
    to define any explicit ``__init__()`` method we prefer on our class, which
    will override the default method provided by Declarative.

Even though we didn't specify it in the constructor, the ``id`` attribute
still produces a value of ``None`` when we access it (as opposed to Python's
usual behavior of raising ``AttributeError`` for an undefined attribute).
SQLAlchemy's :term:`instrumentation` normally produces this default value for
column-mapped attributes when first accessed.    For those attributes where
we've actually assigned a value, the instrumentation system is tracking
those assignments for use within an eventual INSERT statement to be emitted to the
database.

Creating a Session
==================

We're now ready to start talking to the database. The ORM's "handle" to the
database is the :class:`~sqlalchemy.orm.session.Session`. When we first set up
the application, at the same level as our :func:`~sqlalchemy.create_engine`
statement, we define a :class:`~sqlalchemy.orm.session.Session` class which
will serve as a factory for new :class:`~sqlalchemy.orm.session.Session`
objects::

    >>> from sqlalchemy.orm import sessionmaker
    >>> Session = sessionmaker(bind=engine)

In the case where your application does not yet have an
:class:`~sqlalchemy.engine.Engine` when you define your module-level
objects, just set it up like this::

    >>> Session = sessionmaker()

Later, when you create your engine with :func:`~sqlalchemy.create_engine`,
connect it to the :class:`~sqlalchemy.orm.session.Session` using
:meth:`~.sessionmaker.configure`::

    >>> Session.configure(bind=engine)  # once engine is available

.. sidebar:: Session Lifecycle Patterns

    The question of when to make a :class:`.Session` depends a lot on what
    kind of application is being built.  Keep in mind,
    the :class:`.Session` is just a workspace for your objects,
    local to a particular database connection - if you think of
    an application thread as a guest at a dinner party, the :class:`.Session`
    is the guest's plate and the objects it holds are the food
    (and the database...the kitchen?)!  More on this topic
    available at :ref:`session_faq_whentocreate`.

This custom-made :class:`~sqlalchemy.orm.session.Session` class will create
new :class:`~sqlalchemy.orm.session.Session` objects which are bound to our
database. Other transactional characteristics may be defined when calling
:class:`~.sessionmaker` as well; these are described in a later
chapter. Then, whenever you need to have a conversation with the database, you
instantiate a :class:`~sqlalchemy.orm.session.Session`::

    >>> session = Session()

The above :class:`~sqlalchemy.orm.session.Session` is associated with our
SQLite-enabled :class:`.Engine`, but it hasn't opened any connections yet. When it's first
used, it retrieves a connection from a pool of connections maintained by the
:class:`.Engine`, and holds onto it until we commit all changes and/or close the
session object.


Adding New Objects
==================

To persist our ``User`` object, we :meth:`~.Session.add` it to our :class:`~sqlalchemy.orm.session.Session`::

    >>> ed_user = User(name='ed', fullname='Ed Jones', password='edspassword')
    >>> session.add(ed_user)

At this point, we say that the instance is **pending**; no SQL has yet been issued
and the object is not yet represented by a row in the database.  The
:class:`~sqlalchemy.orm.session.Session` will issue the SQL to persist ``Ed
Jones`` as soon as is needed, using a process known as a **flush**. If we
query the database for ``Ed Jones``, all pending information will first be
flushed, and the query is issued immediately thereafter.

For example, below we create a new :class:`~sqlalchemy.orm.query.Query` object
which loads instances of ``User``. We "filter by" the ``name`` attribute of
``ed``, and indicate that we'd like only the first result in the full list of
rows. A ``User`` instance is returned which is equivalent to that which we've
added:

.. sourcecode:: python+sql

    {sql}>>> our_user = session.query(User).filter_by(name='ed').first() # doctest:+ELLIPSIS,+NORMALIZE_WHITESPACE
    BEGIN (implicit)
    INSERT INTO users (name, fullname, password) VALUES (?, ?, ?)
    ('ed', 'Ed Jones', 'edspassword')
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name = ?
     LIMIT ? OFFSET ?
    ('ed', 1, 0)
    {stop}>>> our_user
    <User(name='ed', fullname='Ed Jones', password='edspassword')>

In fact, the :class:`~sqlalchemy.orm.session.Session` has identified that the
row returned is the **same** row as one already represented within its
internal map of objects, so we actually got back the identical instance as
that which we just added::

    >>> ed_user is our_user
    True

The ORM concept at work here is known as an :term:`identity map`
and ensures that
all operations upon a particular row within a
:class:`~sqlalchemy.orm.session.Session` operate upon the same set of data.
Once an object with a particular primary key is present in the
:class:`~sqlalchemy.orm.session.Session`, all SQL queries on that
:class:`~sqlalchemy.orm.session.Session` will always return the same Python
object for that particular primary key; it also will raise an error if an
attempt is made to place a second, already-persisted object with the same
primary key within the session.

We can add more ``User`` objects at once using
:func:`~sqlalchemy.orm.session.Session.add_all`:

.. sourcecode:: python+sql

    >>> session.add_all([
    ...     User(name='wendy', fullname='Wendy Williams', password='foobar'),
    ...     User(name='mary', fullname='Mary Contrary', password='xxg527'),
    ...     User(name='fred', fullname='Fred Flinstone', password='blah')])

Also, we've decided the password for Ed isn't too secure, so lets change it:

.. sourcecode:: python+sql

    >>> ed_user.password = 'f8s7ccs'

The :class:`~sqlalchemy.orm.session.Session` is paying attention. It knows,
for example, that ``Ed Jones`` has been modified:

.. sourcecode:: python+sql

    >>> session.dirty
    IdentitySet([<User(name='ed', fullname='Ed Jones', password='f8s7ccs')>])

and that three new ``User`` objects are pending:

.. sourcecode:: python+sql

    >>> session.new  # doctest: +SKIP
    IdentitySet([<User(name='wendy', fullname='Wendy Williams', password='foobar')>,
    <User(name='mary', fullname='Mary Contrary', password='xxg527')>,
    <User(name='fred', fullname='Fred Flinstone', password='blah')>])

We tell the :class:`~sqlalchemy.orm.session.Session` that we'd like to issue
all remaining changes to the database and commit the transaction, which has
been in progress throughout. We do this via :meth:`~.Session.commit`:

.. sourcecode:: python+sql

    {sql}>>> session.commit()
    UPDATE users SET password=? WHERE users.id = ?
    ('f8s7ccs', 1)
    INSERT INTO users (name, fullname, password) VALUES (?, ?, ?)
    ('wendy', 'Wendy Williams', 'foobar')
    INSERT INTO users (name, fullname, password) VALUES (?, ?, ?)
    ('mary', 'Mary Contrary', 'xxg527')
    INSERT INTO users (name, fullname, password) VALUES (?, ?, ?)
    ('fred', 'Fred Flinstone', 'blah')
    COMMIT

:meth:`~.Session.commit` flushes whatever remaining changes remain to the
database, and commits the transaction. The connection resources referenced by
the session are now returned to the connection pool. Subsequent operations
with this session will occur in a **new** transaction, which will again
re-acquire connection resources when first needed.

If we look at Ed's ``id`` attribute, which earlier was ``None``, it now has a value:

.. sourcecode:: python+sql

    {sql}>>> ed_user.id # doctest: +NORMALIZE_WHITESPACE
    BEGIN (implicit)
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.id = ?
    (1,)
    {stop}1

After the :class:`~sqlalchemy.orm.session.Session` inserts new rows in the
database, all newly generated identifiers and database-generated defaults
become available on the instance, either immediately or via
load-on-first-access. In this case, the entire row was re-loaded on access
because a new transaction was begun after we issued :meth:`~.Session.commit`. SQLAlchemy
by default refreshes data from a previous transaction the first time it's
accessed within a new transaction, so that the most recent state is available.
The level of reloading is configurable as is described in :doc:`/orm/session`.

.. topic:: Session Object States

   As our ``User`` object moved from being outside the :class:`.Session`, to
   inside the :class:`.Session` without a primary key, to actually being
   inserted, it moved between three out of four
   available "object states" - **transient**, **pending**, and **persistent**.
   Being aware of these states and what they mean is always a good idea -
   be sure to read :ref:`session_object_states` for a quick overview.

Rolling Back
============
Since the :class:`~sqlalchemy.orm.session.Session` works within a transaction,
we can roll back changes made too. Let's make two changes that we'll revert;
``ed_user``'s user name gets set to ``Edwardo``:

.. sourcecode:: python+sql

    >>> ed_user.name = 'Edwardo'

and we'll add another erroneous user, ``fake_user``:

.. sourcecode:: python+sql

    >>> fake_user = User(name='fakeuser', fullname='Invalid', password='12345')
    >>> session.add(fake_user)

Querying the session, we can see that they're flushed into the current transaction:

.. sourcecode:: python+sql

    {sql}>>> session.query(User).filter(User.name.in_(['Edwardo', 'fakeuser'])).all() #doctest: +NORMALIZE_WHITESPACE
    UPDATE users SET name=? WHERE users.id = ?
    ('Edwardo', 1)
    INSERT INTO users (name, fullname, password) VALUES (?, ?, ?)
    ('fakeuser', 'Invalid', '12345')
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name IN (?, ?)
    ('Edwardo', 'fakeuser')
    {stop}[<User(name='Edwardo', fullname='Ed Jones', password='f8s7ccs')>, <User(user='fakeuser', fullname='Invalid', password='12345')>]

Rolling back, we can see that ``ed_user``'s name is back to ``ed``, and
``fake_user`` has been kicked out of the session:

.. sourcecode:: python+sql

    {sql}>>> session.rollback()
    ROLLBACK
    {stop}

    {sql}>>> ed_user.name #doctest: +NORMALIZE_WHITESPACE
    BEGIN (implicit)
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.id = ?
    (1,)
    {stop}u'ed'
    >>> fake_user in session
    False

issuing a SELECT illustrates the changes made to the database:

.. sourcecode:: python+sql

    {sql}>>> session.query(User).filter(User.name.in_(['ed', 'fakeuser'])).all() #doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name IN (?, ?)
    ('ed', 'fakeuser')
    {stop}[<User(name='ed', fullname='Ed Jones', password='f8s7ccs')>]

.. _ormtutorial_querying:

Querying
========

A :class:`~sqlalchemy.orm.query.Query` object is created using the
:class:`~sqlalchemy.orm.session.Session.query()` method on
:class:`~sqlalchemy.orm.session.Session`. This function takes a variable
number of arguments, which can be any combination of classes and
class-instrumented descriptors. Below, we indicate a
:class:`~sqlalchemy.orm.query.Query` which loads ``User`` instances. When
evaluated in an iterative context, the list of ``User`` objects present is
returned:

.. sourcecode:: python+sql

    {sql}>>> for instance in session.query(User).order_by(User.id): # doctest: +NORMALIZE_WHITESPACE
    ...     print instance.name, instance.fullname
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users ORDER BY users.id
    ()
    {stop}ed Ed Jones
    wendy Wendy Williams
    mary Mary Contrary
    fred Fred Flinstone

The :class:`~sqlalchemy.orm.query.Query` also accepts ORM-instrumented
descriptors as arguments. Any time multiple class entities or column-based
entities are expressed as arguments to the
:class:`~sqlalchemy.orm.session.Session.query()` function, the return result
is expressed as tuples:

.. sourcecode:: python+sql

    {sql}>>> for name, fullname in session.query(User.name, User.fullname): # doctest: +NORMALIZE_WHITESPACE
    ...     print name, fullname
    SELECT users.name AS users_name,
            users.fullname AS users_fullname
    FROM users
    ()
    {stop}ed Ed Jones
    wendy Wendy Williams
    mary Mary Contrary
    fred Fred Flinstone

The tuples returned by :class:`~sqlalchemy.orm.query.Query` are *named*
tuples, supplied by the :class:`.KeyedTuple` class, and can be treated much like an
ordinary Python object. The names are
the same as the attribute's name for an attribute, and the class name for a
class:

.. sourcecode:: python+sql

    {sql}>>> for row in session.query(User, User.name).all(): #doctest: +NORMALIZE_WHITESPACE
    ...    print row.User, row.name
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    ()
    {stop}<User(name='ed', fullname='Ed Jones', password='f8s7ccs')> ed
    <User(name='wendy', fullname='Wendy Williams', password='foobar')> wendy
    <User(name='mary', fullname='Mary Contrary', password='xxg527')> mary
    <User(name='fred', fullname='Fred Flinstone', password='blah')> fred

You can control the names of individual column expressions using the
:meth:`~.ColumnElement.label` construct, which is available from
any :class:`.ColumnElement`-derived object, as well as any class attribute which
is mapped to one (such as ``User.name``):

.. sourcecode:: python+sql

    {sql}>>> for row in session.query(User.name.label('name_label')).all(): #doctest: +NORMALIZE_WHITESPACE
    ...    print(row.name_label)
    SELECT users.name AS name_label
    FROM users
    (){stop}
    ed
    wendy
    mary
    fred

The name given to a full entity such as ``User``, assuming that multiple
entities are present in the call to :meth:`~.Session.query`, can be controlled using
:func:`~.sqlalchemy.orm.aliased` :

.. sourcecode:: python+sql

    >>> from sqlalchemy.orm import aliased
    >>> user_alias = aliased(User, name='user_alias')

    {sql}>>> for row in session.query(user_alias, user_alias.name).all(): #doctest: +NORMALIZE_WHITESPACE
    ...    print row.user_alias
    SELECT user_alias.id AS user_alias_id,
            user_alias.name AS user_alias_name,
            user_alias.fullname AS user_alias_fullname,
            user_alias.password AS user_alias_password
    FROM users AS user_alias
    (){stop}
    <User(name='ed', fullname='Ed Jones', password='f8s7ccs')>
    <User(name='wendy', fullname='Wendy Williams', password='foobar')>
    <User(name='mary', fullname='Mary Contrary', password='xxg527')>
    <User(name='fred', fullname='Fred Flinstone', password='blah')>

Basic operations with :class:`~sqlalchemy.orm.query.Query` include issuing
LIMIT and OFFSET, most conveniently using Python array slices and typically in
conjunction with ORDER BY:

.. sourcecode:: python+sql

    {sql}>>> for u in session.query(User).order_by(User.id)[1:3]: #doctest: +NORMALIZE_WHITESPACE
    ...    print u
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users ORDER BY users.id
    LIMIT ? OFFSET ?
    (2, 1){stop}
    <User(name='wendy', fullname='Wendy Williams', password='foobar')>
    <User(name='mary', fullname='Mary Contrary', password='xxg527')>

and filtering results, which is accomplished either with
:func:`~sqlalchemy.orm.query.Query.filter_by`, which uses keyword arguments:

.. sourcecode:: python+sql

    {sql}>>> for name, in session.query(User.name).\
    ...             filter_by(fullname='Ed Jones'): # doctest: +NORMALIZE_WHITESPACE
    ...    print name
    SELECT users.name AS users_name FROM users
    WHERE users.fullname = ?
    ('Ed Jones',)
    {stop}ed

...or :func:`~sqlalchemy.orm.query.Query.filter`, which uses more flexible SQL
expression language constructs. These allow you to use regular Python
operators with the class-level attributes on your mapped class:

.. sourcecode:: python+sql

    {sql}>>> for name, in session.query(User.name).\
    ...             filter(User.fullname=='Ed Jones'): # doctest: +NORMALIZE_WHITESPACE
    ...    print name
    SELECT users.name AS users_name FROM users
    WHERE users.fullname = ?
    ('Ed Jones',)
    {stop}ed

The :class:`~sqlalchemy.orm.query.Query` object is fully **generative**, meaning
that most method calls return a new :class:`~sqlalchemy.orm.query.Query`
object upon which further criteria may be added. For example, to query for
users named "ed" with a full name of "Ed Jones", you can call
:func:`~sqlalchemy.orm.query.Query.filter` twice, which joins criteria using
``AND``:

.. sourcecode:: python+sql

    {sql}>>> for user in session.query(User).\
    ...          filter(User.name=='ed').\
    ...          filter(User.fullname=='Ed Jones'): # doctest: +NORMALIZE_WHITESPACE
    ...    print user
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name = ? AND users.fullname = ?
    ('ed', 'Ed Jones')
    {stop}<User(name='ed', fullname='Ed Jones', password='f8s7ccs')>

Common Filter Operators
-----------------------

Here's a rundown of some of the most common operators used in
:func:`~sqlalchemy.orm.query.Query.filter`:

* equals::

    query.filter(User.name == 'ed')

* not equals::

    query.filter(User.name != 'ed')

* LIKE::

    query.filter(User.name.like('%ed%'))

* IN::

    query.filter(User.name.in_(['ed', 'wendy', 'jack']))

    # works with query objects too:
    query.filter(User.name.in_(
            session.query(User.name).filter(User.name.like('%ed%'))
    ))

* NOT IN::

    query.filter(~User.name.in_(['ed', 'wendy', 'jack']))

* IS NULL::

    query.filter(User.name == None)

* IS NOT NULL::

    query.filter(User.name != None)

* AND::

    # use and_()
    from sqlalchemy import and_
    query.filter(and_(User.name == 'ed', User.fullname == 'Ed Jones'))

    # or send multiple expressions to .filter()
    query.filter(User.name == 'ed', User.fullname == 'Ed Jones')

    # or chain multiple filter()/filter_by() calls
    query.filter(User.name == 'ed').filter(User.fullname == 'Ed Jones')

* OR::

    from sqlalchemy import or_
    query.filter(or_(User.name == 'ed', User.name == 'wendy'))

* match::

    query.filter(User.name.match('wendy'))

 The contents of the match parameter are database backend specific.

Returning Lists and Scalars
---------------------------

A number of methods on :class:`.Query`
immediately issue SQL and return a value containing loaded
database results.  Here's a brief tour:

* :meth:`~.Query.all()` returns a list:

  .. sourcecode:: python+sql

      >>> query = session.query(User).filter(User.name.like('%ed')).order_by(User.id)
      {sql}>>> query.all() #doctest: +NORMALIZE_WHITESPACE
      SELECT users.id AS users_id,
              users.name AS users_name,
              users.fullname AS users_fullname,
              users.password AS users_password
      FROM users
      WHERE users.name LIKE ? ORDER BY users.id
      ('%ed',)
      {stop}[<User(name='ed', fullname='Ed Jones', password='f8s7ccs')>,
            <User(name='fred', fullname='Fred Flinstone', password='blah')>]

* :meth:`~.Query.first()` applies a limit of one and returns
  the first result as a scalar:

  .. sourcecode:: python+sql

      {sql}>>> query.first() #doctest: +NORMALIZE_WHITESPACE
      SELECT users.id AS users_id,
              users.name AS users_name,
              users.fullname AS users_fullname,
              users.password AS users_password
      FROM users
      WHERE users.name LIKE ? ORDER BY users.id
       LIMIT ? OFFSET ?
      ('%ed', 1, 0)
      {stop}<User(name='ed', fullname='Ed Jones', password='f8s7ccs')>

* :meth:`~.Query.one()`, fully fetches all rows, and if not
  exactly one object identity or composite row is present in the result, raises
  an error.  With multiple rows found:

  .. sourcecode:: python+sql

      {sql}>>> from sqlalchemy.orm.exc import MultipleResultsFound
      >>> try: #doctest: +NORMALIZE_WHITESPACE
      ...     user = query.one()
      ... except MultipleResultsFound, e:
      ...     print e
      SELECT users.id AS users_id,
              users.name AS users_name,
              users.fullname AS users_fullname,
              users.password AS users_password
      FROM users
      WHERE users.name LIKE ? ORDER BY users.id
      ('%ed',)
      {stop}Multiple rows were found for one()

  With no rows found:

  .. sourcecode:: python+sql

      {sql}>>> from sqlalchemy.orm.exc import NoResultFound
      >>> try: #doctest: +NORMALIZE_WHITESPACE
      ...     user = query.filter(User.id == 99).one()
      ... except NoResultFound, e:
      ...     print e
      SELECT users.id AS users_id,
              users.name AS users_name,
              users.fullname AS users_fullname,
              users.password AS users_password
      FROM users
      WHERE users.name LIKE ? AND users.id = ? ORDER BY users.id
      ('%ed', 99)
      {stop}No row was found for one()

  The :meth:`~.Query.one` method is great for systems that expect to handle
  "no items found" versus "multiple items found" differently; such as a RESTful
  web service, which may want to raise a "404 not found" when no results are found,
  but raise an application error when multiple results are found.

* :meth:`~.Query.scalar` invokes the :meth:`~.Query.one` method, and upon
  success returns the first column of the row:

  .. sourcecode:: python+sql

      >>> query = session.query(User.id).filter(User.name.like('%ed')).\
      ...    order_by(User.id)
      {sql}>>> query.scalar() #doctest: +NORMALIZE_WHITESPACE
      SELECT users.id AS users_id
      FROM users
      WHERE users.name LIKE ? ORDER BY users.id
       LIMIT ? OFFSET ?
      ('%ed', 1, 0)
      {stop}7

.. _orm_tutorial_literal_sql:

Using Literal SQL
-----------------

Literal strings can be used flexibly with
:class:`~sqlalchemy.orm.query.Query`. Most methods accept strings in addition
to SQLAlchemy clause constructs. For example,
:meth:`~sqlalchemy.orm.query.Query.filter()` and
:meth:`~sqlalchemy.orm.query.Query.order_by()`:

.. sourcecode:: python+sql

    {sql}>>> for user in session.query(User).\
    ...             filter("id<224").\
    ...             order_by("id").all(): #doctest: +NORMALIZE_WHITESPACE
    ...     print user.name
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE id<224 ORDER BY id
    ()
    {stop}ed
    wendy
    mary
    fred

Bind parameters can be specified with string-based SQL, using a colon. To
specify the values, use the :meth:`~sqlalchemy.orm.query.Query.params()`
method:

.. sourcecode:: python+sql

    {sql}>>> session.query(User).filter("id<:value and name=:name").\
    ...     params(value=224, name='fred').order_by(User.id).one() # doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE id<? and name=? ORDER BY users.id
    (224, 'fred')
    {stop}<User(name='fred', fullname='Fred Flinstone', password='blah')>

To use an entirely string-based statement, using
:meth:`~sqlalchemy.orm.query.Query.from_statement()`; just ensure that the
columns clause of the statement contains the column names normally used by the
mapper (below illustrated using an asterisk):

.. sourcecode:: python+sql

    {sql}>>> session.query(User).from_statement(
    ...                     "SELECT * FROM users where name=:name").\
    ...                     params(name='ed').all()
    SELECT * FROM users where name=?
    ('ed',)
    {stop}[<User(name='ed', fullname='Ed Jones', password='f8s7ccs')>]

You can use :meth:`~sqlalchemy.orm.query.Query.from_statement()` to go
completely "raw", using string names to identify desired columns:

.. sourcecode:: python+sql

    {sql}>>> session.query("id", "name", "thenumber12").\
    ...         from_statement("SELECT id, name, 12 as "
    ...                 "thenumber12 FROM users where name=:name").\
    ...                 params(name='ed').all()
    SELECT id, name, 12 as thenumber12 FROM users where name=?
    ('ed',)
    {stop}[(1, u'ed', 12)]

.. topic:: Pros and Cons of Literal SQL

   :class:`.Query` is constructed like the rest of SQLAlchemy, in that it tries
   to always allow "falling back" to a less automated, lower level approach to things.
   Accepting strings for all SQL fragments is a big part of that, so that
   you can bypass the need to organize SQL constructs if you know specifically
   what string output you'd like.
   But when using literal strings, the :class:`.Query` no longer knows anything about
   that part of the SQL construct being emitted, and has no ability to
   **transform** it to adapt to new contexts.

   For example, suppose we selected ``User`` objects and ordered by the ``name``
   column, using a string to indicate ``name``:

   .. sourcecode:: python+sql

       >>> q = session.query(User.id, User.name)
       {sql}>>> q.order_by("name").all()
       SELECT users.id AS users_id, users.name AS users_name
       FROM users ORDER BY name
       ()
       {stop}[(1, u'ed'), (4, u'fred'), (3, u'mary'), (2, u'wendy')]

   Perfectly fine.  But suppose, before we got a hold of the :class:`.Query`,
   some sophisticated transformations were applied to it, such as below
   where we use :meth:`~.Query.from_self`, a particularly advanced
   method, to retrieve pairs of user names with
   different numbers of characters::

        >>> from sqlalchemy import func
        >>> ua = aliased(User)
        >>> q = q.from_self(User.id, User.name, ua.name).\
        ...     filter(User.name < ua.name).\
        ...     filter(func.length(ua.name) != func.length(User.name))

   The :class:`.Query` now represents a select from a subquery, where
   ``User`` is represented twice both inside and outside of the subquery.
   Telling the :class:`.Query` to order by "name" doesn't really give
   us much guarantee which "name" it's going to order on.  In this
   case it assumes "name" is against the outer "aliased" ``User`` construct:

   .. sourcecode:: python+sql

       {sql}>>> q.order_by("name").all() #doctest: +NORMALIZE_WHITESPACE
       SELECT anon_1.users_id AS anon_1_users_id,
                anon_1.users_name AS anon_1_users_name,
                users_1.name AS users_1_name
       FROM (SELECT users.id AS users_id, users.name AS users_name
            FROM users) AS anon_1, users AS users_1
       WHERE anon_1.users_name < users_1.name
            AND length(users_1.name) != length(anon_1.users_name)
       ORDER BY name
       ()
       {stop}[(1, u'ed', u'fred'), (1, u'ed', u'mary'), (1, u'ed', u'wendy'), (3, u'mary', u'wendy'), (4, u'fred', u'wendy')]

   Only if we use the SQL element directly, in this case ``User.name``
   or ``ua.name``, do we give :class:`.Query` enough information to know
   for sure which "name" we'd like to order on, where we can see we get different results
   for each:

   .. sourcecode:: python+sql

       {sql}>>> q.order_by(ua.name).all() #doctest: +NORMALIZE_WHITESPACE
       SELECT anon_1.users_id AS anon_1_users_id,
                anon_1.users_name AS anon_1_users_name,
                users_1.name AS users_1_name
       FROM (SELECT users.id AS users_id, users.name AS users_name
            FROM users) AS anon_1, users AS users_1
       WHERE anon_1.users_name < users_1.name
            AND length(users_1.name) != length(anon_1.users_name)
       ORDER BY users_1.name
       ()
       {stop}[(1, u'ed', u'fred'), (1, u'ed', u'mary'), (1, u'ed', u'wendy'), (3, u'mary', u'wendy'), (4, u'fred', u'wendy')]

       {sql}>>> q.order_by(User.name).all() #doctest: +NORMALIZE_WHITESPACE
       SELECT anon_1.users_id AS anon_1_users_id,
                anon_1.users_name AS anon_1_users_name,
                users_1.name AS users_1_name
       FROM (SELECT users.id AS users_id, users.name AS users_name
            FROM users) AS anon_1, users AS users_1
       WHERE anon_1.users_name < users_1.name
            AND length(users_1.name) != length(anon_1.users_name)
       ORDER BY anon_1.users_name
       ()
       {stop}[(1, u'ed', u'wendy'), (1, u'ed', u'mary'), (1, u'ed', u'fred'), (4, u'fred', u'wendy'), (3, u'mary', u'wendy')]

Counting
--------

:class:`~sqlalchemy.orm.query.Query` includes a convenience method for
counting called :meth:`~sqlalchemy.orm.query.Query.count()`:

.. sourcecode:: python+sql

    {sql}>>> session.query(User).filter(User.name.like('%ed')).count() #doctest: +NORMALIZE_WHITESPACE
    SELECT count(*) AS count_1
    FROM (SELECT users.id AS users_id,
                    users.name AS users_name,
                    users.fullname AS users_fullname,
                    users.password AS users_password
    FROM users
    WHERE users.name LIKE ?) AS anon_1
    ('%ed',)
    {stop}2

.. sidebar:: Counting on ``count()``

    :meth:`.Query.count` used to be a very complicated method
    when it would try to guess whether or not a subquery was needed
    around the
    existing query, and in some exotic cases it wouldn't do the right thing.
    Now that it uses a simple subquery every time, it's only two lines long
    and always returns the right answer.  Use ``func.count()`` if a
    particular statement absolutely cannot tolerate the subquery being present.

The :meth:`~.Query.count()` method is used to determine
how many rows the SQL statement would return.   Looking
at the generated SQL above, SQLAlchemy always places whatever it is we are
querying into a subquery, then counts the rows from that.   In some cases
this can be reduced to a simpler ``SELECT count(*) FROM table``, however
modern versions of SQLAlchemy don't try to guess when this is appropriate,
as the exact SQL can be emitted using more explicit means.

For situations where the "thing to be counted" needs
to be indicated specifically, we can specify the "count" function
directly using the expression ``func.count()``, available from the
:attr:`~sqlalchemy.sql.expression.func` construct.  Below we
use it to return the count of each distinct user name:

.. sourcecode:: python+sql

    >>> from sqlalchemy import func
    {sql}>>> session.query(func.count(User.name), User.name).group_by(User.name).all()  #doctest: +NORMALIZE_WHITESPACE
    SELECT count(users.name) AS count_1, users.name AS users_name
    FROM users GROUP BY users.name
    ()
    {stop}[(1, u'ed'), (1, u'fred'), (1, u'mary'), (1, u'wendy')]

To achieve our simple ``SELECT count(*) FROM table``, we can apply it as:

.. sourcecode:: python+sql

    {sql}>>> session.query(func.count('*')).select_from(User).scalar()
    SELECT count(?) AS count_1
    FROM users
    ('*',)
    {stop}4

The usage of :meth:`~.Query.select_from` can be removed if we express the count in terms
of the ``User`` primary key directly:

.. sourcecode:: python+sql

    {sql}>>> session.query(func.count(User.id)).scalar() #doctest: +NORMALIZE_WHITESPACE
    SELECT count(users.id) AS count_1
    FROM users
    ()
    {stop}4

Building a Relationship
=======================

Let's consider how a second table, related to ``User``, can be mapped and
queried.  Users in our system
can store any number of email addresses associated with their username. This
implies a basic one to many association from the ``users`` to a new
table which stores email addresses, which we will call ``addresses``. Using
declarative, we define this table along with its mapped class, ``Address``:

.. sourcecode:: python+sql

    >>> from sqlalchemy import ForeignKey
    >>> from sqlalchemy.orm import relationship, backref

    >>> class Address(Base):
    ...     __tablename__ = 'addresses'
    ...     id = Column(Integer, primary_key=True)
    ...     email_address = Column(String, nullable=False)
    ...     user_id = Column(Integer, ForeignKey('users.id'))
    ...
    ...     user = relationship("User", backref=backref('addresses', order_by=id))
    ...
    ...     def __repr__(self):
    ...         return "<Address(email_address='%s')>" % self.email_address

The above class introduces the :class:`.ForeignKey` construct, which is a
directive applied to :class:`.Column` that indicates that values in this
column should be :term:`constrained` to be values present in the named remote
column. This is a core feature of relational databases, and is the "glue" that
transforms an otherwise unconnected collection of tables to have rich
overlapping relationships. The :class:`.ForeignKey` above expresses that
values in the ``addresses.user_id`` column should be constrained to
those values in the ``users.id`` column, i.e. its primary key.

A second directive, known as :func:`.relationship`,
tells the ORM that the ``Address`` class itself should be linked
to the ``User`` class, using the attribute ``Address.user``.
:func:`.relationship` uses the foreign key
relationships between the two tables to determine the nature of
this linkage, determining that ``Address.user`` will be :term:`many to one`.
A subdirective of :func:`.relationship` called :func:`.backref` is
placed inside of :func:`.relationship`, providing details about
the relationship as expressed in reverse, that of a collection of ``Address``
objects on ``User`` referenced by ``User.addresses``.  The reverse
side of a many-to-one relationship is always :term:`one to many`.
A full catalog of available :func:`.relationship` configurations
is at :ref:`relationship_patterns`.

The two complementing relationships ``Address.user`` and ``User.addresses``
are referred to as a :term:`bidirectional relationship`, and is a key
feature of the SQLAlchemy ORM.   The section :ref:`relationships_backref`
discusses the "backref" feature in detail.

Arguments to :func:`.relationship` which concern the remote class
can be specified using strings, assuming the Declarative system is in
use.   Once all mappings are complete, these strings are evaluated
as Python expressions in order to produce the actual argument, in the
above case the ``User`` class.   The names which are allowed during
this evaluation include, among other things, the names of all classes
which have been created in terms of the declared base.  Below we illustrate creation
of the same "addresses/user" bidirectional relationship in terms of ``User`` instead of
``Address``::

    class User(Base):
        # ....
        addresses = relationship("Address", order_by="Address.id", backref="user")

See the docstring for :func:`.relationship` for more detail on argument style.

.. topic:: Did you know ?

    * a FOREIGN KEY constraint in most (though not all) relational databases can
      only link to a primary key column, or a column that has a UNIQUE constraint.
    * a FOREIGN KEY constraint that refers to a multiple column primary key, and itself
      has multiple columns, is known as a "composite foreign key".  It can also
      reference a subset of those columns.
    * FOREIGN KEY columns can automatically update themselves, in response to a change
      in the referenced column or row.  This is known as the CASCADE *referential action*,
      and is a built in function of the relational database.
    * FOREIGN KEY can refer to its own table.  This is referred to as a "self-referential"
      foreign key.
    * Read more about foreign keys at `Foreign Key - Wikipedia <http://en.wikipedia.org/wiki/Foreign_key>`_.

We'll need to create the ``addresses`` table in the database, so we will issue
another CREATE from our metadata, which will skip over tables which have
already been created:

.. sourcecode:: python+sql

    {sql}>>> Base.metadata.create_all(engine) # doctest: +NORMALIZE_WHITESPACE
    PRAGMA table_info("users")
    ()
    PRAGMA table_info("addresses")
    ()
    CREATE TABLE addresses (
        id INTEGER NOT NULL,
        email_address VARCHAR NOT NULL,
        user_id INTEGER,
        PRIMARY KEY (id),
         FOREIGN KEY(user_id) REFERENCES users (id)
    )
    ()
    COMMIT

Working with Related Objects
=============================

Now when we create a ``User``, a blank ``addresses`` collection will be
present. Various collection types, such as sets and dictionaries, are possible
here (see :ref:`custom_collections` for details), but by
default, the collection is a Python list.

.. sourcecode:: python+sql

    >>> jack = User(name='jack', fullname='Jack Bean', password='gjffdd')
    >>> jack.addresses
    []

We are free to add ``Address`` objects on our ``User`` object. In this case we
just assign a full list directly:

.. sourcecode:: python+sql

    >>> jack.addresses = [
    ...                 Address(email_address='jack@google.com'),
    ...                 Address(email_address='j25@yahoo.com')]

When using a bidirectional relationship, elements added in one direction
automatically become visible in the other direction.  This behavior occurs
based on attribute on-change events and is evaluated in Python, without
using any SQL:

.. sourcecode:: python+sql

    >>> jack.addresses[1]
    <Address(email_address='j25@yahoo.com')>

    >>> jack.addresses[1].user
    <User(name='jack', fullname='Jack Bean', password='gjffdd')>

Let's add and commit ``Jack Bean`` to the database. ``jack`` as well
as the two ``Address`` members in the corresponding ``addresses``
collection are both added to the session at once, using a process
known as **cascading**:

.. sourcecode:: python+sql

    >>> session.add(jack)
    {sql}>>> session.commit()
    INSERT INTO users (name, fullname, password) VALUES (?, ?, ?)
    ('jack', 'Jack Bean', 'gjffdd')
    INSERT INTO addresses (email_address, user_id) VALUES (?, ?)
    ('jack@google.com', 5)
    INSERT INTO addresses (email_address, user_id) VALUES (?, ?)
    ('j25@yahoo.com', 5)
    COMMIT

Querying for Jack, we get just Jack back.  No SQL is yet issued for Jack's addresses:

.. sourcecode:: python+sql

    {sql}>>> jack = session.query(User).\
    ... filter_by(name='jack').one() #doctest: +NORMALIZE_WHITESPACE
    BEGIN (implicit)
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name = ?
    ('jack',)

    {stop}>>> jack
    <User(name='jack', fullname='Jack Bean', password='gjffdd')>

Let's look at the ``addresses`` collection.  Watch the SQL:

.. sourcecode:: python+sql

    {sql}>>> jack.addresses #doctest: +NORMALIZE_WHITESPACE
    SELECT addresses.id AS addresses_id,
            addresses.email_address AS
            addresses_email_address,
            addresses.user_id AS addresses_user_id
    FROM addresses
    WHERE ? = addresses.user_id ORDER BY addresses.id
    (5,)
    {stop}[<Address(email_address='jack@google.com')>, <Address(email_address='j25@yahoo.com')>]

When we accessed the ``addresses`` collection, SQL was suddenly issued. This
is an example of a :term:`lazy loading` relationship.  The ``addresses`` collection
is now loaded and behaves just like an ordinary list.  We'll cover ways
to optimize the loading of this collection in a bit.

.. _ormtutorial_joins:

Querying with Joins
====================

Now that we have two tables, we can show some more features of :class:`.Query`,
specifically how to create queries that deal with both tables at the same time.
The `Wikipedia page on SQL JOIN
<http://en.wikipedia.org/wiki/Join_%28SQL%29>`_ offers a good introduction to
join techniques, several of which we'll illustrate here.

To construct a simple implicit join between ``User`` and ``Address``,
we can use :meth:`.Query.filter()` to equate their related columns together.
Below we load the ``User`` and ``Address`` entities at once using this method:

.. sourcecode:: python+sql

    {sql}>>> for u, a in session.query(User, Address).\
    ...                     filter(User.id==Address.user_id).\
    ...                     filter(Address.email_address=='jack@google.com').\
    ...                     all():   # doctest: +NORMALIZE_WHITESPACE
    ...     print u
    ...     print a
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password,
            addresses.id AS addresses_id,
            addresses.email_address AS addresses_email_address,
            addresses.user_id AS addresses_user_id
    FROM users, addresses
    WHERE users.id = addresses.user_id
            AND addresses.email_address = ?
    ('jack@google.com',)
    {stop}<User(name='jack', fullname='Jack Bean', password='gjffdd')>
    <Address(email_address='jack@google.com')>

The actual SQL JOIN syntax, on the other hand, is most easily achieved
using the :meth:`.Query.join` method:

.. sourcecode:: python+sql

    {sql}>>> session.query(User).join(Address).\
    ...         filter(Address.email_address=='jack@google.com').\
    ...         all() #doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users JOIN addresses ON users.id = addresses.user_id
    WHERE addresses.email_address = ?
    ('jack@google.com',)
    {stop}[<User(name='jack', fullname='Jack Bean', email_address='gjffdd')>]

:meth:`.Query.join` knows how to join between ``User``
and ``Address`` because there's only one foreign key between them. If there
were no foreign keys, or several, :meth:`.Query.join`
works better when one of the following forms are used::

    query.join(Address, User.id==Address.user_id)    # explicit condition
    query.join(User.addresses)                       # specify relationship from left to right
    query.join(Address, User.addresses)              # same, with explicit target
    query.join('addresses')                          # same, using a string

As you would expect, the same idea is used for "outer" joins, using the
:meth:`~.Query.outerjoin` function::

    query.outerjoin(User.addresses)   # LEFT OUTER JOIN

The reference documentation for :meth:`~.Query.join` contains detailed information
and examples of the calling styles accepted by this method; :meth:`~.Query.join`
is an important method at the center of usage for any SQL-fluent application.

.. _ormtutorial_aliases:

Using Aliases
-------------

When querying across multiple tables, if the same table needs to be referenced
more than once, SQL typically requires that the table be *aliased* with
another name, so that it can be distinguished against other occurrences of
that table. The :class:`~sqlalchemy.orm.query.Query` supports this most
explicitly using the :attr:`~sqlalchemy.orm.aliased` construct. Below we join to the ``Address``
entity twice, to locate a user who has two distinct email addresses at the
same time:

.. sourcecode:: python+sql

    >>> from sqlalchemy.orm import aliased
    >>> adalias1 = aliased(Address)
    >>> adalias2 = aliased(Address)
    {sql}>>> for username, email1, email2 in \
    ...     session.query(User.name, adalias1.email_address, adalias2.email_address).\
    ...     join(adalias1, User.addresses).\
    ...     join(adalias2, User.addresses).\
    ...     filter(adalias1.email_address=='jack@google.com').\
    ...     filter(adalias2.email_address=='j25@yahoo.com'):
    ...     print username, email1, email2      # doctest: +NORMALIZE_WHITESPACE
    SELECT users.name AS users_name,
            addresses_1.email_address AS addresses_1_email_address,
            addresses_2.email_address AS addresses_2_email_address
    FROM users JOIN addresses AS addresses_1
            ON users.id = addresses_1.user_id
    JOIN addresses AS addresses_2
            ON users.id = addresses_2.user_id
    WHERE addresses_1.email_address = ?
            AND addresses_2.email_address = ?
    ('jack@google.com', 'j25@yahoo.com')
    {stop}jack jack@google.com j25@yahoo.com

Using Subqueries
----------------

The :class:`~sqlalchemy.orm.query.Query` is suitable for generating statements
which can be used as subqueries. Suppose we wanted to load ``User`` objects
along with a count of how many ``Address`` records each user has. The best way
to generate SQL like this is to get the count of addresses grouped by user
ids, and JOIN to the parent. In this case we use a LEFT OUTER JOIN so that we
get rows back for those users who don't have any addresses, e.g.::

    SELECT users.*, adr_count.address_count FROM users LEFT OUTER JOIN
        (SELECT user_id, count(*) AS address_count
            FROM addresses GROUP BY user_id) AS adr_count
        ON users.id=adr_count.user_id

Using the :class:`~sqlalchemy.orm.query.Query`, we build a statement like this
from the inside out. The ``statement`` accessor returns a SQL expression
representing the statement generated by a particular
:class:`~sqlalchemy.orm.query.Query` - this is an instance of a :func:`~.expression.select`
construct, which are described in :ref:`sqlexpression_toplevel`::

    >>> from sqlalchemy.sql import func
    >>> stmt = session.query(Address.user_id, func.count('*').\
    ...         label('address_count')).\
    ...         group_by(Address.user_id).subquery()

The ``func`` keyword generates SQL functions, and the ``subquery()`` method on
:class:`~sqlalchemy.orm.query.Query` produces a SQL expression construct
representing a SELECT statement embedded within an alias (it's actually
shorthand for ``query.statement.alias()``).

Once we have our statement, it behaves like a
:class:`~sqlalchemy.schema.Table` construct, such as the one we created for
``users`` at the start of this tutorial. The columns on the statement are
accessible through an attribute called ``c``:

.. sourcecode:: python+sql

    {sql}>>> for u, count in session.query(User, stmt.c.address_count).\
    ...     outerjoin(stmt, User.id==stmt.c.user_id).order_by(User.id): # doctest: +NORMALIZE_WHITESPACE
    ...     print u, count
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password,
            anon_1.address_count AS anon_1_address_count
    FROM users LEFT OUTER JOIN
        (SELECT addresses.user_id AS user_id, count(?) AS address_count
        FROM addresses GROUP BY addresses.user_id) AS anon_1
        ON users.id = anon_1.user_id
    ORDER BY users.id
    ('*',)
    {stop}<User(name='ed', fullname='Ed Jones', password='f8s7ccs')> None
    <User(name='wendy', fullname='Wendy Williams', password='foobar')> None
    <User(name='mary', fullname='Mary Contrary', password='xxg527')> None
    <User(name='fred', fullname='Fred Flinstone', password='blah')> None
    <User(name='jack', fullname='Jack Bean', password='gjffdd')> 2

Selecting Entities from Subqueries
----------------------------------

Above, we just selected a result that included a column from a subquery. What
if we wanted our subquery to map to an entity ? For this we use ``aliased()``
to associate an "alias" of a mapped class to a subquery:

.. sourcecode:: python+sql

    {sql}>>> stmt = session.query(Address).\
    ...                 filter(Address.email_address != 'j25@yahoo.com').\
    ...                 subquery()
    >>> adalias = aliased(Address, stmt)
    >>> for user, address in session.query(User, adalias).\
    ...         join(adalias, User.addresses): # doctest: +NORMALIZE_WHITESPACE
    ...     print user
    ...     print address
    SELECT users.id AS users_id,
                users.name AS users_name,
                users.fullname AS users_fullname,
                users.password AS users_password,
                anon_1.id AS anon_1_id,
                anon_1.email_address AS anon_1_email_address,
                anon_1.user_id AS anon_1_user_id
    FROM users JOIN
        (SELECT addresses.id AS id,
                addresses.email_address AS email_address,
                addresses.user_id AS user_id
        FROM addresses
        WHERE addresses.email_address != ?) AS anon_1
        ON users.id = anon_1.user_id
    ('j25@yahoo.com',)
    {stop}<User(name='jack', fullname='Jack Bean', password='gjffdd')>
    <Address(email_address='jack@google.com')>

Using EXISTS
------------

The EXISTS keyword in SQL is a boolean operator which returns True if the
given expression contains any rows. It may be used in many scenarios in place
of joins, and is also useful for locating rows which do not have a
corresponding row in a related table.

There is an explicit EXISTS construct, which looks like this:

.. sourcecode:: python+sql

    >>> from sqlalchemy.sql import exists
    >>> stmt = exists().where(Address.user_id==User.id)
    {sql}>>> for name, in session.query(User.name).filter(stmt):   # doctest: +NORMALIZE_WHITESPACE
    ...     print name
    SELECT users.name AS users_name
    FROM users
    WHERE EXISTS (SELECT *
    FROM addresses
    WHERE addresses.user_id = users.id)
    ()
    {stop}jack

The :class:`~sqlalchemy.orm.query.Query` features several operators which make
usage of EXISTS automatically. Above, the statement can be expressed along the
``User.addresses`` relationship using :meth:`~.RelationshipProperty.Comparator.any`:

.. sourcecode:: python+sql

    {sql}>>> for name, in session.query(User.name).\
    ...         filter(User.addresses.any()):   # doctest: +NORMALIZE_WHITESPACE
    ...     print name
    SELECT users.name AS users_name
    FROM users
    WHERE EXISTS (SELECT 1
    FROM addresses
    WHERE users.id = addresses.user_id)
    ()
    {stop}jack

:meth:`~.RelationshipProperty.Comparator.any` takes criterion as well, to limit the rows matched:

.. sourcecode:: python+sql

    {sql}>>> for name, in session.query(User.name).\
    ...     filter(User.addresses.any(Address.email_address.like('%google%'))):   # doctest: +NORMALIZE_WHITESPACE
    ...     print name
    SELECT users.name AS users_name
    FROM users
    WHERE EXISTS (SELECT 1
    FROM addresses
    WHERE users.id = addresses.user_id AND addresses.email_address LIKE ?)
    ('%google%',)
    {stop}jack

:meth:`~.RelationshipProperty.Comparator.has` is the same operator as
:meth:`~.RelationshipProperty.Comparator.any` for many-to-one relationships
(note the ``~`` operator here too, which means "NOT"):

.. sourcecode:: python+sql

    {sql}>>> session.query(Address).\
    ...         filter(~Address.user.has(User.name=='jack')).all() # doctest: +NORMALIZE_WHITESPACE
    SELECT addresses.id AS addresses_id,
            addresses.email_address AS addresses_email_address,
            addresses.user_id AS addresses_user_id
    FROM addresses
    WHERE NOT (EXISTS (SELECT 1
    FROM users
    WHERE users.id = addresses.user_id AND users.name = ?))
    ('jack',)
    {stop}[]

Common Relationship Operators
-----------------------------

Here's all the operators which build on relationships - each one
is linked to its API documentation which includes full details on usage
and behavior:

* :meth:`~.RelationshipProperty.Comparator.__eq__` (many-to-one "equals" comparison)::

    query.filter(Address.user == someuser)

* :meth:`~.RelationshipProperty.Comparator.__ne__` (many-to-one "not equals" comparison)::

    query.filter(Address.user != someuser)

* IS NULL (many-to-one comparison, also uses :meth:`~.RelationshipProperty.Comparator.__eq__`)::

    query.filter(Address.user == None)

* :meth:`~.RelationshipProperty.Comparator.contains` (used for one-to-many collections)::

    query.filter(User.addresses.contains(someaddress))

* :meth:`~.RelationshipProperty.Comparator.any` (used for collections)::

    query.filter(User.addresses.any(Address.email_address == 'bar'))

    # also takes keyword arguments:
    query.filter(User.addresses.any(email_address='bar'))

* :meth:`~.RelationshipProperty.Comparator.has` (used for scalar references)::

    query.filter(Address.user.has(name='ed'))

* :meth:`.Query.with_parent` (used for any relationship)::

    session.query(Address).with_parent(someuser, 'addresses')

Eager Loading
=============

Recall earlier that we illustrated a :term:`lazy loading` operation, when
we accessed the ``User.addresses`` collection of a ``User`` and SQL
was emitted.  If you want to reduce the number of queries (dramatically, in many cases),
we can apply an :term:`eager load` to the query operation.   SQLAlchemy
offers three types of eager loading, two of which are automatic, and a third
which involves custom criterion.   All three are usually invoked via functions known
as :term:`query options` which give additional instructions to the :class:`.Query` on how
we would like various attributes to be loaded, via the :meth:`.Query.options` method.

Subquery Load
-------------

In this case we'd like to indicate that ``User.addresses`` should load eagerly.
A good choice for loading a set of objects as well as their related collections
is the :func:`.orm.subqueryload` option, which emits a second SELECT statement
that fully loads the collections associated with the results just loaded.
The name "subquery" originates from the fact that the SELECT statement
constructed directly via the :class:`.Query` is re-used, embedded as a subquery
into a SELECT against the related table.   This is a little elaborate but
very easy to use:

.. sourcecode:: python+sql

    >>> from sqlalchemy.orm import subqueryload
    {sql}>>> jack = session.query(User).\
    ...                 options(subqueryload(User.addresses)).\
    ...                 filter_by(name='jack').one() #doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name = ?
    ('jack',)
    SELECT addresses.id AS addresses_id,
            addresses.email_address AS addresses_email_address,
            addresses.user_id AS addresses_user_id,
            anon_1.users_id AS anon_1_users_id
    FROM (SELECT users.id AS users_id
        FROM users WHERE users.name = ?) AS anon_1
    JOIN addresses ON anon_1.users_id = addresses.user_id
    ORDER BY anon_1.users_id, addresses.id
    ('jack',)
    {stop}>>> jack
    <User(name='jack', fullname='Jack Bean', password='gjffdd')>

    >>> jack.addresses
    [<Address(email_address='jack@google.com')>, <Address(email_address='j25@yahoo.com')>]

Joined Load
-------------

The other automatic eager loading function is more well known and is called
:func:`.orm.joinedload`.   This style of loading emits a JOIN, by default
a LEFT OUTER JOIN, so that the lead object as well as the related object
or collection is loaded in one step.   We illustrate loading the same
``addresses`` collection in this way - note that even though the ``User.addresses``
collection on ``jack`` is actually populated right now, the query
will emit the extra join regardless:

.. sourcecode:: python+sql

    >>> from sqlalchemy.orm import joinedload

    {sql}>>> jack = session.query(User).\
    ...                        options(joinedload(User.addresses)).\
    ...                        filter_by(name='jack').one() #doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password,
            addresses_1.id AS addresses_1_id,
            addresses_1.email_address AS addresses_1_email_address,
            addresses_1.user_id AS addresses_1_user_id
    FROM users
        LEFT OUTER JOIN addresses AS addresses_1 ON users.id = addresses_1.user_id
    WHERE users.name = ? ORDER BY addresses_1.id
    ('jack',)

    {stop}>>> jack
    <User(name='jack', fullname='Jack Bean', password='gjffdd')>

    >>> jack.addresses
    [<Address(email_address='jack@google.com')>, <Address(email_address='j25@yahoo.com')>]

Note that even though the OUTER JOIN resulted in two rows, we still only got
one instance of ``User`` back.  This is because :class:`.Query` applies a "uniquing"
strategy, based on object identity, to the returned entities.  This is specifically
so that joined eager loading can be applied without affecting the query results.

While :func:`.joinedload` has been around for a long time, :func:`.subqueryload`
is a newer form of eager loading.   :func:`.subqueryload` tends to be more appropriate
for loading related collections while :func:`.joinedload` tends to be better suited
for many-to-one relationships, due to the fact that only one row is loaded
for both the lead and the related object.

.. topic:: ``joinedload()`` is not a replacement for ``join()``

   The join created by :func:`.joinedload` is anonymously aliased such that
   it **does not affect the query results**.   An :meth:`.Query.order_by`
   or :meth:`.Query.filter` call **cannot** reference these aliased
   tables - so-called "user space" joins are constructed using
   :meth:`.Query.join`.   The rationale for this is that :func:`.joinedload` is only
   applied in order to affect how related objects or collections are loaded
   as an optimizing detail - it can be added or removed with no impact
   on actual results.   See the section :ref:`zen_of_eager_loading` for
   a detailed description of how this is used.

Explicit Join + Eagerload
--------------------------

A third style of eager loading is when we are constructing a JOIN explicitly in
order to locate the primary rows, and would like to additionally apply the extra
table to a related object or collection on the primary object.   This feature
is supplied via the :func:`.orm.contains_eager` function, and is most
typically useful for pre-loading the many-to-one object on a query that needs
to filter on that same object.  Below we illustrate loading an ``Address``
row as well as the related ``User`` object, filtering on the ``User`` named
"jack" and using :func:`.orm.contains_eager` to apply the "user" columns to the ``Address.user``
attribute:

.. sourcecode:: python+sql

    >>> from sqlalchemy.orm import contains_eager
    {sql}>>> jacks_addresses = session.query(Address).\
    ...                             join(Address.user).\
    ...                             filter(User.name=='jack').\
    ...                             options(contains_eager(Address.user)).\
    ...                             all() #doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password,
            addresses.id AS addresses_id,
            addresses.email_address AS addresses_email_address,
            addresses.user_id AS addresses_user_id
    FROM addresses JOIN users ON users.id = addresses.user_id
    WHERE users.name = ?
    ('jack',)

    {stop}>>> jacks_addresses
    [<Address(email_address='jack@google.com')>, <Address(email_address='j25@yahoo.com')>]

    >>> jacks_addresses[0].user
    <User(name='jack', fullname='Jack Bean', password='gjffdd')>

For more information on eager loading, including how to configure various forms
of loading by default, see the section :doc:`/orm/loading`.

Deleting
========

Let's try to delete ``jack`` and see how that goes. We'll mark as deleted in
the session, then we'll issue a ``count`` query to see that no rows remain:

.. sourcecode:: python+sql

    >>> session.delete(jack)
    {sql}>>> session.query(User).filter_by(name='jack').count() # doctest: +NORMALIZE_WHITESPACE
    UPDATE addresses SET user_id=? WHERE addresses.id = ?
    (None, 1)
    UPDATE addresses SET user_id=? WHERE addresses.id = ?
    (None, 2)
    DELETE FROM users WHERE users.id = ?
    (5,)
    SELECT count(*) AS count_1
    FROM (SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name = ?) AS anon_1
    ('jack',)
    {stop}0

So far, so good.  How about Jack's ``Address`` objects ?

.. sourcecode:: python+sql

    {sql}>>> session.query(Address).filter(
    ...     Address.email_address.in_(['jack@google.com', 'j25@yahoo.com'])
    ...  ).count() # doctest: +NORMALIZE_WHITESPACE
    SELECT count(*) AS count_1
    FROM (SELECT addresses.id AS addresses_id,
                    addresses.email_address AS addresses_email_address,
                    addresses.user_id AS addresses_user_id
    FROM addresses
    WHERE addresses.email_address IN (?, ?)) AS anon_1
    ('jack@google.com', 'j25@yahoo.com')
    {stop}2

Uh oh, they're still there ! Analyzing the flush SQL, we can see that the
``user_id`` column of each address was set to NULL, but the rows weren't
deleted. SQLAlchemy doesn't assume that deletes cascade, you have to tell it
to do so.

.. _tutorial_delete_cascade:

Configuring delete/delete-orphan Cascade
----------------------------------------

We will configure **cascade** options on the ``User.addresses`` relationship
to change the behavior. While SQLAlchemy allows you to add new attributes and
relationships to mappings at any point in time, in this case the existing
relationship needs to be removed, so we need to tear down the mappings
completely and start again - we'll close the :class:`.Session`::

    >>> session.close()

and use a new :func:`.declarative_base`::

    >>> Base = declarative_base()

Next we'll declare the ``User`` class, adding in the ``addresses`` relationship
including the cascade configuration (we'll leave the constructor out too)::

    >>> class User(Base):
    ...     __tablename__ = 'users'
    ...
    ...     id = Column(Integer, primary_key=True)
    ...     name = Column(String)
    ...     fullname = Column(String)
    ...     password = Column(String)
    ...
    ...     addresses = relationship("Address", backref='user',
    ...                     cascade="all, delete, delete-orphan")
    ...
    ...     def __repr__(self):
    ...        return "<User(name='%s', fullname='%s', password'%s')>" % (
    ...                                self.name, self.fullname, self.password)

Then we recreate ``Address``, noting that in this case we've created
the ``Address.user`` relationship via the ``User`` class already::

    >>> class Address(Base):
    ...     __tablename__ = 'addresses'
    ...     id = Column(Integer, primary_key=True)
    ...     email_address = Column(String, nullable=False)
    ...     user_id = Column(Integer, ForeignKey('users.id'))
    ...
    ...     def __repr__(self):
    ...         return "<Address(email_address='%s')>" % self.email_address

Now when we load the user ``jack`` (below using :meth:`~.Query.get`,
which loads by primary key), removing an address from the
corresponding ``addresses`` collection will result in that ``Address``
being deleted:

.. sourcecode:: python+sql

    # load Jack by primary key
    {sql}>>> jack = session.query(User).get(5)    #doctest: +NORMALIZE_WHITESPACE
    BEGIN (implicit)
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.id = ?
    (5,)
    {stop}

    # remove one Address (lazy load fires off)
    {sql}>>> del jack.addresses[1] #doctest: +NORMALIZE_WHITESPACE
    SELECT addresses.id AS addresses_id,
            addresses.email_address AS addresses_email_address,
            addresses.user_id AS addresses_user_id
    FROM addresses
    WHERE ? = addresses.user_id
    (5,)
    {stop}

    # only one address remains
    {sql}>>> session.query(Address).filter(
    ...     Address.email_address.in_(['jack@google.com', 'j25@yahoo.com'])
    ... ).count() # doctest: +NORMALIZE_WHITESPACE
    DELETE FROM addresses WHERE addresses.id = ?
    (2,)
    SELECT count(*) AS count_1
    FROM (SELECT addresses.id AS addresses_id,
                    addresses.email_address AS addresses_email_address,
                    addresses.user_id AS addresses_user_id
    FROM addresses
    WHERE addresses.email_address IN (?, ?)) AS anon_1
    ('jack@google.com', 'j25@yahoo.com')
    {stop}1

Deleting Jack will delete both Jack and the remaining ``Address`` associated
with the user:

.. sourcecode:: python+sql

    >>> session.delete(jack)

    {sql}>>> session.query(User).filter_by(name='jack').count() # doctest: +NORMALIZE_WHITESPACE
    DELETE FROM addresses WHERE addresses.id = ?
    (1,)
    DELETE FROM users WHERE users.id = ?
    (5,)
    SELECT count(*) AS count_1
    FROM (SELECT users.id AS users_id,
                    users.name AS users_name,
                    users.fullname AS users_fullname,
                    users.password AS users_password
    FROM users
    WHERE users.name = ?) AS anon_1
    ('jack',)
    {stop}0

    {sql}>>> session.query(Address).filter(
    ...    Address.email_address.in_(['jack@google.com', 'j25@yahoo.com'])
    ... ).count() # doctest: +NORMALIZE_WHITESPACE
    SELECT count(*) AS count_1
    FROM (SELECT addresses.id AS addresses_id,
                    addresses.email_address AS addresses_email_address,
                    addresses.user_id AS addresses_user_id
    FROM addresses
    WHERE addresses.email_address IN (?, ?)) AS anon_1
    ('jack@google.com', 'j25@yahoo.com')
    {stop}0

.. topic:: More on Cascades

   Further detail on configuration of cascades is at :ref:`unitofwork_cascades`.
   The cascade functionality can also integrate smoothly with
   the ``ON DELETE CASCADE`` functionality of the relational database.
   See :ref:`passive_deletes` for details.

Building a Many To Many Relationship
====================================

We're moving into the bonus round here, but lets show off a many-to-many
relationship. We'll sneak in some other features too, just to take a tour.
We'll make our application a blog application, where users can write
``BlogPost`` items, which have ``Keyword`` items associated with them.

For a plain many-to-many, we need to create an un-mapped :class:`.Table` construct
to serve as the association table.  This looks like the following::

    >>> from sqlalchemy import Table, Text
    >>> # association table
    >>> post_keywords = Table('post_keywords', Base.metadata,
    ...     Column('post_id', Integer, ForeignKey('posts.id')),
    ...     Column('keyword_id', Integer, ForeignKey('keywords.id'))
    ... )

Above, we can see declaring a :class:`.Table` directly is a little different
than declaring a mapped class.  :class:`.Table` is a constructor function, so
each individual :class:`.Column` argument is separated by a comma.  The
:class:`.Column` object is also given its name explicitly, rather than it being
taken from an assigned attribute name.

Next we define ``BlogPost`` and ``Keyword``, with a :func:`.relationship` linked
via the ``post_keywords`` table::

    >>> class BlogPost(Base):
    ...     __tablename__ = 'posts'
    ...
    ...     id = Column(Integer, primary_key=True)
    ...     user_id = Column(Integer, ForeignKey('users.id'))
    ...     headline = Column(String(255), nullable=False)
    ...     body = Column(Text)
    ...
    ...     # many to many BlogPost<->Keyword
    ...     keywords = relationship('Keyword', secondary=post_keywords, backref='posts')
    ...
    ...     def __init__(self, headline, body, author):
    ...         self.author = author
    ...         self.headline = headline
    ...         self.body = body
    ...
    ...     def __repr__(self):
    ...         return "BlogPost(%r, %r, %r)" % (self.headline, self.body, self.author)


    >>> class Keyword(Base):
    ...     __tablename__ = 'keywords'
    ...
    ...     id = Column(Integer, primary_key=True)
    ...     keyword = Column(String(50), nullable=False, unique=True)
    ...
    ...     def __init__(self, keyword):
    ...         self.keyword = keyword

.. note::

    The above class declarations illustrate explicit ``__init__()`` methods.
    Remember, when using Declarative, it's optional!

Above, the many-to-many relationship is ``BlogPost.keywords``. The defining
feature of a many-to-many relationship is the ``secondary`` keyword argument
which references a :class:`~sqlalchemy.schema.Table` object representing the
association table. This table only contains columns which reference the two
sides of the relationship; if it has *any* other columns, such as its own
primary key, or foreign keys to other tables, SQLAlchemy requires a different
usage pattern called the "association object", described at
:ref:`association_pattern`.

We would also like our ``BlogPost`` class to have an ``author`` field. We will
add this as another bidirectional relationship, except one issue we'll have is
that a single user might have lots of blog posts. When we access
``User.posts``, we'd like to be able to filter results further so as not to
load the entire collection. For this we use a setting accepted by
:func:`~sqlalchemy.orm.relationship` called ``lazy='dynamic'``, which
configures an alternate **loader strategy** on the attribute. To use it on the
"reverse" side of a :func:`~sqlalchemy.orm.relationship`, we use the
:func:`~sqlalchemy.orm.backref` function:

.. sourcecode:: python+sql

    >>> from sqlalchemy.orm import backref
    >>> # "dynamic" loading relationship to User
    >>> BlogPost.author = relationship(User, backref=backref('posts', lazy='dynamic'))

Create new tables:

.. sourcecode:: python+sql

    {sql}>>> Base.metadata.create_all(engine) # doctest: +NORMALIZE_WHITESPACE
    PRAGMA table_info("users")
    ()
    PRAGMA table_info("addresses")
    ()
    PRAGMA table_info("posts")
    ()
    PRAGMA table_info("keywords")
    ()
    PRAGMA table_info("post_keywords")
    ()
    CREATE TABLE posts (
        id INTEGER NOT NULL,
        user_id INTEGER,
        headline VARCHAR(255) NOT NULL,
        body TEXT,
        PRIMARY KEY (id),
         FOREIGN KEY(user_id) REFERENCES users (id)
    )
    ()
    COMMIT
    CREATE TABLE keywords (
        id INTEGER NOT NULL,
        keyword VARCHAR(50) NOT NULL,
        PRIMARY KEY (id),
         UNIQUE (keyword)
    )
    ()
    COMMIT
    CREATE TABLE post_keywords (
        post_id INTEGER,
        keyword_id INTEGER,
         FOREIGN KEY(post_id) REFERENCES posts (id),
         FOREIGN KEY(keyword_id) REFERENCES keywords (id)
    )
    ()
    COMMIT

Usage is not too different from what we've been doing.  Let's give Wendy some blog posts:

.. sourcecode:: python+sql

    {sql}>>> wendy = session.query(User).\
    ...                 filter_by(name='wendy').\
    ...                 one() #doctest: +NORMALIZE_WHITESPACE
    SELECT users.id AS users_id,
            users.name AS users_name,
            users.fullname AS users_fullname,
            users.password AS users_password
    FROM users
    WHERE users.name = ?
    ('wendy',)
    {stop}
    >>> post = BlogPost("Wendy's Blog Post", "This is a test", wendy)
    >>> session.add(post)

We're storing keywords uniquely in the database, but we know that we don't
have any yet, so we can just create them:

.. sourcecode:: python+sql

    >>> post.keywords.append(Keyword('wendy'))
    >>> post.keywords.append(Keyword('firstpost'))

We can now look up all blog posts with the keyword 'firstpost'. We'll use the
``any`` operator to locate "blog posts where any of its keywords has the
keyword string 'firstpost'":

.. sourcecode:: python+sql

    {sql}>>> session.query(BlogPost).\
    ...             filter(BlogPost.keywords.any(keyword='firstpost')).\
    ...             all() #doctest: +NORMALIZE_WHITESPACE
    INSERT INTO keywords (keyword) VALUES (?)
    ('wendy',)
    INSERT INTO keywords (keyword) VALUES (?)
    ('firstpost',)
    INSERT INTO posts (user_id, headline, body) VALUES (?, ?, ?)
    (2, "Wendy's Blog Post", 'This is a test')
    INSERT INTO post_keywords (post_id, keyword_id) VALUES (?, ?)
    ((1, 1), (1, 2))
    SELECT posts.id AS posts_id,
            posts.user_id AS posts_user_id,
            posts.headline AS posts_headline,
            posts.body AS posts_body
    FROM posts
    WHERE EXISTS (SELECT 1
        FROM post_keywords, keywords
        WHERE posts.id = post_keywords.post_id
            AND keywords.id = post_keywords.keyword_id
            AND keywords.keyword = ?)
    ('firstpost',)
    {stop}[BlogPost("Wendy's Blog Post", 'This is a test', <User(name='wendy', fullname='Wendy Williams', password='foobar')>)]

If we want to look up posts owned by the user ``wendy``, we can tell
the query to narrow down to that ``User`` object as a parent:

.. sourcecode:: python+sql

    {sql}>>> session.query(BlogPost).\
    ...             filter(BlogPost.author==wendy).\
    ...             filter(BlogPost.keywords.any(keyword='firstpost')).\
    ...             all() #doctest: +NORMALIZE_WHITESPACE
    SELECT posts.id AS posts_id,
            posts.user_id AS posts_user_id,
            posts.headline AS posts_headline,
            posts.body AS posts_body
    FROM posts
    WHERE ? = posts.user_id AND (EXISTS (SELECT 1
        FROM post_keywords, keywords
        WHERE posts.id = post_keywords.post_id
            AND keywords.id = post_keywords.keyword_id
            AND keywords.keyword = ?))
    (2, 'firstpost')
    {stop}[BlogPost("Wendy's Blog Post", 'This is a test', <User(name='wendy', fullname='Wendy Williams', password='foobar')>)]

Or we can use Wendy's own ``posts`` relationship, which is a "dynamic"
relationship, to query straight from there:

.. sourcecode:: python+sql

    {sql}>>> wendy.posts.\
    ...         filter(BlogPost.keywords.any(keyword='firstpost')).\
    ...         all() #doctest: +NORMALIZE_WHITESPACE
    SELECT posts.id AS posts_id,
            posts.user_id AS posts_user_id,
            posts.headline AS posts_headline,
            posts.body AS posts_body
    FROM posts
    WHERE ? = posts.user_id AND (EXISTS (SELECT 1
        FROM post_keywords, keywords
        WHERE posts.id = post_keywords.post_id
            AND keywords.id = post_keywords.keyword_id
            AND keywords.keyword = ?))
    (2, 'firstpost')
    {stop}[BlogPost("Wendy's Blog Post", 'This is a test', <User(name='wendy', fullname='Wendy Williams', password='foobar')>)]

Further Reference
==================

Query Reference: :ref:`query_api_toplevel`

Mapper Reference: :ref:`mapper_config_toplevel`

Relationship Reference: :ref:`relationship_config_toplevel`

Session Reference: :doc:`/orm/session`
