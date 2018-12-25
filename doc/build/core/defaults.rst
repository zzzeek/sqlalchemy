.. module:: sqlalchemy.schema

.. _metadata_defaults_toplevel:

.. _metadata_defaults:

Column Insert/Update Defaults
=============================

SQLAlchemy provides a very rich featureset regarding column level events which
take place during INSERT and UPDATE statements. Options include:

* Scalar values used as defaults during INSERT and UPDATE operations
* Python functions which execute upon INSERT and UPDATE operations
* SQL expressions which are embedded in INSERT statements (or in some cases execute beforehand)
* SQL expressions which are embedded in UPDATE statements
* Server side default values used during INSERT
* Markers for server-side triggers used during UPDATE

The general rule for all insert/update defaults is that they only take effect
if no value for a particular column is passed as an ``execute()`` parameter;
otherwise, the given value is used.

Scalar Defaults
---------------

The simplest kind of default is a scalar value used as the default value of a column::

    Table("mytable", meta,
        Column("somecolumn", Integer, default=12)
    )

Above, the value "12" will be bound as the column value during an INSERT if no
other value is supplied.

A scalar value may also be associated with an UPDATE statement, though this is
not very common (as UPDATE statements are usually looking for dynamic
defaults)::

    Table("mytable", meta,
        Column("somecolumn", Integer, onupdate=25)
    )


Python-Executed Functions
-------------------------

The :paramref:`.Column.default` and :paramref:`.Column.onupdate` keyword arguments also accept Python
functions. These functions are invoked at the time of insert or update if no
other value for that column is supplied, and the value returned is used for
the column's value. Below illustrates a crude "sequence" that assigns an
incrementing counter to a primary key column::

    # a function which counts upwards
    i = 0
    def mydefault():
        global i
        i += 1
        return i

    t = Table("mytable", meta,
        Column('id', Integer, primary_key=True, default=mydefault),
    )

It should be noted that for real "incrementing sequence" behavior, the
built-in capabilities of the database should normally be used, which may
include sequence objects or other autoincrementing capabilities. For primary
key columns, SQLAlchemy will in most cases use these capabilities
automatically. See the API documentation for
:class:`~sqlalchemy.schema.Column` including the :paramref:`.Column.autoincrement` flag, as
well as the section on :class:`~sqlalchemy.schema.Sequence` later in this
chapter for background on standard primary key generation techniques.

To illustrate onupdate, we assign the Python ``datetime`` function ``now`` to
the :paramref:`.Column.onupdate` attribute::

    import datetime

    t = Table("mytable", meta,
        Column('id', Integer, primary_key=True),

        # define 'last_updated' to be populated with datetime.now()
        Column('last_updated', DateTime, onupdate=datetime.datetime.now),
    )

When an update statement executes and no value is passed for ``last_updated``,
the ``datetime.datetime.now()`` Python function is executed and its return
value used as the value for ``last_updated``. Notice that we provide ``now``
as the function itself without calling it (i.e. there are no parenthesis
following) - SQLAlchemy will execute the function at the time the statement
executes.

.. _context_default_functions:

Context-Sensitive Default Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Python functions used by :paramref:`.Column.default` and
:paramref:`.Column.onupdate` may also make use of the current statement's
context in order to determine a value. The `context` of a statement is an
internal SQLAlchemy object which contains all information about the statement
being executed, including its source expression, the parameters associated with
it and the cursor. The typical use case for this context with regards to
default generation is to have access to the other values being inserted or
updated on the row. To access the context, provide a function that accepts a
single ``context`` argument::

    def mydefault(context):
        return context.get_current_parameters()['counter'] + 12

    t = Table('mytable', meta,
        Column('counter', Integer),
        Column('counter_plus_twelve', Integer, default=mydefault, onupdate=mydefault)
    )

The above default generation function is applied so that it will execute for
all INSERT and UPDATE statements where a value for ``counter_plus_twelve`` was
otherwise not provided, and the value will be that of whatever value is present
in the execution for the ``counter`` column, plus the number 12.

For a single statement that is being executed using "executemany" style, e.g.
with multiple parameter sets passed to :meth:`.Connection.execute`, the user-
defined function is called once for each set of parameters. For the use case of
a multi-valued :class:`.Insert` construct (e.g. with more than one VALUES
clause set up via the :meth:`.Insert.values` method), the user-defined function
is also called once for each set of parameters.

When the function is invoked, the special method
:meth:`.DefaultExecutionContext.get_current_parameters` is available from
the context object (an subclass of :class:`.DefaultExecutionContext`).  This
method returns a dictionary of column-key to values that represents the
full set of values for the INSERT or UPDATE statement.   In the case of a
multi-valued INSERT construct, the subset of parameters that corresponds to
the individual VALUES clause is isolated from the full parameter dictionary
and returned alone.

.. versionadded:: 1.2

    Added :meth:`.DefaultExecutionContext.get_current_parameters` method,
    which improves upon the still-present
    :attr:`.DefaultExecutionContext.current_parameters` attribute
    by offering the service of organizing multiple VALUES clauses
    into individual parameter dictionaries.

Client-Invoked SQL Expressions
------------------------------

The :paramref:`.Column.default` and :paramref:`.Column.onupdate` keywords may
also be passed SQL expressions, which are in most cases rendered inline within the
INSERT or UPDATE statement::

    t = Table("mytable", meta,
        Column('id', Integer, primary_key=True),

        # define 'create_date' to default to now()
        Column('create_date', DateTime, default=func.now()),

        # define 'key' to pull its default from the 'keyvalues' table
        Column('key', String(20), default=select([keyvalues.c.key]).where(keyvalues.c.type='type1')),

        # define 'last_modified' to use the current_timestamp SQL function on update
        Column('last_modified', DateTime, onupdate=func.utc_timestamp())
        )

Above, the ``create_date`` column will be populated with the result of the
``now()`` SQL function (which, depending on backend, compiles into ``NOW()``
or ``CURRENT_TIMESTAMP`` in most cases) during an INSERT statement, and the
``key`` column with the result of a SELECT subquery from another table. The
``last_modified`` column will be populated with the value of
the SQL ``UTC_TIMESTAMP()`` MySQL function when an UPDATE statement is
emitted for this table.

.. note::

    When using SQL functions with the :attr:`.func` construct, we "call" the
    named function, e.g. with parenthesis as in ``func.now()``.   This differs
    from when we specify a Python callable as a default such as
    ``datetime.datetime``, where we pass the function itself, but we don't
    invoke it ourselves.   In the case of a SQL function, invoking
    ``func.now()`` returns the SQL expression object that will render the
    "NOW" function into the SQL being emitted.

Default and update SQL expressions specified by :paramref:`.Column.default` and
:paramref:`.Column.onupdate` are invoked explicitly by SQLAlchemy when an
INSERT or UPDATE statement occurs, typically rendered inline within the DML
statement except in certain cases listed below.   This is different than a
"server side" default, which is part of the table's DDL definition, e.g. as
part of the "CREATE TABLE" statement, which are likely more common.   For
server side defaults, see the next section :ref:`server_defaults`.

When a SQL expression indicated by :paramref:`.Column.default` is used with
primary key columns, there are some cases where SQLAlchemy must "pre-execute"
the default generation SQL function, meaning it is invoked in a separate SELECT
statement, and the resulting value is passed as a parameter to the INSERT.
This only occurs for primary key columns for an INSERT statement that is being
asked to return this primary key value, where RETURNING or ``cursor.lastrowid``
may not be used.   An :class:`.Insert` construct that specifies the
:paramref:`~.expression.insert.inline` flag will always render default expressions
inline.

When the statement is executed with a single set of parameters (that is, it is
not an "executemany" style execution), the returned
:class:`~sqlalchemy.engine.ResultProxy` will contain a collection accessible
via :meth:`.ResultProxy.postfetch_cols` which contains a list of all
:class:`~sqlalchemy.schema.Column` objects which had an inline-executed
default. Similarly, all parameters which were bound to the statement, including
all Python and SQL expressions which were pre-executed, are present in the
:meth:`.ResultProxy.last_inserted_params` or
:meth:`.ResultProxy.last_updated_params` collections on
:class:`~sqlalchemy.engine.ResultProxy`. The
:attr:`.ResultProxy.inserted_primary_key` collection contains a list of primary
key values for the row inserted (a list so that single-column and composite-
column primary keys are represented in the same format).

.. _server_defaults:

Server-invoked DDL-Explicit Default Expressions
-----------------------------------------------

A variant on the SQL expression default is the :paramref:`.Column.server_default`, which gets
placed in the CREATE TABLE statement during a :meth:`.Table.create` operation:

.. sourcecode:: python+sql

    t = Table('test', meta,
        Column('abc', String(20), server_default='abc'),
        Column('created_at', DateTime, server_default=func.sysdate()),
        Column('index_value', Integer, server_default=text("0"))
    )

A create call for the above table will produce::

    CREATE TABLE test (
        abc varchar(20) default 'abc',
        created_at datetime default sysdate,
        index_value integer default 0
    )

The above example illustrates the two typical use cases for :paramref:`.Column.server_default`,
that of the SQL function (SYSDATE in the above example) as well as a server-side constant
value (the integer "0" in the above example).  It is advisable to use the
:func:`.text` construct for any literal SQL values as opposed to passing the
raw value, as SQLAlchemy does not typically perform any quoting or escaping on
these values.

Like client-generated expressions, :paramref:`.Column.server_default` can accommodate
SQL expressions in general, however it is expected that these will usually be simple
functions and expressions, and not the more complex cases like an embedded SELECT.


.. _triggered_columns:

Marking Implicitly Generated Values, timestamps, and Triggered Columns
----------------------------------------------------------------------

Columns which generate a new value on INSERT or UPDATE based on other
server-side database mechanisms, such as database-specific auto-generating
behaviors such as seen with TIMESTAMP columns on some platforms, as well as
custom triggers that invoke upon INSERT or UPDATE to generate a new value,
may be called out using :class:`.FetchedValue` as a marker::

    t = Table('test', meta,
        Column('id', Integer, primary_key=True),
        Column('abc', TIMESTAMP, server_default=FetchedValue()),
        Column('def', String(20), server_onupdate=FetchedValue())
    )

The :class:`.FetchedValue` indicator does not affect the rendered DDL for the
CREATE TABLE.  Instead, it marks the column as one that will have a new value
populated by the database during the process of an INSERT or UPDATE statement,
and for supporting  databases may be used to indicate that the column should be
part of a RETURNING or OUTPUT clause for the statement.    Tools such as the
SQLAlchemy ORM then make use of this marker in order to know how to get at the
value of the column after such an operation.   In particular, the
:meth:`.ValuesBase.return_defaults` method can be used with an :class:`.Insert`
or :class:`.Update` construct to indicate that these values should be
returned.

For details on using :class:`.FetchedValue` with the ORM, see
:ref:`orm_server_defaults`.

.. seealso::

    :ref:`orm_server_defaults`


Defining Sequences
------------------

SQLAlchemy represents database sequences using the
:class:`~sqlalchemy.schema.Sequence` object, which is considered to be a
special case of "column default". It only has an effect on databases which
have explicit support for sequences, which currently includes PostgreSQL,
Oracle, and Firebird. The :class:`~sqlalchemy.schema.Sequence` object is
otherwise ignored.

The :class:`~sqlalchemy.schema.Sequence` may be placed on any column as a
"default" generator to be used during INSERT operations, and can also be
configured to fire off during UPDATE operations if desired. It is most
commonly used in conjunction with a single integer primary key column::

    table = Table("cartitems", meta,
        Column(
            "cart_id",
            Integer,
            Sequence('cart_id_seq', metadata=meta), primary_key=True),
        Column("description", String(40)),
        Column("createdate", DateTime())
    )

Where above, the table "cartitems" is associated with a sequence named
"cart_id_seq". When INSERT statements take place for "cartitems", and no value
is passed for the "cart_id" column, the "cart_id_seq" sequence will be used to
generate a value.   Typically, the sequence function is embedded in the
INSERT statement, which is combined with RETURNING so that the newly generated
value can be returned to the Python code::

    INSERT INTO cartitems (cart_id, description, createdate)
    VALUES (next_val(cart_id_seq), 'some description', '2015-10-15 12:00:15')
    RETURNING cart_id

When the :class:`~sqlalchemy.schema.Sequence` is associated with a
:class:`.Column` as its **Python-side** default generator, the
:class:`.Sequence` will also be subject to "CREATE SEQUENCE" and "DROP
SEQUENCE" DDL when similar DDL is emitted for the owning :class:`.Table`.
This is a limited scope convenience feature that does not accommodate for
inheritance of other aspects of the :class:`.MetaData`, such as the default
schema.  Therefore, it is best practice that for a :class:`.Sequence` which
is local to a certain :class:`.Column` / :class:`.Table`, that it be
explicitly associated with the :class:`.MetaData` using the
:paramref:`.Sequence.metadata` parameter.  See the section
:ref:`sequence_metadata` for more background on this.

Associating a Sequence on a SERIAL column
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PostgreSQL's SERIAL datatype is an auto-incrementing type that implies
the implicit creation of a PostgreSQL sequence when CREATE TABLE is emitted.
If a :class:`.Column` specifies an explicit :class:`.Sequence` object
which also specifies a true value for the :paramref:`.Sequence.optional`
boolean flag, the :class:`.Sequence` will not take effect under PostgreSQL,
and the SERIAL datatype will proceed normally.   Instead, the :class:`.Sequence`
will only take effect when used against other sequence-supporting
databases, currently Oracle and Firebird.

Executing a Sequence Standalone
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A SEQUENCE is a first class schema object in SQL and can be used to generate
values independently in the database.   If you have a :class:`.Sequence`
object, it can be invoked with its "next value" instruction by
passing it directly to a SQL execution method::

    with my_engine.connect() as conn:
        seq = Sequence('some_sequence')
        nextid = conn.execute(seq)

In order to embed the "next value" function of a :class:`.Sequence`
inside of a SQL statement like a SELECT or INSERT, use the :meth:`.Sequence.next_value`
method, which will render at statement compilation time a SQL function that is
appropriate for the target backend::

    >>> my_seq = Sequence('some_sequence')
    >>> stmt = select([my_seq.next_value()])
    >>> print stmt.compile(dialect=postgresql.dialect())
    SELECT nextval('some_sequence') AS next_value_1

.. _sequence_metadata:

Associating a Sequence with the MetaData
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For many years, the SQLAlchemy documentation referred to the
example of associating a :class:`.Sequence` with a table as follows::

    table = Table("cartitems", meta,
        Column("cart_id", Integer, Sequence('cart_id_seq'),
               primary_key=True),
        Column("description", String(40)),
        Column("createdate", DateTime())
    )

While the above is a prominent idiomatic pattern, it is recommended that
the :class:`.Sequence` in most cases be explicitly associated with the
:class:`.MetaData`, using the :paramref:`.Sequence.metadata` parameter::

    table = Table("cartitems", meta,
        Column(
            "cart_id",
            Integer,
            Sequence('cart_id_seq', metadata=meta), primary_key=True),
        Column("description", String(40)),
        Column("createdate", DateTime())
    )

The :class:`.Sequence` object is a first class
schema construct that can exist independently of any table in a database, and
can also be shared among tables.   Therefore SQLAlchemy does not implicitly
modify the :class:`.Sequence` when it is associated with a :class:`.Column`
object as either the Python-side or server-side default  generator.  While the
CREATE SEQUENCE / DROP SEQUENCE DDL is emitted for a  :class:`.Sequence`
defined as a Python side generator at the same time the table itself is subject
to CREATE or DROP, this is a convenience feature that does not imply that the
:class:`.Sequence` is fully associated with the :class:`.MetaData` object.

Explicitly associating the :class:`.Sequence` with :class:`.MetaData`
allows for the following behaviors:

* The :class:`.Sequence` will inherit the :paramref:`.MetaData.schema`
  parameter specified to the target :class:`.MetaData`, which
  affects the production of CREATE / DROP DDL, if any.

* The :meth:`.Sequence.create` and :meth:`.Sequence.drop` methods
  automatically use the engine bound to the :class:`.MetaData`
  object, if any.

* The :meth:`.MetaData.create_all` and :meth:`.MetaData.drop_all`
  methods will emit CREATE / DROP for this :class:`.Sequence`,
  even if the :class:`.Sequence` is not associated with any
  :class:`.Table` / :class:`.Column` that's a member of this
  :class:`.MetaData`.

Since the vast majority of cases that deal with :class:`.Sequence` expect
that :class:`.Sequence` to be fully "owned" by the assocated :class:`.Table`
and that options like default schema are propagated, setting the
:paramref:`.Sequence.metadata` parameter should be considered a best practice.

Associating a Sequence as the Server Side Default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: The following technique is known to work only with the PostgreSQL
   database.  It does not work with Oracle.

The preceding sections illustrate how to associate a :class:`.Sequence` with a
:class:`.Column` as the **Python side default generator**::

    Column(
        "cart_id", Integer, Sequence('cart_id_seq', metadata=meta),
        primary_key=True)

In the above case, the :class:`.Sequence` will automatically be subject
to CREATE SEQUENCE / DROP SEQUENCE DDL when the related :class:`.Table`
is subject to CREATE / DROP.  However, the sequence will **not** be present
as the server-side default for the column when CREATE TABLE is emitted.

If we want the sequence to be used as a server-side default,
meaning it takes place even if we emit INSERT commands to the table from
the SQL command line, we can use the :paramref:`.Column.server_default`
parameter in conjunction with the value-generation function of the
sequence, available from the :meth:`.Sequence.next_value` method.  Below
we illustrate the same :class:`.Sequence` being associated with the
:class:`.Column` both as the Python-side default generator as well as
the server-side default generator::

    cart_id_seq = Sequence('cart_id_seq', metadata=meta)
    table = Table("cartitems", meta,
        Column(
            "cart_id", Integer, cart_id_seq,
            server_default=cart_id_seq.next_value(), primary_key=True),
        Column("description", String(40)),
        Column("createdate", DateTime())
    )

or with the ORM::

    class CartItem(Base):
        __tablename__ = 'cartitems'

        cart_id_seq = Sequence('cart_id_seq', metadata=Base.metadata)
        cart_id = Column(
            Integer, cart_id_seq,
            server_default=cart_id_seq.next_value(), primary_key=True)
        description = Column(String(40))
        createdate = Column(DateTime)

When the "CREATE TABLE" statement is emitted, on PostgreSQL it would be
emitted as::

    CREATE TABLE cartitems (
        cart_id INTEGER DEFAULT nextval('cart_id_seq') NOT NULL,
        description VARCHAR(40),
        createdate TIMESTAMP WITHOUT TIME ZONE,
        PRIMARY KEY (cart_id)
    )

Placement of the :class:`.Sequence` in both the Python-side and server-side
default generation contexts ensures that the "primary key fetch" logic
works in all cases.  Typically, sequence-enabled databases also support
RETURNING for INSERT statements, which is used automatically by SQLAlchemy
when emitting this statement.  However if RETURNING is not used for a particular
insert, then SQLAlchemy would prefer to "pre-execute" the sequence outside
of the INSERT statement itself, which only works if the sequence is
included as the Python-side default generator function.

The example also associates the :class:`.Sequence` with the enclosing
:class:`.MetaData` directly, which again ensures that the :class:`.Sequence`
is fully associated with the parameters of the :class:`.MetaData` collection
including the default schema, if any.

.. seealso::

    :ref:`postgresql_sequences` - in the PostgreSQL dialect documentation

    :ref:`oracle_returning` - in the Oracle dialect documentation

Default Objects API
-------------------

.. autoclass:: ColumnDefault


.. autoclass:: DefaultClause


.. autoclass:: DefaultGenerator


.. autoclass:: FetchedValue


.. autoclass:: PassiveDefault


.. autoclass:: Sequence
    :members:
