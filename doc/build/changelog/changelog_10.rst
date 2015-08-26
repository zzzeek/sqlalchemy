

==============
1.0 Changelog
==============

.. changelog_imports::

    .. include:: changelog_09.rst
        :start-line: 5

    .. include:: changelog_08.rst
        :start-line: 5

    .. include:: changelog_07.rst
        :start-line: 5

.. changelog::
    :version: 1.0.2

    .. change::
        :tags: bug, ext, declarative
        :tickets: 3383

        Fixed regression regarding the declarative ``__declare_first__``
        and ``__declare_last__`` accessors where these would no longer be
        called on the superclass of the declarative base.

.. changelog::
    :version: 1.0.1
    :released: April 23, 2015

    .. change::
        :tags: bug, firebird
        :tickets: 3380
        :pullreq: github:168

        Fixed a regression due to :ticket:`3034` where limit/offset
        clauses were not properly interpreted by the Firebird dialect.
        Pull request courtesy effem-git.

    .. change::
        :tags: bug, firebird
        :tickets: 3381

        Fixed support for "literal_binds" mode when using limit/offset
        with Firebird, so that the values are again rendered inline when
        this is selected.  Related to :ticket:`3034`.

    .. change::
        :tags: bug, sqlite
        :tickets: 3378

        Fixed a regression due to :ticket:`3282`, where due to the fact that
        we attempt to assume the availability of ALTER when creating/dropping
        schemas, in the case of SQLite we simply said to not worry about
        foreign keys at all, since ALTER is not available, when creating
        and dropping tables.  This meant that the sorting of tables was
        basically skipped in the case of SQLite, and for the vast majority
        of SQLite use cases, this is not an issue.

        However, users who were doing DROPs on SQLite
        with tables that contained data and with referential integrity
        turned on would then experience errors, as the
        dependency sorting *does* matter in the case of DROP with
        enforced constraints, when those tables have data (SQLite will still
        happily let you create foreign keys to nonexistent tables and drop
        tables referring to existing ones with constraints enabled, as long as
        there's no data being referenced).

        In order to maintain the new feature of :ticket:`3282` while still
        allowing a SQLite DROP operation to maintain ordering, we now
        do the sort with full FKs taken under consideration, and if we encounter
        an unresolvable cycle, only *then* do we forego attempting to sort
        the tables; we instead emit a warning and go with the unsorted list.
        If an environment needs both ordered DROPs *and* has foreign key
        cycles, then the warning notes they will need to restore the
        ``use_alter`` flag to their :class:`.ForeignKey` and
        :class:`.ForeignKeyConstraint` objects so that just those objects will
        be omitted from the dependency sort.

        .. seealso::

            :ref:`feature_3282` - contains an updated note about SQLite.

    .. change::
        :tags: bug, sql
        :tickets: 3372

        Fixed issue where a straight SELECT EXISTS query would fail to
        assign the proper result type of Boolean to the result mapping, and
        instead would leak column types from within the query into the
        result map.  This issue exists in 0.9 and earlier as well, however
        has less of an impact in those versions.  In 1.0, due to :ticket:`918`
        this becomes a regression in that we now rely upon the result mapping
        to be very accurate, else we can assign result-type processors to
        the wrong column.   In all versions, this issue also has the effect
        that a simple EXISTS will not apply the Boolean type handler, leading
        to simple 1/0 values for backends without native boolean instead of
        True/False.   The fix includes that an EXISTS columns argument
        will be anon-labeled like other column expressions; a similar fix is
        implemented for pure-boolean expressions like ``not_(True())``.

    .. change::
        :tags: bug, orm
        :tickets: 3374

        Fixed issue where a query of the form
        ``query(B).filter(B.a != A(id=7))`` would render the ``NEVER_SET``
        symbol, when
        given a transient object. For a persistent object, it would
        always use the persisted database value and not the currently
        set value.  Assuming autoflush is turned on, this usually would
        not be apparent for persistent values, as any pending changes
        would be flushed first in any case.  However, this is inconsistent
        vs. the logic used for the  non-negated comparison,
        ``query(B).filter(B.a == A(id=7))``, which does use the
        current value and additionally allows comparisons to transient
        objects.  The comparison now uses the current value and not
        the database-persisted value.

        Unlike the other ``NEVER_SET`` issues that are repaired as regressions
        caused by :ticket:`3061` in this release, this particular issue is
        present at least as far back as 0.8 and possibly earlier, however it
        was discovered as a result of repairing the related ``NEVER_SET``
        issues.

        .. seealso::

            :ref:`bug_3374`

    .. change::
        :tags: bug, orm
        :tickets: 3371

        Fixed a regression cause by :ticket:`3061` where the NEVER_SET
        symbol could leak into relationship-oriented queries, including
        ``filter()`` and ``with_parent()`` queries.  The ``None`` symbol
        is returned in all cases, however many of these queries have never
        been correctly supported in any case, and produce comparisons
        to NULL without using the IS operator.  For this reason, a warning
        is also added to that subset of relationship queries that don't
        currently provide for ``IS NULL``.

        .. seealso::

            :ref:`bug_3371`


    .. change::
        :tags: bug, orm
        :tickets: 3368

        Fixed a regression caused by :ticket:`3061` where the
        NEVER_SET symbol could leak into a lazyload query, subsequent
        to the flush of a pending object.  This would occur typically
        for a many-to-one relationship that does not use a simple
        "get" strategy.   The good news is that the fix improves efficiency
        vs. 0.9, because we can now skip the SELECT statement entirely
        when we detect NEVER_SET symbols present in the parameters; prior to
        :ticket:`3061`, we couldn't discern if the None here were set or not.


.. changelog::
    :version: 1.0.0
    :released: April 16, 2015

    .. change::
        :tags: bug, orm
        :tickets: 3367

        Identified an inconsistency when handling :meth:`.Query.join` to the
        same target more than once; it implicitly dedupes only in the case of
        a relationship join, and due to :ticket:`3233`, in 1.0 a join
        to the same table twice behaves differently than 0.9 in that it no
        longer erroneously aliases.   To help document this change,
        the verbiage regarding :ticket:`3233` in the migration notes has
        been generalized, and a warning has been added when :meth:`.Query.join`
        is called against the same target relationship more than once.

    .. change::
        :tags: bug, orm
        :tickets: 3364

        Made a small improvement to the heuristics of relationship when
        determining remote side with semi-self-referential (e.g. two joined
        inh subclasses referring to each other), non-simple join conditions
        such that the parententity is taken into account and can reduce the
        need for using the ``remote()`` annotation; this can restore some
        cases that might have worked without the annotation prior to 0.9.4
        via :ticket:`2948`.

    .. change::
        :tags: bug, mssql
        :tickets: 3360

        Fixed a regression where the "last inserted id" mechanics would
        fail to store the correct value for MSSQL on an INSERT where the
        primary key value was present in the insert params before execution,
        as well as in the case where an INSERT from SELECT would state the
        target columns as column objects, instead of string keys.


    .. change::
        :tags: bug, mssql
        :pullreq: github:166

        Using the ``Binary`` constructor now present in pymssql rather than
        patching one in.  Pull request courtesy Ramiro Morales.

    .. change::
        :tags: bug, tests
        :tickets: 3356

        Fixed the pathing used when tests run; for sqla_nose.py and py.test,
        the "./lib" prefix is again inserted at the head of sys.path but
        only if sys.flags.no_user_site isn't set; this makes it act just
        like the way Python puts "." in the current path by default.
        For tox, we are setting the PYTHONNOUSERSITE flag now.

    .. change::
        :tags: feature, sql
        :tickets: 3084
        :pullreq: bitbucket:47

        The topological sorting used to sort :class:`.Table` objects
        and available via the :attr:`.MetaData.sorted_tables` collection
        will now produce a **deterministic** ordering; that is, the same
        ordering each time given a set of tables with particular names
        and dependencies.  This is to help with comparison of DDL scripts
        and other use cases.  The tables are sent to the topological sort
        sorted by name, and the topological sort itself will process
        the incoming data in an ordered fashion.  Pull request
        courtesy Sebastian Bank.

        .. seealso::

            :ref:`feature_3084`

    .. change::
        :tags: feature, orm
        :pullreq: github:164

        Added new argument :paramref:`.Query.update.update_args` which allows
        kw arguments such as ``mysql_limit`` to be passed to the underlying
        :class:`.Update` construct.  Pull request courtesy Amir Sadoughi.

.. changelog::
    :version: 1.0.0b5
    :released: April 3, 2015

    .. change::
        :tags: bug, orm
        :tickets: 3349

        :class:`.Query` doesn't support joins, subselects, or special
        FROM clauses when using the :meth:`.Query.update` or
        :meth:`.Query.delete` methods; instead of silently ignoring these
        fields if methods like :meth:`.Query.join` or
        :meth:`.Query.select_from` has been called, an error is raised.
        In 0.9.10 this only emits a warning.

    .. change::
        :tags: bug, orm

        Added a list() call around a weak dictionary used within the
        commit phase of the session, which without it could cause
        a "dictionary changed size during iter" error if garbage collection
        interacted within the process.   Change was introduced by
        #3139.

    .. change::
        :tags: bug, postgresql
        :tickets: 3343

        Fixed bug where updated PG index reflection as a result of
        :ticket:`3184` would cause index operations to fail on Postgresql
        versions 8.4 and earlier.  The enhancements are now
        disabled when using an older version of Postgresql.

    .. change::
        :tags: bug, sql
        :tickets: 3346

        The warning emitted by the unicode type for a non-unicode type
        has been liberalized to warn for values that aren't even string
        values, such as integers; previously, the updated warning system
        of 1.0 made use of string formatting operations which
        would raise an internal TypeError.   While these cases should ideally
        raise totally, some backends like SQLite and MySQL do accept them
        and are potentially in use by legacy code, not to mention that they
        will always pass through if unicode conversion is turned off
        for the target backend.

    .. change::
        :tags: bug, orm
        :tickets: 3347

        Fixed a bug related to "nested" inner join eager loading, which
        exists in 0.9 as well but is more of a regression in 1.0 due to
        :ticket:`3008` which turns on "nested" by default, such that
        a joined eager load that travels across sibling paths from a common
        ancestor using innerjoin=True will correctly splice each "innerjoin"
        sibling into the appropriate part of the join, when a series of
        inner/outer joins are mixed together.

.. changelog::
    :version: 1.0.0b4
    :released: March 29, 2015

    .. change::
        :tags: bug, mssql, oracle, firebird, sybase
        :tickets: 3338

        Turned off the "simple order by" flag on the MSSQL, Oracle dialects;
        this is the flag that per :ticket:`2992` causes an order by or group by
        an expression that's also in the columns clause to be copied by
        label, even if referenced as the expression object.   The behavior
        for MSSQL is now the old behavior that copies the whole expression
        in by default, as MSSQL can be picky on these particularly in
        GROUP BY expressions.  The flag is also turned off defensively
        for the Firebird and Sybase dialects.

    .. change::
        :tags: feature, schema
        :tickets: 3341

        The "auto-attach" feature of constraints such as :class:`.UniqueConstraint`
        and :class:`.CheckConstraint` has been further enhanced such that
        when the constraint is associated with non-table-bound :class:`.Column`
        objects, the constraint will set up event listeners with the
        columns themselves such that the constraint auto attaches at the
        same time the columns are associated with the table.  This in particular
        helps in some edge cases in declarative but is also of general use.

    .. change::
        :tags: bug, sql
        :tickets: 3340

        Fixed bug in new "label resolution" feature of :ticket:`2992` where
        a label that was anonymous, then labeled again with a name, would
        fail to be locatable via a textual label.  This situation occurs
        naturally when a mapped :func:`.column_property` is given an
        explicit label in a query.

    .. change::
        :tags: bug, sql
        :tickets: 3335

        Fixed bug in new "label resolution" feature of :ticket:`2992` where
        the string label placed in the order_by() or group_by() of a statement
        would place higher priority on the name as found
        inside the FROM clause instead of a more locally available name
        inside the columns clause.

.. changelog::
    :version: 1.0.0b3
    :released: March 20, 2015

    .. change::
        :tags: bug, mysql
        :tickets: 2771

        Repaired the commit for issue #2771 which was inadvertently commented
        out.


.. changelog::
    :version: 1.0.0b2
    :released: March 20, 2015

    .. change::
        :tags: bug, mysql
        :tickets: 2771
        :pullreq: bitbucket:49

        Fixes to fully support using the ``'utf8mb4'`` MySQL-specific charset
        with MySQL dialects, in particular MySQL-Python and PyMySQL.   In
        addition, MySQL databases that report more unusual charsets such as
        'koi8u' or 'eucjpms' will also work correctly.  Pull request
        courtesy Thomas Grainger.

    .. change::
        :tags: change, ext, declarative
        :tickets: 3331

        Loosened some restrictions that were added to ``@declared_attr``
        objects, such that they were prevented from being called outside
        of the declarative process; this is related to the enhancements
        of #3150 which allow ``@declared_attr`` to return a value that is
        cached based on the current class as it's being configured.
        The exception raise has been removed, and the behavior changed
        so that outside of the declarative process, the function decorated by
        ``@declared_attr`` is called every time just like a regular
        ``@property``, without using any caching, as none is available
        at this stage.

    .. change::
        :tags: bug, engine
        :tickets: 3330, 3329

        The "auto close" for :class:`.ResultProxy` is now a "soft" close.
        That is, after exhausing all rows using the fetch methods, the
        DBAPI cursor is released as before and the object may be safely
        discarded, but the fetch methods may continue to be called for which
        they will return an end-of-result object (None for fetchone, empty list
        for fetchmany and fetchall).   Only if :meth:`.ResultProxy.close`
        is called explicitly will these methods raise the "result is closed"
        error.

        .. seealso::

            :ref:`change_3330`

    .. change::
        :tags: bug, orm
        :tickets: 3327
        :pullreq: github:160

        Fixed 1.0 regression from pullreq github:137 where Py2K unicode
        literals (e.g. ``u""``) would not be accepted by the
        :paramref:`.relationship.cascade` option.
        Pull request courtesy Julien Castets.


.. changelog::
    :version: 1.0.0b1
    :released: March 13, 2015

    Version 1.0.0b1 is the first release of the 1.0 series.   Many changes
    described here are also present in the 0.9 and sometimes the 0.8
    series as well.  For changes that are specific to 1.0 with an emphasis
    on compatibility concerns, see :doc:`/changelog/migration_10`.

    .. change::
        :tags: feature, extensions
        :tickets: 3054

        Added a new extension suite :mod:`sqlalchemy.ext.baked`.  This
        simple but unusual system allows for a dramatic savings in Python
        overhead for the construction and processing of orm :class:`.Query`
        objects, from query construction up through rendering of a string
        SQL statement.

        .. seealso::

            :ref:`baked_toplevel`

    .. change::
        :tags: bug, postgresql
        :tickets: 3319

        The Postgresql :class:`.postgresql.ENUM` type will emit a
        DROP TYPE instruction when a plain ``table.drop()`` is called,
        assuming the object is not associated directly with a
        :class:`.MetaData` object.   In order to accomodate the use case of
        an enumerated type shared between multiple tables, the type should
        be associated directly with the :class:`.MetaData` object; in this
        case the type will only be created at the metadata level, or if
        created directly.  The rules for create/drop of
        Postgresql enumerated types have been highly reworked in general.

        .. seealso::

            :ref:`change_3319`

    .. change::
        :tags: feature, orm
        :tickets: 3317

        Added a new event suite :class:`.QueryEvents`.  The
        :meth:`.QueryEvents.before_compile` event allows the creation
        of functions which may place additional modifications to
        :class:`.Query` objects before the construction of the SELECT
        statement.   It is hoped that this event be made much more
        useful via the advent of a new inspection system that will
        allow for detailed modifications to be made against
        :class:`.Query` objects in an automated fashion.

        .. seealso::

            :class:`.QueryEvents`


    .. change::
        :tags: feature, orm
        :tickets: 3249

        The subquery wrapping which occurs when joined eager loading
        is used with a one-to-many query that also features LIMIT,
        OFFSET, or DISTINCT has been disabled in the case of a one-to-one
        relationship, that is a one-to-many with
        :paramref:`.relationship.uselist` set to False.  This will produce
        more efficient queries in these cases.

        .. seealso::

            :ref:`change_3249`


    .. change::
        :tags: bug, orm
        :tickets: 3301

        Fixed bug where the session attachment error "object is already
        attached to session X" would fail to prevent the object from
        also being attached to the new session, in the case that execution
        continued after the error raise occurred.

    .. change::
        :tags: bug, ext
        :tickets: 3219, 3240

        Fixed bug where using an ``__abstract__`` mixin in the middle
        of a declarative inheritance hierarchy would prevent attributes
        and configuration being correctly propagated from the base class
        to the inheriting class.

    .. change::
        :tags: feature, sql
        :tickets: 918

        The SQL compiler now generates the mapping of expected columns
        such that they are matched to the received result set positionally,
        rather than by name.  Originally, this was seen as a way to handle
        cases where we had columns returned with difficult-to-predict names,
        though in modern use that issue has been overcome by anonymous
        labeling.   In this version, the approach basically reduces function
        call count per-result by a few dozen calls, or more for larger
        sets of result columns.  The approach still degrades into a modern
        version of the old approach if any discrepancy in size exists between
        the compiled set of columns versus what was received, so there's no
        issue for partially or fully textual compilation scenarios where these
        lists might not line up.

    .. change::
        :tags: feature, postgresql
        :pullreq: github:132

        The PG8000 dialect now supports the
        :paramref:`.create_engine.encoding` parameter, by setting up
        the client encoding on the connection which is then intercepted
        by pg8000.  Pull request courtesy Tony Locke.

    .. change::
        :tags: feature, postgresql
        :pullreq: github:132

        Added support for PG8000's native JSONB feature.  Pull request
        courtesy Tony Locke.

    .. change::
        :tags: change, orm

        Mapped attributes marked as deferred without explicit undeferral
        will now remain "deferred" even if their column is otherwise
        present in the result set in some way.   This is a performance
        enhancement in that an ORM load no longer spends time searching
        for each deferred column when the result set is obtained.  However,
        for an application that has been relying upon this, an explicit
        :func:`.undefer` or similar option should now be used.

    .. change::
        :tags: feature, orm
        :tickets: 3307

        Mapped state internals have been reworked to allow for a 50% reduction
        in callcounts specific to the "expiration" of objects, as in
        the "auto expire" feature of :meth:`.Session.commit` and
        for :meth:`.Session.expire_all`, as well as in the "cleanup" step
        which occurs when object states are garbage collected.

    .. change::
        :tags: bug, mysql

        The MySQL dialect now supports CAST on types that are constructed
        as :class:`.TypeDecorator` objects.

    .. change::
        :tags: bug, mysql
        :tickets: 3237

        A warning is emitted when :func:`.cast` is used with the MySQL
        dialect on a type where MySQL does not support CAST; MySQL only
        supports CAST on a subset of datatypes.   SQLAlchemy has for a long
        time just omitted the CAST for unsupported types in the case of
        MySQL.  While we don't want to change this now, we emit a warning
        to show that it's taken place.   A warning is also emitted when
        a CAST is used with an older MySQL version (< 4) that doesn't support
        CAST at all, it's skipped in this case as well.

    .. change::
        :tags: feature, sql
        :tickets: 3087

        Literal values within a :class:`.DefaultClause`, which is invoked
        when using the :paramref:`.Column.server_default` parameter, will
        now be rendered using the "inline" compiler, so that they are rendered
        as-is, rather than as bound parameters.

        .. seealso::

            :ref:`change_3087`

    .. change::
        :tags: feature, oracle
        :pullreq: github:152

        Added support for cx_oracle connections to a specific service
        name, as opposed to a tns name, by passing ``?service_name=<name>``
        to the URL.  Pull request courtesy Sławomir Ehlert.

    .. change::
        :tags: feature, mysql
        :tickets: 3155

        The MySQL dialect now renders TIMESTAMP with NULL / NOT NULL in
        all cases, so that MySQL 5.6.6 with the
        ``explicit_defaults_for_timestamp`` flag enabled will
        will allow TIMESTAMP to continue to work as expected when
        ``nullable=False``.  Existing applications are unaffected as
        SQLAlchemy has always emitted NULL for a TIMESTAMP column that
        is ``nullable=True``.

        .. seealso::

            :ref:`change_3155`

            :ref:`mysql_timestamp_null`

    .. change::
        :tags: bug, schema
        :tickets: 3299, 3067

        The :class:`.CheckConstraint` construct now supports naming
        conventions that include the token ``%(column_0_name)s``; the
        constraint expression is scanned for columns.  Additionally,
        naming conventions for check constraints that don't include the
        ``%(constraint_name)s`` token will now work for :class:`.SchemaType`-
        generated constraints, such as those of :class:`.Boolean` and
        :class:`.Enum`; this stopped working in 0.9.7 due to :ticket:`3067`.

        .. seealso::

            :ref:`naming_check_constraints`

            :ref:`naming_schematypes`


    .. change::
        :tags: feature, postgresql, pypy
        :tickets: 3052
        :pullreq: bitbucket:34

        Added support for the psycopg2cffi DBAPI on pypy.   Pull request
        courtesy shauns.

        .. seealso::

            :mod:`sqlalchemy.dialects.postgresql.psycopg2cffi`

    .. change::
        :tags: feature, orm
        :tickets: 3262
        :pullreq: bitbucket:38

        A warning is emitted when the same polymorphic identity is assigned
        to two different mappers in the same hierarchy.  This is typically a
        user error and means that the two different mapping types cannot be
        correctly distinguished at load time.  Pull request courtesy
        Sebastian Bank.

    .. change::
        :tags: feature, sql
        :pullreq: github:150

        The type of expression is reported when an object passed to a
        SQL expression unit can't be interpreted as a SQL fragment;
        pull request courtesy Ryan P. Kelly.

    .. change::
        :tags: bug, orm
        :tickets: 3227, 3242, 1326

        The primary :class:`.Mapper` of a :class:`.Query` is now passed to the
        :meth:`.Session.get_bind` method when calling upon
        :meth:`.Query.count`, :meth:`.Query.update`, :meth:`.Query.delete`,
        as well as queries against mapped columns,
        :obj:`.column_property` objects, and SQL functions and expressions
        derived from mapped columns.   This allows sessions that rely upon
        either customized :meth:`.Session.get_bind` schemes or "bound" metadata
        to work in all relevant cases.

        .. seealso::

            :ref:`bug_3227`

    .. change::
        :tags: enhancement, sql
        :tickets: 3074

        Custom dialects that implement :class:`.GenericTypeCompiler` can
        now be constructed such that the visit methods receive an indication
        of the owning expression object, if any.  Any visit method that
        accepts keyword arguments (e.g. ``**kw``) will in most cases
        receive a keyword argument ``type_expression``, referring to the
        expression object that the type is contained within.  For columns
        in DDL, the dialect's compiler class may need to alter its
        ``get_column_specification()`` method to support this as well.
        The ``UserDefinedType.get_col_spec()`` method will also receive
        ``type_expression`` if it provides ``**kw`` in its argument
        signature.

    .. change::
        :tags: bug, sql
        :tickets: 3288

        The multi-values version of :meth:`.Insert.values` has been
        repaired to work more usefully with tables that have Python-
        side default values and/or functions, as well as server-side
        defaults. The feature will now work with a dialect that uses
        "positional" parameters; a Python callable will also be
        invoked individually for each row just as is the case with an
        "executemany" style invocation; a server- side default column
        will no longer implicitly receive the value explicitly
        specified for the first row, instead refusing to invoke
        without an explicit value.

        .. seealso::

            :ref:`bug_3288`

    .. change::
        :tags: feature, general

        Structural memory use has been improved via much more significant use
        of ``__slots__`` for many internal objects.  This optimization is
        particularly geared towards the base memory size of large applications
        that have lots of tables and columns, and greatly reduces memory
        size for a variety of high-volume objects including event listening
        internals, comparator objects and parts of the ORM attribute and
        loader strategy system.

        .. seealso::

            :ref:`feature_slots`

    .. change::
        :tags: bug, mysql
        :tickets: 3283

        The :class:`.mysql.SET` type has been overhauled to no longer
        assume that the empty string, or a set with a single empty string
        value, is in fact a set with a single empty string; instead, this
        is by default treated as the empty set.  In order to handle persistence
        of a :class:`.mysql.SET` that actually wants to include the blank
        value ``''`` as a legitimate value, a new bitwise operational mode
        is added which is enabled by the
        :paramref:`.mysql.SET.retrieve_as_bitwise` flag, which will persist
        and retrieve values unambiguously using their bitflag positioning.
        Storage and retrieval of unicode values for driver configurations
        that aren't converting unicode natively is also repaired.

        .. seealso::

            :ref:`change_3283`


    .. change::
        :tags: feature, schema
        :tickets: 3282

        The DDL generation system of :meth:`.MetaData.create_all`
        and :meth:`.MetaData.drop_all` has been enhanced to in most
        cases automatically handle the case of mutually dependent
        foreign key constraints; the need for the
        :paramref:`.ForeignKeyConstraint.use_alter` flag is greatly
        reduced.  The system also works for constraints which aren't given
        a name up front; only in the case of DROP is a name required for
        at least one of the constraints involved in the cycle.

        .. seealso::

            :ref:`feature_3282`

    .. change::
        :tags: feature, schema

        Added a new accessor :attr:`.Table.foreign_key_constraints`
        to complement the :attr:`.Table.foreign_keys` collection,
        as well as :attr:`.ForeignKeyConstraint.referred_table`.

    .. change::
        :tags: bug, sqlite
        :tickets: 3244, 3261

        UNIQUE and FOREIGN KEY constraints are now fully reflected on
        SQLite both with and without names.  Previously, foreign key
        names were ignored and unnamed unique constraints were skipped.
        Thanks to Jon Nelson for assistance with this.

    .. change::
        :tags: feature, examples

        A new suite of examples dedicated to providing a detailed study
        into performance of SQLAlchemy ORM and Core, as well as the DBAPI,
        from multiple perspectives.  The suite runs within a container
        that provides built in profiling displays both through console
        output as well as graphically via the RunSnake tool.

        .. seealso::

            :ref:`examples_performance`

    .. change::
        :tags: feature, orm
        :tickets: 3100

        A new series of :class:`.Session` methods which provide hooks
        directly into the unit of work's facility for emitting INSERT
        and UPDATE statements has been created.  When used correctly,
        this expert-oriented system can allow ORM-mappings to be used
        to generate bulk insert and update statements batched into
        executemany groups, allowing the statements to proceed at
        speeds that rival direct use of the Core.

        .. seealso::

            :ref:`bulk_operations`

    .. change::
        :tags: feature, mssql
        :tickets: 3039

        SQL Server 2012 now recommends VARCHAR(max), NVARCHAR(max),
        VARBINARY(max) for large text/binary types.  The MSSQL dialect will
        now respect this based on version detection, as well as the new
        ``deprecate_large_types`` flag.

        .. seealso::

            :ref:`mssql_large_type_deprecation`

    .. change::
        :tags: bug, sqlite
        :tickets: 3257

        The SQLite dialect, when using the :class:`.sqlite.DATE`,
        :class:`.sqlite.TIME`,
        or :class:`.sqlite.DATETIME` types, and given a ``storage_format`` that
        only renders numbers, will render the types in DDL as
        ``DATE_CHAR``, ``TIME_CHAR``, and ``DATETIME_CHAR``, so that despite the
        lack of alpha characters in the values, the column will still
        deliver the "text affinity".  Normally this is not needed, as the
        textual values within the default storage formats already
        imply text.

        .. seealso::

            :ref:`sqlite_datetime`

    .. change::
        :tags: bug, engine
        :tickets: 3266

        The engine-level error handling and wrapping routines will now
        take effect in all engine connection use cases, including
        when user-custom connect routines are used via the
        :paramref:`.create_engine.creator` parameter, as well as when
        the :class:`.Connection` encounters a connection error on
        revalidation.

        .. seealso::

            :ref:`change_3266`

    .. change::
        :tags: feature, oracle

        New Oracle DDL features for tables, indexes: COMPRESS, BITMAP.
        Patch courtesy Gabor Gombas.

    .. change::
        :tags: bug, oracle

        An alias name will be properly quoted when referred to using the
        ``%(name)s`` token inside the :meth:`.Select.with_hint` method.
        Previously, the Oracle backend hadn't implemented this quoting.

    .. change::
        :tags: feature, oracle
        :tickets: 3220

        Added support for CTEs under Oracle.  This includes some tweaks
        to the aliasing syntax, as well as a new CTE feature
        :meth:`.CTE.suffix_with`, which is useful for adding in special
        Oracle-specific directives to the CTE.

        .. seealso::

            :ref:`change_3220`

    .. change::
        :tags: feature, mysql
        :tickets: 3121

        Updated the "supports_unicode_statements" flag to True for MySQLdb
        and Pymysql under Python 2.   This refers to the SQL statements
        themselves, not the parameters, and affects issues such as table
        and column names using non-ASCII characters.   These drivers both
        appear to support Python 2 Unicode objects without issue in modern
        versions.

    .. change::
        :tags: bug, mysql
        :tickets: 3263

        The :meth:`.ColumnOperators.match` operator is now handled such that the
        return type is not strictly assumed to be boolean; it now
        returns a :class:`.Boolean` subclass called :class:`.MatchType`.
        The type will still produce boolean behavior when used in Python
        expressions, however the dialect can override its behavior at
        result time.  In the case of MySQL, while the MATCH operator
        is typically used in a boolean context within an expression,
        if one actually queries for the value of a match expression, a
        floating point value is returned; this value is not compatible
        with SQLAlchemy's C-based boolean processor, so MySQL's result-set
        behavior now follows that of the :class:`.Float` type.
        A new operator object ``notmatch_op`` is also added to better allow
        dialects to define the negation of a match operation.

        .. seealso::

            :ref:`change_3263`

    .. change::
        :tags: bug, postgresql
        :tickets: 3264

        The :meth:`.PGDialect.has_table` method will now query against
        ``pg_catalog.pg_table_is_visible(c.oid)``, rather than testing
        for an exact schema match, when the schema name is None; this
        so that the method will also illustrate that temporary tables
        are present.  Note that this is a behavioral change, as Postgresql
        allows a non-temporary table to silently overwrite an existing
        temporary table of the same name, so this changes the behavior
        of ``checkfirst`` in that unusual scenario.

        .. seealso::

            :ref:`change_3264`

    .. change::
        :tags: bug, sql
        :tickets: 3260

        Fixed bug in :meth:`.Table.tometadata` method where the
        :class:`.CheckConstraint` associated with a :class:`.Boolean`
        or :class:`.Enum` type object would be doubled in the target table.
        The copy process now tracks the production of this constraint object
        as local to a type object.

    .. change::
        :tags: feature, orm
        :tickets: 3217

        Added a parameter :paramref:`.Query.join.isouter` which is synonymous
        with calling :meth:`.Query.outerjoin`; this flag is to provide a more
        consistent interface compared to Core :meth:`.FromClause.join`.
        Pull request courtesy Jonathan Vanasco.

    .. change::
        :tags: bug, sql
        :tickets: 3243

        The behavioral contract of the :attr:`.ForeignKeyConstraint.columns`
        collection has been made consistent; this attribute is now a
        :class:`.ColumnCollection` like that of all other constraints and
        is initialized at the point when the constraint is associated with
        a :class:`.Table`.

        .. seealso::

            :ref:`change_3243`

    .. change::
        :tags: bug, orm
        :tickets: 3256

        The :meth:`.PropComparator.of_type` modifier has been
        improved in conjunction with loader directives such as
        :func:`.joinedload` and :func:`.contains_eager` such that if
        two :meth:`.PropComparator.of_type` modifiers of the same
        base type/path are encountered, they will be joined together
        into a single "polymorphic" entity, rather than replacing
        the entity of type A with the one of type B.  E.g.
        a joinedload of ``A.b.of_type(BSub1)->BSub1.c`` combined with
        joinedload of ``A.b.of_type(BSub2)->BSub2.c`` will create a
        single joinedload of ``A.b.of_type((BSub1, BSub2)) -> BSub1.c, BSub2.c``,
        without the need for the ``with_polymorphic`` to be explicit
        in the query.

        .. seealso::

            :ref:`eagerloading_polymorphic_subtypes` - contains an updated
            example illustrating the new format.

    .. change::
        :tags: bug, sql
        :tickets: 3245

        The :attr:`.Column.key` attribute is now used as the source of
        anonymous bound parameter names within expressions, to match the
        existing use of this value as the key when rendered in an INSERT
        or UPDATE statement.   This allows :attr:`.Column.key` to be used
        as a "substitute" string to work around a difficult column name
        that doesn't translate well into a bound parameter name.   Note that
        the paramstyle is configurable on :func:`.create_engine` in any case,
        and most DBAPIs today support a named and positional style.

    .. change::
        :tags: bug, sql
        :pullreq: github:146

        Fixed the name of the :paramref:`.PoolEvents.reset.dbapi_connection`
        parameter as passed to this event; in particular this affects
        usage of the "named" argument style for this event.  Pull request
        courtesy Jason Goldberger.

    .. change::
        :tags: feature, sql
        :pullreq: github:139

        Added a new parameter :paramref:`.Table.tometadata.name` to
        the :meth:`.Table.tometadata` method.  Similar to
        :paramref:`.Table.tometadata.schema`, this argument causes the newly
        copied :class:`.Table` to take on the new name instead of
        the existing one.  An interesting capability this adds is that of
        copying a :class:`.Table` object to the *same* :class:`.MetaData`
        target with a new name.  Pull request courtesy n.d. parker.

    .. change::
        :tags: bug, orm
        :pullreq: github:137

        Repaired support of the ``copy.deepcopy()`` call when used by the
        :class:`.orm.util.CascadeOptions` argument, which occurs
        if ``copy.deepcopy()`` is being used with :func:`.relationship`
        (not an officially supported use case).  Pull request courtesy
        duesenfranz.

    .. change::
        :tags: bug, sql
        :tickets: 3170

        Reversing a change that was made in 0.9, the "singleton" nature
        of the "constants" :func:`.null`, :func:`.true`, and :func:`.false`
        has been reverted.   These functions returning a "singleton" object
        had the effect that different instances would be treated as the
        same regardless of lexical use, which in particular would impact
        the rendering of the columns clause of a SELECT statement.

        .. seealso::

            :ref:`bug_3170`

    .. change::
        :tags: bug, orm
        :tickets: 3139

        Fixed bug where :meth:`.Session.expunge` would not fully detach
        the given object if the object had been subject to a delete
        operation that was flushed, but not committed.  This would also
        affect related operations like :func:`.make_transient`.

        .. seealso::

            :ref:`bug_3139`

    .. change::
        :tags: bug, orm
        :tickets: 3230

        A warning is emitted in the case of multiple relationships that
        ultimately will populate a foreign key column in conflict with
        another, where the relationships are attempting to copy values
        from different source columns.  This occurs in the case where
        composite foreign keys with overlapping columns are mapped to
        relationships that each refer to a different referenced column.
        A new documentation section illustrates the example as well as how
        to overcome the issue by specifying "foreign" columns specifically
        on a per-relationship basis.

        .. seealso::

            :ref:`relationship_overlapping_foreignkeys`

    .. change::
        :tags: feature, sql
        :tickets: 3172

        Exception messages have been spiffed up a bit.  The SQL statement
        and parameters are not displayed if None, reducing confusion for
        error messages that weren't related to a statement.  The full
        module and classname for the DBAPI-level exception is displayed,
        making it clear that this is a wrapped DBAPI exception.  The
        statement and parameters themselves are bounded within a bracketed
        sections to better isolate them from the error message and from
        each other.

    .. change::
        :tags: bug, orm
        :tickets: 3228

        The :meth:`.Query.update` method will now convert string key
        names in the given dictionary of values into mapped attribute names
        against the mapped class being updated.  Previously, string names
        were taken in directly and passed to the core update statement without
        any means to resolve against the mapped entity.  Support for synonyms
        and hybrid attributes as the subject attributes of
        :meth:`.Query.update` are also supported.

        .. seealso::

            :ref:`bug_3228`

    .. change::
        :tags: bug, orm
        :tickets: 3035

        Improvements to the mechanism used by :class:`.Session` to locate
        "binds" (e.g. engines to use), such engines can be associated with
        mixin classes, concrete subclasses, as well as a wider variety
        of table metadata such as joined inheritance tables.

        .. seealso::

            :ref:`bug_3035`

    .. change::
        :tags: bug, general
        :tickets: 3218

        The ``__module__`` attribute is now set for all those SQL and
        ORM functions that are derived as "public factory" symbols, which
        should assist with documentation tools being able to report on the
        target module.

    .. change::
        :tags: feature, sql

        :meth:`.Insert.from_select` now includes Python and SQL-expression
        defaults if otherwise unspecified; the limitation where non-
        server column defaults aren't included in an INSERT FROM
        SELECT is now lifted and these expressions are rendered as
        constants into the SELECT statement.

        .. seealso::

            :ref:`feature_insert_from_select_defaults`

    .. change::
        :tags: bug, orm
        :tickets: 3233

        Fixed bug in single table inheritance where a chain of joins
        that included the same single inh entity more than once
        (normally this should raise an error) could, in some cases
        depending on what was being joined "from", implicitly alias the
        second case of the single inh entity, producing
        a query that "worked".   But as this implicit aliasing is not
        intended in the case of single table inheritance, it didn't
        really "work" fully and was very misleading, since it wouldn't
        always appear.

        .. seealso::

            :ref:`bug_3233`


    .. change::
        :tags: bug, orm
        :tickets: 3222

        The ON clause rendered when using :meth:`.Query.join`,
        :meth:`.Query.outerjoin`, or the standalone :func:`.orm.join` /
        :func:`.orm.outerjoin` functions to a single-inheritance subclass will
        now include the "single table criteria" in the ON clause even
        if the ON clause is otherwise hand-rolled; it is now added to the
        criteria using AND, the same way as if joining to a single-table
        target using relationship or similar.

        This is sort of in-between feature and bug.

        .. seealso::

            :ref:`migration_3222`

    .. change::
        :tags: feature, sql
        :tickets: 3184
        :pullreq: bitbucket:30

        The :class:`.UniqueConstraint` construct is now included when
        reflecting a :class:`.Table` object, for databases where this
        is applicable.  In order to achieve this
        with sufficient accuracy, MySQL and Postgresql now contain features
        that correct for the duplication of indexes and unique constraints
        when reflecting tables, indexes, and constraints.
        In the case of MySQL, there is not actually a "unique constraint"
        concept independent of a "unique index", so for this backend
        :class:`.UniqueConstraint` continues to remain non-present for a
        reflected :class:`.Table`.  For Postgresql, the query used to
        detect indexes against ``pg_index`` has been improved to check for
        the same construct in ``pg_constraint``, and the implicitly
        constructed unique index is not included with a
        reflected :class:`.Table`.

        In both cases, the  :meth:`.Inspector.get_indexes` and the
        :meth:`.Inspector.get_unique_constraints` methods return both
        constructs individually, but include a new token
        ``duplicates_constraint`` in the case of Postgresql or
        ``duplicates_index`` in the case
        of MySQL to indicate when this condition is detected.
        Pull request courtesy Johannes Erdfelt.

        .. seealso::

            :ref:`feature_3184`

    .. change::
        :tags: feature, postgresql
        :pullreq: github:134

        Added support for the FILTER keyword as applied to aggregate
        functions, supported by Postgresql 9.4.   Pull request
        courtesy Ilja Everilä.

        .. seealso::

            :ref:`feature_gh134`

    .. change::
        :tags: bug, sql, engine
        :tickets: 3215

        Fixed bug where a "branched" connection, that is the kind you get
        when you call :meth:`.Connection.connect`, would not share invalidation
        status with the parent.  The architecture of branching has been tweaked
        a bit so that the branched connection defers to the parent for
        all invalidation status and operations.

    .. change::
        :tags: bug, sql, engine
        :tickets: 3190

        Fixed bug where a "branched" connection, that is the kind you get
        when you call :meth:`.Connection.connect`, would not share transaction
        status with the parent.  The architecture of branching has been tweaked
        a bit so that the branched connection defers to the parent for
        all transactional status and operations.

    .. change::
        :tags: bug, declarative
        :tickets: 2670

        A relationship set up with :class:`.declared_attr` on
        a :class:`.AbstractConcreteBase` base class will now be configured
        on the abstract base mapping automatically, in addition to being
        set up on descendant concrete classes as usual.

        .. seealso::

            :ref:`feature_3150`

    .. change::
        :tags: feature, declarative
        :tickets: 3150

        The :class:`.declared_attr` construct has newly improved
        behaviors and features in conjunction with declarative.  The
        decorated function will now have access to the final column
        copies present on the local mixin when invoked, and will also
        be invoked exactly once for each mapped class, the returned result
        being memoized.   A new modifier :attr:`.declared_attr.cascading`
        is added as well.

        .. seealso::

            :ref:`feature_3150`

    .. change::
        :tags: feature, ext
        :tickets: 3210

        The :mod:`sqlalchemy.ext.automap` extension will now set
        ``cascade="all, delete-orphan"`` automatically on a one-to-many
        relationship/backref where the foreign key is detected as containing
        one or more non-nullable columns.  This argument is present in the
        keywords passed to :func:`.automap.generate_relationship` in this
        case and can still be overridden.  Additionally, if the
        :class:`.ForeignKeyConstraint` specifies ``ondelete="CASCADE"``
        for a non-nullable or ``ondelete="SET NULL"`` for a nullable set
        of columns, the argument ``passive_deletes=True`` is also added to the
        relationship.  Note that not all backends support reflection of
        ondelete, but backends that do include Postgresql and MySQL.

    .. change::
        :tags: feature, sql
        :tickets: 3206

        Added new method :meth:`.Select.with_statement_hint` and ORM
        method :meth:`.Query.with_statement_hint` to support statement-level
        hints that are not specific to a table.

    .. change::
        :tags: bug, sqlite
        :tickets: 3203
        :pullreq: bitbucket:31

        SQLite now supports reflection of unique constraints from
        temp tables; previously, this would fail with a TypeError.
        Pull request courtesy Johannes Erdfelt.

        .. seealso::

            :ref:`change_3204` - changes regarding SQLite temporary
            table and view reflection.

    .. change::
        :tags: bug, sqlite
        :tickets: 3204

        Added :meth:`.Inspector.get_temp_table_names` and
        :meth:`.Inspector.get_temp_view_names`; currently, only the
        SQLite and Oracle dialects support these methods.  The return of
        temporary table and view names has been **removed** from SQLite and
        Oracle's version of :meth:`.Inspector.get_table_names` and
        :meth:`.Inspector.get_view_names`; other database backends cannot
        support this information (such as MySQL), and the scope of operation
        is different in that the tables can be local to a session and
        typically aren't supported in remote schemas.

        .. seealso::

            :ref:`change_3204`

    .. change::
        :tags: feature, postgresql
        :tickets: 2891
        :pullreq: github:128

        Support has been added for reflection of materialized views
        and foreign tables, as well as support for materialized views
        within :meth:`.Inspector.get_view_names`, and a new method
        :meth:`.PGInspector.get_foreign_table_names` available on the
        Postgresql version of :class:`.Inspector`.  Pull request courtesy
        Rodrigo Menezes.

        .. seealso::

            :ref:`feature_2891`


    .. change::
        :tags: feature, orm

        Added new event handlers :meth:`.AttributeEvents.init_collection`
        and :meth:`.AttributeEvents.dispose_collection`, which track when
        a collection is first associated with an instance and when it is
        replaced.  These handlers supersede the :meth:`.collection.linker`
        annotation. The old hook remains supported through an event adapter.

    .. change::
        :tags: bug, orm
        :tickets: 3148, 3188

        A major rework to the behavior of expression labels, most
        specifically when used with ColumnProperty constructs with
        custom SQL expressions and in conjunction with the "order by
        labels" logic first introduced in 0.9.  Fixes include that an
        ``order_by(Entity.some_col_prop)`` will now make use of "order by
        label" rules even if Entity has been subject to aliasing,
        either via inheritance rendering or via the use of the
        ``aliased()`` construct; rendering of the same column property
        multiple times with aliasing (e.g. ``query(Entity.some_prop,
        entity_alias.some_prop)``) will label each occurrence of the
        entity with a distinct label, and additionally "order by
        label" rules will work for both (e.g.
        ``order_by(Entity.some_prop, entity_alias.some_prop)``).
        Additional issues that could prevent the "order by label"
        logic from working in 0.9, most notably that the state of a
        Label could change such that "order by label" would stop
        working depending on how things were called, has been fixed.

        .. seealso::

            :ref:`bug_3188`


    .. change::
        :tags: bug, mysql
        :tickets: 3186

        MySQL boolean symbols "true", "false" work again.  0.9's change
        in :ticket:`2682` disallowed the MySQL dialect from making use of the
        "true" and "false" symbols in the context of "IS" / "IS NOT", but
        MySQL supports this syntax even though it has no boolean type.
        MySQL remains "non native boolean", but the :func:`.true`
        and :func:`.false` symbols again produce the
        keywords "true" and "false", so that an expression like
        ``column.is_(true())`` again works on MySQL.

        .. seealso::

            :ref:`bug_3186`

    .. change::
        :tags: changed, mssql
        :tickets: 3182

        The hostname-based connection format for SQL Server when using
        pyodbc will no longer specify a default "driver name", and a warning
        is emitted if this is missing.  The optimal driver name for SQL Server
        changes frequently and is per-platform, so hostname based connections
        need to specify this.  DSN-based connections are preferred.

        .. seealso::

            :ref:`change_3182`

    .. change::
        :tags: changed, sql

        The :func:`~.expression.column` and :func:`~.expression.table`
        constructs are now importable from the "from sqlalchemy" namespace,
        just like every other Core construct.

    .. change::
        :tags: changed, sql
        :tickets: 2992

        The implicit conversion of strings to :func:`.text` constructs
        when passed to most builder methods of :func:`.select` as
        well as :class:`.Query` now emits a warning with just the
        plain string sent.   The textual conversion still proceeds normally,
        however.  The only method that accepts a string without a warning
        are the "label reference" methods like order_by(), group_by();
        these functions will now at compile time attempt to resolve a single
        string argument to a column or label expression present in the
        selectable; if none is located, the expression still renders, but
        you get the warning again. The rationale here is that the implicit
        conversion from string to text is more unexpected than not these days,
        and it is better that the user send more direction to the Core / ORM
        when passing a raw string as to what direction should be taken.
        Core/ORM tutorials have been updated to go more in depth as to how text
        is handled.

        .. seealso::

            :ref:`migration_2992`


    .. change::
        :tags: feature, engine
        :tickets: 3178

        A new style of warning can be emitted which will "filter" up to
        N occurrences of a parameterized string.   This allows parameterized
        warnings that can refer to their arguments to be delivered a fixed
        number of times until allowing Python warning filters to squelch them,
        and prevents memory from growing unbounded within Python's
        warning registries.

        .. seealso::

            :ref:`feature_3178`

    .. change::
        :tags: feature, orm

        The :class:`.Query` will raise an exception when :meth:`.Query.yield_per`
        is used with mappings or options where either
        subquery eager loading, or joined eager loading with collections,
        would take place.  These loading strategies are
        not currently compatible with yield_per, so by raising this error,
        the method is safer to use.  Eager loads can be disabled with
        the ``lazyload('*')`` option or :meth:`.Query.enable_eagerloads`.

        .. seealso::

            :ref:`migration_yield_per_eager_loading`

    .. change::
        :tags: bug, orm
        :tickets: 3177

        Changed the approach by which the "single inheritance criterion"
        is applied, when using :meth:`.Query.from_self`, or its common
        user :meth:`.Query.count`.  The criteria to limit rows to those
        with a certain type is now indicated on the inside subquery,
        not the outside one, so that even if the "type" column is not
        available in the columns clause, we can filter on it on the "inner"
        query.

        .. seealso::

            :ref:`migration_3177`

    .. change::
        :tags: changed, orm

        The ``proc()`` callable passed to the ``create_row_processor()``
        method of custom :class:`.Bundle` classes now accepts only a single
        "row" argument.

        .. seealso::

            :ref:`bundle_api_change`

    .. change::
        :tags: changed, orm

        Deprecated event hooks removed:  ``populate_instance``,
        ``create_instance``, ``translate_row``, ``append_result``

        .. seealso::

            :ref:`migration_deprecated_orm_events`

    .. change::
        :tags: bug, orm
        :tickets: 3145

        Made a small adjustment to the mechanics of lazy loading,
        such that it has less chance of interfering with a joinload() in the
        very rare circumstance that an object points to itself; in this
        scenario, the object refers to itself while loading its attributes
        which can cause a mixup between loaders.   The use case of
        "object points to itself" is not fully supported, but the fix also
        removes some overhead so for now is part of testing.

    .. change::
        :tags: feature, orm
        :tickets: 3176

        A new implementation for :class:`.KeyedTuple` used by the
        :class:`.Query` object offers dramatic speed improvements when
        fetching large numbers of column-oriented rows.

        .. seealso::

            :ref:`feature_3176`

    .. change::
        :tags: feature, orm
        :tickets: 3008

        The behavior of :paramref:`.joinedload.innerjoin` as well as
        :paramref:`.relationship.innerjoin` is now to use "nested"
        inner joins, that is, right-nested, as the default behavior when an
        inner join joined eager load is chained to an outer join eager load.

        .. seealso::

            :ref:`migration_3008`

    .. change::
        :tags: bug, orm
        :tickets: 3171

        The "resurrect" ORM event has been removed.  This event hook had
        no purpose since the old "mutable attribute" system was removed
        in 0.8.

    .. change::
        :tags: bug, sql
        :tickets: 3169

        Using :meth:`.Insert.from_select`  now implies ``inline=True``
        on :func:`.insert`.  This helps to fix a bug where an
        INSERT...FROM SELECT construct would inadvertently be compiled
        as "implicit returning" on supporting backends, which would
        cause breakage in the case of an INSERT that inserts zero rows
        (as implicit returning expects a row), as well as arbitrary
        return data in the case of an INSERT that inserts multiple
        rows (e.g. only the first row of many).
        A similar change is also applied to an INSERT..VALUES
        with multiple parameter sets; implicit RETURNING will no longer emit
        for this statement either.  As both of these constructs deal
        with varible numbers of rows, the
        :attr:`.ResultProxy.inserted_primary_key` accessor does not
        apply.   Previously, there was a documentation note that one
        may prefer ``inline=True`` with INSERT..FROM SELECT as some databases
        don't support returning and therefore can't do "implicit" returning,
        but there's no reason an INSERT...FROM SELECT needs implicit returning
        in any case.   Regular explicit :meth:`.Insert.returning` should
        be used to return variable numbers of result rows if inserted
        data is needed.

    .. change::
        :tags: bug, orm
        :tickets: 3167

        Fixed bug where attribute "set" events or columns with
        ``@validates`` would have events triggered within the flush process,
        when those columns were the targets of a "fetch and populate"
        operation, such as an autoincremented primary key, a Python side
        default, or a server-side default "eagerly" fetched via RETURNING.

    .. change::
        :tags: feature, oracle

        Added support for the Oracle table option ON COMMIT.

    .. change::
        :tags: feature, postgresql
        :tickets: 2051

        Added support for PG table options TABLESPACE, ON COMMIT,
        WITH(OUT) OIDS, and INHERITS, when rendering DDL via
        the :class:`.Table` construct.   Pull request courtesy
        malikdiarra.

        .. seealso::

            :ref:`postgresql_table_options`

    .. change::
        :tags: bug, orm, py3k

        The :class:`.IdentityMap` exposed from :attr:`.Session.identity_map`
        now returns lists for ``items()`` and ``values()`` in Py3K.
        Early porting to Py3K here had these returning iterators, when
        they technically should be "iterable views"..for now, lists are OK.

    .. change::
        :tags: orm, feature

        UPDATE statements can now be batched within an ORM flush
        into more performant executemany() call, similarly to how INSERT
        statements can be batched; this will be invoked within flush
        to the degree that subsequent UPDATE statements for the
        same mapping and table involve the identical columns within the
        VALUES clause, that no SET-level SQL expressions
        are embedded, and that the versioning requirements for the mapping
        are compatible with the backend dialect's ability to return
        a correct rowcount for an executemany operation.

    .. change::
        :tags: engine, bug
        :tickets: 3163

        Removing (or adding) an event listener at the same time that the event
        is being run itself, either from inside the listener or from a
        concurrent thread, now raises a RuntimeError, as the collection used is
        now an instance of ``colletions.deque()`` and does not support changes
        while being iterated.  Previously, a plain Python list was used where
        removal from inside the event itself would produce silent failures.

    .. change::
        :tags: orm, feature
        :tickets: 2963

        The ``info`` parameter has been added to the constructor for
        :class:`.SynonymProperty` and :class:`.ComparableProperty`.

    .. change::
        :tags: sql, feature
        :tickets: 2963

        The ``info`` parameter has been added as a constructor argument
        to all schema constructs including :class:`.MetaData`,
        :class:`.Index`, :class:`.ForeignKey`, :class:`.ForeignKeyConstraint`,
        :class:`.UniqueConstraint`, :class:`.PrimaryKeyConstraint`,
        :class:`.CheckConstraint`.

    .. change::
        :tags: orm, feature
        :tickets: 2971

        The :attr:`.InspectionAttr.info` collection is now moved down to
        :class:`.InspectionAttr`, where in addition to being available
        on all :class:`.MapperProperty` objects, it is also now available
        on hybrid properties, association proxies, when accessed via
        :attr:`.Mapper.all_orm_descriptors`.

    .. change::
        :tags: sql, feature
        :tickets: 3027
        :pullrequest: bitbucket:29

        The :paramref:`.Table.autoload_with` flag now implies that
        :paramref:`.Table.autoload` should be ``True``.  Pull request
        courtesy Malik Diarra.

    .. change::
        :tags: postgresql, feature
        :pullreq: github:126

        Added new method :meth:`.PGInspector.get_enums`, when using the
        inspector for Postgresql will provide a list of ENUM types.
        Pull request courtesy Ilya Pekelny.

    .. change::
        :tags: mysql, bug

        The MySQL dialect will now disable :meth:`.ConnectionEvents.handle_error`
        events from firing for those statements which it uses internally
        to detect if a table exists or not.   This is achieved using an
        execution option ``skip_user_error_events`` that disables the handle
        error event for the scope of that execution.   In this way, user code
        that rewrites exceptions doesn't need to worry about the MySQL
        dialect or other dialects that occasionally need to catch
        SQLAlchemy specific exceptions.

    .. change::
        :tags: mysql, bug
        :tickets: 2515

        Changed the default value of "raise_on_warnings" to False for
        MySQLconnector.  This was set at True for some reason.  The "buffered"
        flag unfortunately must stay at True as MySQLconnector does not allow
        a cursor to be closed unless all results are fully fetched.

    .. change::
        :tags: bug, orm
        :tickets: 3117

        The "evaluator" for query.update()/delete() won't work with multi-table
        updates, and needs to be set to `synchronize_session=False` or
        `synchronize_session='fetch'`; this now raises an exception, with a
        message to change the synchronize setting.
        This is upgraded from a warning emitted as of 0.9.7.

    .. change::
        :tags: removed

        The Drizzle dialect has been removed from the Core; it is now
        available as `sqlalchemy-drizzle <https://bitbucket.org/zzzeek/sqlalchemy-drizzle>`_,
        an independent, third party dialect.  The dialect is still based
        almost entirely off of the MySQL dialect present in SQLAlchemy.

        .. seealso::

            :ref:`change_2984`

    .. change::
        :tags: enhancement, orm
        :tickets: 3061

        Adjustment to attribute mechanics concerning when a value is
        implicitly initialized to None via first access; this action,
        which has always resulted in a population of the attribute,
        no longer does so; the None value is returned but the underlying
        attribute receives no set event.  This is consistent with how collections
        work and allows attribute mechanics to behave more consistently;
        in particular, getting an attribute with no value does not squash
        the event that should proceed if the value is actually set to None.

        .. seealso::

        	:ref:`migration_3061`

	.. change::
		:tags: feature, sql
		:tickets: 3034

		The :meth:`.Select.limit` and :meth:`.Select.offset` methods
		now accept any SQL expression, in addition to integer values, as
		arguments.  Typically this is used to allow a bound parameter to be
		passed, which can be substituted with a value later thus allowing
		Python-side caching of the SQL query.   The implementation
		here is fully backwards compatible with existing third party dialects,
		however those dialects which implement special LIMIT/OFFSET systems
		will need modification in order to take advantage of the new
		capabilities.  Limit and offset also support "literal_binds" mode,
        where bound parameters are rendered inline as strings based on
        a compile-time option.
        Work on this feature is courtesy of Dobes Vandermeer.


		.. seealso::

			:ref:`feature_3034`.
