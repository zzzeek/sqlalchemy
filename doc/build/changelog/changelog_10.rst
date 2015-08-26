

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
    :version: 1.0.8
    :released: July 22, 2015

    .. change::
        :tags: bug, misc
        :tickets: 3494

        Fixed an issue where a particular base class within utils
        didn't implement ``__slots__``, and therefore meant all subclasses
        of that class didn't either, negating the rationale for ``__slots__``
        to be in use.  Didn't cause any issue except on IronPython
        which apparently does not implement ``__slots__`` behavior compatibly
        with cPython.


.. changelog::
    :version: 1.0.7
    :released: July 20, 2015

    .. change::
        :tags: feature, sql
        :tickets: 3459
        :pullreq: bitbucket:56

        Added a :meth:`.ColumnElement.cast` method which performs the same
        purpose as the standalone :func:`.cast` function.  Pull request
        courtesy Sebastian Bank.

    .. change::
        :tags: bug, engine
        :tickets: 3481

        Fixed regression where new methods on :class:`.ResultProxy` used
        by the ORM :class:`.Query` object (part of the performance
        enhancements of :ticket:`3175`) would not raise the "this result
        does not return rows" exception in the case where the driver
        (typically MySQL) fails to generate cursor.description correctly;
        an AttributeError against NoneType would be raised instead.

    .. change::
        :tags: bug, engine
        :tickets: 3483

        Fixed regression where :meth:`.ResultProxy.keys` would return
        un-adjusted internal symbol names for "anonymous" labels, which
        are the "foo_1" types of labels we see generated for SQL functions
        without labels and similar.  This was a side effect of the
        performance enhancements implemented as part of #918.


    .. change::
        :tags: bug, sql
        :tickets: 3490

        Fixed bug where coersion of literal ``True`` or ``False`` constant
        in conjunction with :func:`.and_` or :func:`.or_` would fail
        with an AttributeError.

    .. change::
        :tags: bug, sql
        :tickets: 3485

        Fixed potential issue where a custom subclass
        of :class:`.FunctionElement` or other column element that incorrectly
        states 'None' or any other invalid object as the ``.type``
        attribute will report this exception instead of recursion overflow.

    .. change::
        :tags: bug, sql
        :pullreq: github:188

        Fixed bug where the modulus SQL operator wouldn't work in reverse
        due to a missing ``__rmod__`` method.  Pull request courtesy
        dan-gittik.

    .. change::
        :tags: feature, schema
        :pullreq: github:186

        Added support for the MINVALUE, MAXVALUE, NO MINVALUE, NO MAXVALUE,
        and CYCLE arguments for CREATE SEQUENCE as supported by Postgresql
        and Oracle.  Pull request courtesy jakeogh.

    .. change::
        :tags: bug, orm, declarative
        :tickets: 3480

        Fixed bug in :class:`.AbstractConcreteBase` extension where
        a column setup on the ABC base which had a different attribute
        name vs. column name would not be correctly mapped on the final
        base class.   The failure on 0.9 would be silent whereas on
        1.0 it raised an ArgumentError, so may not have been noticed
        prior to 1.0.

    .. change::
        :tags: bug, orm
        :tickets: 3469

        Fixed 1.0 regression where value objects that override
        ``__eq__()`` to return a non-boolean-capable object, such as
        some geoalchemy types as well as numpy types, were being tested
        for ``bool()`` during a unit of work update operation, where in
        0.9 the return value of ``__eq__()`` was tested against "is True"
        to guard against this.

    .. change::
        :tags: bug, orm
        :tickets: 3468

        Fixed 1.0 regression where a "deferred" attribute would not populate
        correctly if it were loaded within the "optimized inheritance load",
        which is a special SELECT emitted in the case of joined table
        inheritance used to populate expired or unloaded attributes against
        a joined table without loading the base table.  This is related to
        the fact that SQLA 1.0 no longer guesses about loading deferred
        columns and must be directed explicitly.

    .. change::
        :tags: bug, orm
        :tickets: 3466

        Fixed 1.0 regression where the "parent entity" of a synonym-
        mapped attribute on top of an :func:`.aliased` object would
        resolve to the original mapper, not the :func:`.aliased`
        version of it, thereby causing problems for a :class:`.Query`
        that relies on this attribute (e.g. it's the only representative
        attribute given in the constructor) to figure out the correct FROM
        clause for the query.

.. changelog::
    :version: 1.0.6
    :released: June 25, 2015

    .. change::
        :tags: bug, orm
        :tickets: 3465

        Fixed a major regression in the 1.0 series where the version_id_counter
        feature would cause an object's version counter to be incremented
        when there was no net change to the object's row, but instead an object
        related to it via relationship (e.g. typically many-to-one)
        were associated or de-associated with it, resulting in an UPDATE
        statement that updates the object's version counter and nothing else.
        In the use case where the relatively recent "server side" and/or
        "programmatic/conditional" version counter feature were used
        (e.g. setting version_id_generator to False), the bug could cause an
        UPDATE without a valid SET clause to be emitted.

    .. change::
        :tags: bug, mssql
        :tickets: 3464

        Fixed issue when using :class:`.VARBINARY` type in conjunction with
        an INSERT of NULL + pyodbc; pyodbc requires a special
        object be passed in order to persist NULL.  As the :class:`.VARBINARY`
        type is now usually the default for :class:`.LargeBinary` due to
        :ticket:`3039`, this issue is partially a regression in 1.0.
        The pymssql driver appears to be unaffected.

    .. change::
        :tags: bug, postgresql, pypy
        :tickets: 3439

        Re-fixed this issue first released in 1.0.5 to fix psycopg2cffi
        JSONB support once again, as they suddenly
        switched on unconditional decoding of JSONB types in version 2.7.1.
        Version detection now specifies 2.7.1 as where we should expect
        the DBAPI to do json encoding for us.

    .. change::
        :tags: feature, postgresql
        :tickets: 3455
        :pullreq: github:179

        Added support for storage parameters under CREATE INDEX, using
        a new keyword argument ``postgresql_with``.  Also added support for
        reflection to support both the ``postgresql_with`` flag as well
        as the ``postgresql_using`` flag, which will now be set on
        :class:`.Index` objects that are reflected, as well present
        in a new "dialect_options" dictionary in the result of
        :meth:`.Inspector.get_indexes`.  Pull request courtesy Pete Hollobon.

        .. seealso::

            :ref:`postgresql_index_storage`

    .. change::
        :tags: bug, orm
        :tickets: 3462

        Fixed 1.0 regression where the enhanced behavior of single-inheritance
        joins of :ticket:`3222` takes place inappropriately
        for a JOIN along explicit join criteria with a single-inheritance
        subclass that does not make use of any discriminator, resulting
        in an additional "AND NULL" clause.

    .. change::
        :tags: bug, postgresql
        :tickets: 3454

        Repaired the :class:`.ExcludeConstraint` construct to support common
        features that other objects like :class:`.Index` now do, that
        the column expression may be specified as an arbitrary SQL
        expression such as :obj:`.cast` or :obj:`.text`.

    .. change::
        :tags: feature, postgresql
        :pullreq: github:182

        Added new execution option ``max_row_buffer`` which is interpreted
        by the psycopg2 dialect when the ``stream_results`` option is
        used, which sets a limit on the size of the row buffer that may be
        allocated.  This value is also provided based on the integer
        value sent to :meth:`.Query.yield_per`.  Pull request courtesy
        mcclurem.

    .. change::
        :tags: bug, orm
        :tickets: 3451
        :pullreq: github:181

        Fixed bug in new :meth:`.Session.bulk_update_mappings` feature where
        the primary key columns used in the WHERE clause to locate the row
        would also be included in the SET clause, setting their value to
        themselves unnecessarily.  Pull request courtesy Patrick Hayes.

    .. change::
        :tags: bug, orm
        :tickets: 3448

        Fixed an unexpected-use regression whereby custom :class:`.Comparator`
        objects that made use of the ``__clause_element__()`` method and
        returned an object that was an ORM-mapped
        :class:`.InstrumentedAttribute` and not explicitly a
        :class:`.ColumnElement` would fail to be correctly
        handled when passed as an expression to :meth:`.Session.query`.
        The logic in 0.9 happened to succeed on this, so this use case is now
        supported.

    .. change::
        :tags: bug, sql
        :tickets: 3445

        Fixed a bug where clause adaption as applied to a :class:`.Label`
        object would fail to accommodate the labeled SQL expression
        in all cases, such that any SQL operation that made use of
        :meth:`.Label.self_group` would use the original unadapted
        expression.  One effect of this would be that an ORM :func:`.aliased`
        construct would not fully accommodate attributes mapped by
        :obj:`.column_property`, such that the un-aliased table could
        leak out when the property were used in some kinds of SQL
        comparisons.

    .. change::
        :tags: bug, documentation
        :tickets: 2077

        Fixed an internal "memoization" routine for method types such
        that a Python descriptor is no longer used; repairs inspectability
        of these methods including support for Sphinx documentation.

.. changelog::
    :version: 1.0.5
    :released: June 7, 2015

    .. change::
        :tags: feature, engine

        Added new engine event :meth:`.ConnectionEvents.engine_disposed`.
        Called after the :meth:`.Engine.dispose` method is called.

    .. change::
        :tags: bug, postgresql, pypy
        :tickets: 3439

        Repaired some typing and test issues related to the pypy
        psycopg2cffi dialect, in particular that the current 2.7.0 version
        does not have native support for the JSONB type.  The version detection
        for psycopg2 features has been tuned into a specific sub-version
        for psycopg2cffi.  Additionally, test coverage has been enabled
        for the full series of psycopg2 features under psycopg2cffi.

    .. change::
        :tags: feature, ext
        :pullreq: bitbucket:54

        Added support for ``*args`` to be passed to the baked query
        initial callable, in the same way that ``*args`` are supported
        for the :meth:`.BakedQuery.add_criteria` and
        :meth:`.BakedQuery.with_criteria` methods.  Initial PR courtesy
        Naoki INADA.

    .. change::
        :tags: bug, engine
        :tickets: 3435

        Fixed bug where known boolean values used by
        :func:`.engine_from_config` were not being parsed correctly;
        these included ``pool_threadlocal`` and the psycopg2 argument
        ``use_native_unicode``.

    .. change::
        :tags: bug, mssql
        :tickets: 3424, 3430

        Added a new dialect flag to the MSSQL dialect
        ``legacy_schema_aliasing`` which when set to False will disable a
        very old and obsolete behavior, that of the compiler's
        attempt to turn all schema-qualified table names into alias names,
        to work around old and no longer locatable issues where SQL
        server could not parse a multi-part identifier name in all
        circumstances.   The behavior prevented more
        sophisticated statements from working correctly, including those which
        use hints, as well as CRUD statements that embed correlated SELECT
        statements.  Rather than continue to repair the feature to work
        with more complex statements, it's better to just disable it
        as it should no longer be needed for any modern SQL server
        version.  The flag defaults to True for the 1.0.x series, leaving
        current behavior unchanged for this version series.  In the 1.1
        series, it will default to False.  For the 1.0 series,
        when not set to either value explicitly, a warning is emitted
        when a schema-qualified table is first used in a statement, which
        suggests that the flag be set to False for all modern SQL Server
        versions.

        .. seealso::

            :ref:`legacy_schema_rendering`

    .. change::
        :tags: feature, engine
        :tickets: 3379

        Adjustments to the engine plugin hook, such that the
        :meth:`.URL.get_dialect` method will continue to return the
        ultimate :class:`.Dialect` object when a dialect plugin is used,
        without the need for the caller to be aware of the
        :meth:`.Dialect.get_dialect_cls` method.


    .. change::
        :tags: bug, ext
        :tickets: 3427

        Fixed regression in the :mod:`sqlalchemy.ext.mutable` extension
        as a result of the bugfix for :ticket:`3167`,
        where attribute and validation events are no longer
        called within the flush process.  The mutable
        extension was relying upon this behavior in the case where a column
        level Python-side default were responsible for generating the new value
        on INSERT or UPDATE, or when a value were fetched from the RETURNING
        clause for "eager defaults" mode.  The new value would not be subject
        to any event when populated and the mutable extension could not
        establish proper coercion or history listening.  A new event
        :meth:`.InstanceEvents.refresh_flush` is added which the mutable
        extension now makes use of for this use case.

    .. change::
        :tags: feature, orm
        :tickets: 3427

        Added new event :meth:`.InstanceEvents.refresh_flush`, invoked
        when an INSERT or UPDATE level default value fetched via RETURNING
        or Python-side default is invoked within the flush process.  This
        is to provide a hook that is no longer present as a result of
        :ticket:`3167`, where attribute and validation events are no longer
        called within the flush process.

    .. change::
        :tags: feature, ext
        :tickets: 3427

        Added a new semi-public method to :class:`.MutableBase`
        :meth:`.MutableBase._get_listen_keys`.  Overriding this method
        is needed in the case where a :class:`.MutableBase` subclass needs
        events to propagate for attribute keys other than the key to which
        the mutable type is associated with, when intercepting the
        :meth:`.InstanceEvents.refresh` or
        :meth:`.InstanceEvents.refresh_flush` events.  The current example of
        this is composites using :class:`.MutableComposite`.

    .. change::
        :tags: bug, engine
        :tickets: 3421

        Added support for the case of the misbehaving DBAPI that has
        pep-249 exception names linked to exception classes of an entirely
        different name, preventing SQLAlchemy's own exception wrapping from
        wrapping the error appropriately.
        The SQLAlchemy dialect in use needs to implement a new
        accessor :attr:`.DefaultDialect.dbapi_exception_translation_map`
        to support this feature; this is implemented now for the py-postgresql
        dialect.

    .. change::
        :tags: bug, orm
        :tickets: 3420

        The "lightweight named tuple" used when a :class:`.Query` returns
        rows failed to implement ``__slots__`` correctly such that it still
        had a ``__dict__``.    This is resolved, but in the extremely
        unlikely case someone was assigning values to the returned tuples,
        that will no longer work.

    .. change::
        :tags: bug, engine
        :tickets: 3419

        Fixed bug involving the case when pool checkout event handlers are used
        and connection attempts are made in the handler itself which fail,
        the owning connection record would not be freed until the stack trace
        of the connect error itself were freed.   For the case where a test
        pool of only a single connection were used, this means the pool would
        be fully checked out until that stack trace were freed.  This mostly
        impacts very specific debugging scenarios and is unlikely to have been
        noticable in any production application.  The fix applies an
        explicit checkin of the record before re-raising the caught exception.


.. changelog::
    :version: 1.0.4
    :released: May 7, 2015

    .. change::
        :tags: bug, orm
        :tickets: 3416

        Fixed unexpected-use regression where in the odd case that the
        primaryjoin of a relationship involved comparison to an unhashable
        type such as an HSTORE, lazy loads would fail due to a hash-oriented
        check on the statement parameters, modified in 1.0 as a result of
        :ticket:`3061` to use hashing and modified in :ticket:`3368`
        to occur in cases more common than "load on pending".
        The values are now checked for the ``__hash__`` attribute beforehand.

    .. change::
        :tags: bug, orm
        :tickets: 3412, 3347

        Liberalized an assertion that was added as part of :ticket:`3347`
        to protect against unknown conditions when splicing inner joins
        together within joined eager loads with ``innerjoin=True``; if
        some of the joins use a "secondary" table, the assertion needs to
        unwrap further joins in order to pass.

    .. change::
        :tags: bug, schema
        :tickets: 3411

        Fixed bug in enhanced constraint-attachment logic introduced in
        :ticket:`3341` where in the unusual case of a constraint that refers
        to a mixture of :class:`.Column` objects and string column names
        at the same time, the auto-attach-on-column-attach logic will be
        skipped; for the constraint to be auto-attached in this case,
        all columns must be assembled on the target table up front.
        Added a new section to the migration document regarding the
        original feature as well as this change.

        .. seealso::

            :ref:`change_3341`

    .. change::
        :tags: bug, orm
        :tickets: 3409, 3320

        Repaired / added to tests yet more expressions that were reported
        as failing with the new 'entity' key value added to
        :attr:`.Query.column_descriptions`, the logic to discover the "from"
        clause is again reworked to accommodate columns from aliased classes,
        as well as to report the correct value for the "aliased" flag in these
        cases.


.. changelog::
    :version: 1.0.3
    :released: April 30, 2015

    .. change::
        :tags: bug, orm, pypy
        :tickets: 3405

        Fixed regression from 0.9.10 prior to release due to :ticket:`3349`
        where the check for query state on :meth:`.Query.update` or
        :meth:`.Query.delete` compared the empty tuple to itself using ``is``,
        which fails on Pypy to produce ``True`` in this case; this would
        erronously emit a warning in 0.9 and raise an exception in 1.0.

    .. change::
        :tags: feature, engine
        :tickets: 3379

        New features added to support engine/pool plugins with advanced
        functionality.   Added a new "soft invalidate" feature to the
        connection pool at the level of the checked out connection wrapper
        as well as the :class:`._ConnectionRecord`.  This works similarly
        to a modern pool invalidation in that connections aren't actively
        closed, but are recycled only on next checkout; this is essentially
        a per-connection version of that feature.  A new event
        :class:`.PoolEvents.soft_invalidate` is added to complement it.

        Also added new flag
        :attr:`.ExceptionContext.invalidate_pool_on_disconnect`.
        Allows an error handler within :meth:`.ConnectionEvents.handle_error`
        to maintain a "disconnect" condition, but to handle calling invalidate
        on individual connections in a specific manner within the event.

    .. change::
        :tags: feature, engine
        :tickets: 3355

        Added new event :class:`.DialectEvents.do_connect`, which allows
        interception / replacement of when the :meth:`.Dialect.connect`
        hook is called to create a DBAPI connection.  Also added
        dialect plugin hooks :meth:`.Dialect.get_dialect_cls` and
        :meth:`.Dialect.engine_created` which allow external plugins to
        add events to existing dialects using entry points.

    .. change::
        :tags: bug, orm
        :tickets: 3403, 3320

        Fixed regression from 0.9.10 prior to release where the new addition
        of ``entity`` to the :attr:`.Query.column_descriptions` accessor
        would fail if the target entity was produced from a core selectable
        such as a :class:`.Table` or :class:`.CTE` object.

    .. change::
        :tags: feature, sql

        Added a placeholder method :meth:`.TypeEngine.compare_against_backend`
        which is now consumed by Alembic migrations as of 0.7.6.  User-defined
        types can implement this method to assist in the comparison of
        a type against one reflected from the database.

    .. change::
        :tags: bug, orm
        :tickets: 3402

        Fixed regression within the flush process when an attribute were
        set to a SQL expression for an UPDATE, and the SQL expression when
        compared to the previous value of the attribute would produce a SQL
        comparison other than ``==`` or ``!=``, the exception "Boolean value
        of this clause is not defined" would raise.   The fix ensures that
        the unit of work will not interpret the SQL expression in this way.

    .. change::
        :tags: bug, ext
        :tickets: 3397

        Fixed bug in association proxy where an any()/has()
        on an relationship->scalar non-object attribute comparison would fail,
        e.g.
        ``filter(Parent.some_collection_to_attribute.any(Child.attr == 'foo'))``

    .. change::
        :tags: bug, sql
        :tickets: 3396

        Fixed bug where the truncation of long labels in SQL could produce
        a label that overlapped another label that is not truncated; this
        because the length threshhold for truncation was greater than
        the portion of the label that remains after truncation.  These
        two values have now been made the same; label_length - 6.
        The effect here is that shorter column labels will be "truncated"
        where they would not have been truncated before.

    .. change::
        :tags: bug, orm
        :tickets: 3392

        Fixed unexpected use regression due to :ticket:`2992` where
        textual elements placed
        into the :meth:`.Query.order_by` clause in conjunction with joined
        eager loading would be added to the columns clause of the inner query
        in such a way that they were assumed to be table-bound column names,
        in the case where the joined eager load needs to wrap the query
        in a subquery to accommodate for a limit/offset.

        Originally, the behavior here was intentional, in that a query such
        as ``query(User).order_by('name').limit(1)``
        would order by ``user.name`` even if the query was modified by
        joined eager loading to be within a subquery, as ``'name'`` would
        be interpreted as a symbol to be located within the FROM clauses,
        in this case ``User.name``, which would then be copied into the
        columns clause to ensure it were present for ORDER BY.  However, the
        feature fails to anticipate the case where ``order_by("name")`` refers
        to a specific label name present in the local columns clause already
        and not a name bound to a selectable in the FROM clause.

        Beyond that, the feature also fails for deprecated cases such as
        ``order_by("name desc")``, which, while it emits a
        warning that :func:`.text` should be used here (note that the issue
        does not impact cases where :func:`.text` is used explicitly),
        still produces a different query than previously where the "name desc"
        expression is copied into the columns clause inappropriately.  The
        resolution is such that the "joined eager loading" aspect of the
        feature will skip over these so-called "label reference" expressions
        when augmenting the inner columns clause, as though they were
        :func:`.text` constructs already.

    .. change::
        :tags: bug, sql
        :tickets: 3391

        Fixed regression due to :ticket:`3282` where the ``tables`` collection
        passed as a keyword argument to the :meth:`.DDLEvents.before_create`,
        :meth:`.DDLEvents.after_create`, :meth:`.DDLEvents.before_drop`, and
        :meth:`.DDLEvents.after_drop` events would no longer be a list
        of tables, but instead a list of tuples which contained a second
        entry with foreign keys to be added or dropped.  As the ``tables``
        collection, while documented as not necessarily stable, has come
        to be relied upon, this change is considered a regression.
        Additionally, in some cases for "drop", this collection would
        be an iterator that would cause the operation to fail if
        prematurely iterated.   The collection is now a list of table
        objects in all cases and test coverage for the format of this
        collection is now added.


    .. change::
        :tags: bug, orm
        :tickets: 3388

        Fixed a regression regarding the :meth:`.MapperEvents.instrument_class`
        event where its invocation was moved to be after the class manager's
        instrumentation of the class, which is the opposite of what the
        documentation for the event explicitly states.  The rationale for the
        switch was due to Declarative taking the step of setting up
        the full "instrumentation manager" for a class before it was mapped
        for the purpose of the new ``@declared_attr`` features
        described in :ref:`feature_3150`, but the change was also made
        against the classical use of :func:`.mapper` for consistency.
        However, SQLSoup relies upon the instrumentation event happening
        before any instrumentation under classical mapping.
        The behavior is reverted in the case of classical and declarative
        mapping, the latter implemented by using a simple memoization
        without using class manager.

    .. change::
        :tags: bug, orm
        :tickets: 3387

        Fixed issue in new :meth:`.QueryEvents.before_compile` event where
        changes made to the :class:`.Query` object's collection of entities
        to load within the event would render in the SQL, but would not
        be reflected during the loading process.

.. changelog::
    :version: 1.0.2
    :released: April 24, 2015

    .. change::
        :tags: bug, sql
        :tickets: 3338, 3385

        Fixed a regression that was incorrectly fixed in 1.0.0b4
        (hence becoming two regressions); reports that
        SELECT statements would GROUP BY a label name and fail was misconstrued
        that certain backends such as SQL Server should not be emitting
        ORDER BY or GROUP BY on a simple label name at all; when in fact,
        we had forgotten that 0.9 was already emitting ORDER BY on a simple
        label name for all backends, as described in :ref:`migration_1068`,
        even though 1.0 includes a rewrite of this logic as part of
        :ticket:`2992`.  As far
        as emitting GROUP BY against a simple label, even Postgresql has
        cases where it will raise an error even though the label to group
        on should be apparent, so it is clear that GROUP BY should never
        be rendered in this way automatically.

        In 1.0.2, SQL Server, Firebird and others will again emit ORDER BY on
        a simple label name when passed a
        :class:`.Label` construct that is also present in the columns clause.
        Additionally, no backend will emit GROUP BY against the simple label
        name only when passed a :class:`.Label` construct.

    .. change::
        :tags: bug, orm, declarative
        :tickets: 3383

        Fixed unexpected use regression regarding the declarative
        ``__declare_first__`` and ``__declare_last__`` accessors where these
        would no longer be called on the superclass of the declarative base.

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

        Fixed unexpected use regression cause by :ticket:`3061` where
        the NEVER_SET
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

        .. note:: this resolution was incorrect, please see version 1.0.2
           for a rework of this resolution.

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

        .. seealso::

            :ref:`change_3341`

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
        :tags: change, orm, declarative
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

        Fixed unexpected use regression from pullreq github:137 where
        Py2K unicode literals (e.g. ``u""``) would not be accepted by the
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
        :tags: feature, ext
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
        :tags: bug, orm, declarative
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
        :tags: bug, orm, declarative
        :tickets: 2670

        A relationship set up with :class:`.declared_attr` on
        a :class:`.AbstractConcreteBase` base class will now be configured
        on the abstract base mapping automatically, in addition to being
        set up on descendant concrete classes as usual.

        .. seealso::

            :ref:`feature_3150`

    .. change::
        :tags: feature, orm, declarative
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
