
==============
0.9 Changelog
==============

.. changelog_imports::

    .. include:: changelog_08.rst
        :start-line: 5

    .. include:: changelog_07.rst
        :start-line: 5

.. changelog::
    :version: 0.9.5

    .. change::
        :tags: feature, orm
        :tickets: 3029

        The "primaryjoin" model has been stretched a bit further to allow
        a join condition that is strictly from a single column to itself,
        translated through some kind of SQL function or expression.  This
        is kind of experimental, but the first proof of concept is a
        "materialized path" join condition where a path string is compared
        to itself using "like".   The :meth:`.Operators.like` operator has
        also been added to the list of valid operators to use in a primaryjoin
        condition.

    .. change::
        :tags: feature, sql
        :tickets: 3028

        Liberalized the contract for :class:`.Index` a bit in that you can
        specify a :func:`.text` expression as the target; the index no longer
        needs to have a table-bound column present if the index is to be
        manually added to the table, either via inline declaration or via
        :meth:`.Table.append_constraint`.

    .. change::
        :tags: bug, mssql
        :tickets: 3025

        Revised the query used to determine the current default schema name
        to use the ``database_principal_id()`` function in conjunction with
        the ``sys.database_principals`` view so that we can determine
        the default schema independently of the type of login in progress
        (e.g., SQL Server, Windows, etc).

    .. change::
        :tags: bug, sql
        :tickets: 3024

        Fixed bug in new :meth:`.DialectKWArgs.argument_for` method where
        adding an argument for a construct not previously included for any
        special arguments would fail.

    .. change::
        :tags: bug, py3k, tests
        :tickets: 2830
        :pullreq: bitbucket:2830

        Corrected for some deprecation warnings involving the ``imp``
        module and Python 3.3 or greater, when running tests.  Pull
        request courtesy Matt Chisholm.

    .. change::
        :tags: bug, sql
        :tickets: 3020, 1068

        Fixed regression introduced in 0.9 where new "ORDER BY <labelname>"
        feature from :ticket:`1068` would not apply quoting rules to the
        label name as rendered in the ORDER BY.

    .. change::
        :tags: feature, orm
        :tickets: 3017

        Added new utility function :func:`.make_transient_to_detached` which can
        be used to manufacture objects that behave as though they were loaded
        from a session, then detached.   Attributes that aren't present
        are marked as expired, and the object can be added to a Session
        where it will act like a persistent one.

    .. change::
        :tags: bug, sql

        Restored the import for :class:`.Function` to the ``sqlalchemy.sql.expression``
        import namespace, which was removed at the beginning of 0.9.

    .. change::
        :tags: bug, orm, sql
        :tickets: 3013

        Fixes to the newly enhanced boolean coercion in :ticket:`2804` where
        the new rules for "where" and "having" woudn't take effect for the
        "whereclause" and "having" kw arguments of the :func:`.select` construct,
        which is also what :class:`.Query` uses so wasn't working in the
        ORM either.

    .. change::
        :tags: feature, sql
        :tickets: 2990

        Added new flag :paramref:`.expression.between.symmetric`, when set to True
        renders "BETWEEN SYMMETRIC".  Also added a new negation operator
        "notbetween_op", which now allows an expression like ``~col.between(x, y)``
        to render as "col NOT BETWEEN x AND y", rather than a parentheiszed NOT
        string.

.. changelog::
    :version: 0.9.4
    :released: March 28, 2014

    .. change::
        :tags: feature, orm
        :tickets: 3007

        Added new parameter :paramref:`.orm.mapper.confirm_deleted_rows`.  Defaults
        to True, indicates that a series of DELETE statements should confirm
        that the cursor rowcount matches the number of primary keys that should
        have matched;  this behavior had been taken off in most cases
        (except when version_id is used) to support the unusual edge case of
        self-referential ON DELETE CASCADE; to accommodate this, the message
        is now just a warning, not an exception, and the flag can be used
        to indicate a mapping that expects self-refererntial cascaded
        deletes of this nature.  See also :ticket:`2403` for background on the
        original change.

    .. change::
        :tags: bug, ext, automap
        :tickets: 3004

        Added support to automap for the case where a relationship should
        not be created between two classes that are in a joined inheritance
        relationship, for those foreign keys that link the subclass back to
        the superclass.

    .. change::
        :tags: bug, orm
        :tickets: 2948

        Fixed a very old behavior where the lazy load emitted for a one-to-many
        could inappropriately pull in the parent table, and also return results
        inconsistent based on what's in the parent table, when the primaryjoin
        includes some kind of discriminator against the parent table, such
        as ``and_(parent.id == child.parent_id, parent.deleted == False)``.
        While this primaryjoin doesn't make that much sense for a one-to-many,
        it is slightly more common when applied to the many-to-one side, and
        the one-to-many comes as a result of a backref.
        Loading rows from ``child`` in this case would keep ``parent.deleted == False``
        as is within the query, thereby yanking it into the FROM clause
        and doing a cartesian product.  The new behavior will now substitute
        the value of the local "parent.deleted" for that parameter as is
        appropriate.   Though typically, a real-world app probably wants to use a
        different primaryjoin for the o2m side in any case.

    .. change::
        :tags: bug, orm
        :tickets: 2965

        Improved the check for "how to join from A to B" such that when
        a table has multiple, composite foreign keys targeting a parent table,
        the :paramref:`.relationship.foreign_keys` argument will be properly
        interpreted in order to resolve the ambiguity; previously this condition
        would raise that there were multiple FK paths when in fact the
        foreign_keys argument should be establishing which one is expected.

    .. change::
        :tags: bug, mysql

        Tweaked the settings for mysql-connector-python; in Py2K, the
        "supports unicode statements" flag is now False, so that SQLAlchemy
        will encode the *SQL string* (note: *not* the parameters)
        to bytes before sending to the database.  This seems to allow
        all unicode-related tests to pass for mysql-connector, including those
        that use non-ascii table/column names, as well as some tests for the
        TEXT type using unicode under cursor.executemany().

    .. change::
        :tags: feature, engine

        Added some new event mechanics for dialect-level events; the initial
        implementation allows an event handler to redefine the specific mechanics
        by which an arbitrary dialect invokes execute() or executemany() on a
        DBAPI cursor.  The new events, at this point semi-public and experimental,
        are in support of some upcoming transaction-related extensions.

    .. change::
        :tags: feature, engine
        :tickets: 2978

        An event listener can now be associated with a :class:`.Engine`,
        after one or more :class:`.Connection` objects have been created
        (such as by an orm :class:`.Session` or via explicit connect)
        and the listener will pick up events from those connections.
        Previously, performance concerns pushed the event transfer from
        :class:`.Engine` to  :class:`.Connection` at init-time only, but
        we've inlined a bunch of conditional checks to make this possible
        without any additional function calls.

    .. change::
        :tags: bug, tests
        :tickets: 2980

        Fixed a few errant ``u''`` strings that would prevent tests from passing
        in Py3.2.  Patch courtesy Arfrever Frehtes Taifersar Arahesis.

    .. change::
        :tags: bug, engine
        :tickets: 2985

        A major improvement made to the mechanics by which the :class:`.Engine`
        recycles the connection pool when a "disconnect" condition is detected;
        instead of discarding the pool and explicitly closing out connections,
        the pool is retained and a "generational" timestamp is updated to
        reflect the current time, thereby causing all existing connections
        to be recycled when they are next checked out.   This greatly simplifies
        the recycle process, removes the need for "waking up" connect attempts
        waiting on the old pool and eliminates the race condition that many
        immediately-discarded "pool" objects could be created during the
        recycle operation.

    .. change::
        :tags: bug, oracle
        :tickets: 2987

        Added new datatype :class:`.oracle.DATE`, which is a subclass of
        :class:`.DateTime`.  As Oracle has no "datetime" type per se,
        it instead has only ``DATE``, it is appropriate here that the
        ``DATE`` type as present in the Oracle dialect be an instance of
        :class:`.DateTime`.  This issue doesn't change anything as far as
        the behavior of the type, as data conversion is handled by the
        DBAPI in any case, however the improved subclass layout will help
        the use cases of inspecting types for cross-database compatibility.
        Also removed uppercase ``DATETIME`` from the Oracle dialect as this
        type isn't functional in that context.

    .. change::
        :tags: bug, sql
        :tickets: 2988
        :pullreq: github:78

        Fixed an 0.9 regression where a :class:`.Table` that failed to
        reflect correctly wouldn't be removed from the parent
        :class:`.MetaData`, even though in an invalid state.  Pullreq
        courtesy Roman Podoliaka.

    .. change::
        :tags: bug, engine

        The :meth:`.ConnectionEvents.after_cursor_execute` event is now
        emitted for the "_cursor_execute()" method of :class:`.Connection`;
        this is the "quick" executor that is used for things like
        when a sequence is executed ahead of an INSERT statement, as well as
        for dialect startup checks like unicode returns, charset, etc.
        the :meth:`.ConnectionEvents.before_cursor_execute` event was already
        invoked here.  The "executemany" flag is now always set to False
        here, as this event always corresponds to a single execution.
        Previously the flag could be True if we were acting on behalf of
        an executemany INSERT statement.

    .. change::
        :tags: bug, orm

        Added support for the not-quite-yet-documented ``insert=True``
        flag for :func:`.event.listen` to work with mapper / instance events.

    .. change::
        :tags: feature, sql

        Added support for literal rendering of boolean values, e.g.
        "true" / "false" or "1" / "0".

    .. change::
        :tags: feature, sql

        Added a new feature :func:`.schema.conv`, the purpose of which is to
        mark a constraint name as already having had a naming convention applied.
        This token will be used by Alembic migrations as of Alembic 0.6.4
        in order to render constraints in migration scripts with names marked
        as already having been subject to a naming convention.

    .. change::
        :tags: bug, sql

        :paramref:`.MetaData.naming_convention` feature will now also
        apply to :class:`.CheckConstraint` objects that are associated
        directly with a :class:`.Column` instead of just on the
        :class:`.Table`.

    .. change::
        :tags: bug, sql
        :tickets: 2991

        Fixed bug in new :paramref:`.MetaData.naming_convention` feature
        where the name of a check constraint making use of the
        `"%(constraint_name)s"` token would get doubled up for the
        constraint generated by a boolean or enum type, and overall
        duplicate events would cause the `"%(constraint_name)s"` token
        to keep compounding itself.

    .. change::
        :tags: feature, orm

        A warning is emitted if the :meth:`.MapperEvents.before_configured`
        or :meth:`.MapperEvents.after_configured` events are applied to a
        specific mapper or mapped class, as the events are only invoked
        for the :class:`.Mapper` target at the general level.

    .. change::
        :tags: feature, orm

        Added a new keyword argument ``once=True`` to :func:`.event.listen`
        and :func:`.event.listens_for`.  This is a convenience feature which
        will wrap the given listener such that it is only invoked once.

    .. change::
        :tags: feature, oracle
        :tickets: 2911
        :pullreq: github:74

        Added a new engine option ``coerce_to_unicode=True`` to the
        cx_Oracle dialect, which restores the cx_Oracle outputtypehandler
        approach to Python unicode conversion under Python 2, which was
        removed in 0.9.2 as a result of :ticket:`2911`.  Some use cases would
        prefer that unicode coersion is unconditional for all string values,
        despite performance concerns.  Pull request courtesy
        Christoph Zwerschke.

    .. change::
        :tags: bug, pool

        Fixed small issue in :class:`.SingletonThreadPool` where the current
        connection to be returned might get inadvertently cleaned out during
        the "cleanup" process.  Patch courtesy jd23.

    .. change::
        :tags: bug, ext, py3k

        Fixed bug in association proxy where assigning an empty slice
        (e.g. ``x[:] = [...]``) would fail on Py3k.

    .. change::
        :tags: bug, general
        :tickets: 2979

        Fixed some test/feature failures occurring in Python 3.4,
        in particular the logic used to wrap "column default" callables
        wouldn't work properly for Python built-ins.

    .. change::
        :tags: feature, general

        Support has been added for pytest to run tests.   This runner
        is currently being supported in addition to nose, and will likely
        be preferred to nose going forward.   The nose plugin system used
        by SQLAlchemy has been split out so that it works under pytest as
        well.  There are no plans to drop support for nose at the moment
        and we hope that the test suite itself can continue to remain as
        agnostic of testing platform as possible.  See the file
        README.unittests.rst for updated information on running tests
        with pytest.

        The test plugin system has also been enhanced to support running
        tests against mutiple database URLs at once, by specifying the ``--db``
        and/or ``--dburi`` flags multiple times.  This does not run the entire test
        suite for each database, but instead allows test cases that are specific
        to certain backends make use of that backend as the test is run.
        When using pytest as the test runner, the system will also run
        specific test suites multiple times, once for each database, particularly
        those tests within the "dialect suite".   The plan is that the enhanced
        system will also be used by Alembic, and allow Alembic to run
        migration operation tests against multiple backends in one run, including
        third-party backends not included within Alembic itself.
        Third party dialects and extensions are also encouraged to standardize
        on SQLAlchemy's test suite as a basis; see the file README.dialects.rst
        for background on building out from SQLAlchemy's test platform.

    .. change::
        :tags: feature, orm
        :tickets: 2976

        Added a new option to :paramref:`.relationship.innerjoin` which is
        to specify the string ``"nested"``.  When set to ``"nested"`` as opposed
        to ``True``, the "chaining" of joins will parenthesize the inner join on the
        right side of an existing outer join, instead of chaining as a string
        of outer joins.   This possibly should have been the default behavior
        when 0.9 was released, as we introduced the feature of right-nested
        joins in the ORM, however we are keeping it as a non-default for now
        to avoid further surprises.

        .. seealso::

            :ref:`feature_2976`

    .. change::
        :tags: bug, ext
        :tickets: 2810

        Fixed a regression in association proxy caused by :ticket:`2810` which
        caused a user-provided "getter" to no longer receive values of ``None``
        when fetching scalar values from a target that is non-present.  The
        check for None introduced by this change is now moved into the default
        getter, so a user-provided getter will also again receive values of
        None.

    .. change::
        :tags: bug, sql
        :tickets: 2974

        Adjusted the logic which applies names to the .c collection when
        a no-name :class:`.BindParameter` is received, e.g. via :func:`.sql.literal`
        or similar; the "key" of the bind param is used as the key within
        .c. rather than the rendered name.  Since these binds have "anonymous"
        names in any case, this allows individual bound parameters to
        have their own name within a selectable if they are otherwise unlabeled.

    .. change::
        :tags: bug, sql
        :tickets: 2974

        Some changes to how the :attr:`.FromClause.c` collection behaves
        when presented with duplicate columns.  The behavior of emitting a
        warning and replacing the old column with the same name still
        remains to some degree; the replacement in particular is to maintain
        backwards compatibility.  However, the replaced column still remains
        associated with the ``c`` collection now in a collection ``._all_columns``,
        which is used by constructs such as aliases and unions, to deal with
        the set of columns in ``c`` more towards what is actually in the
        list of columns rather than the unique set of key names.  This helps
        with situations where SELECT statements with same-named columns
        are used in unions and such, so that the union can match the columns
        up positionally and also there's some chance of :meth:`.FromClause.corresponding_column`
        still being usable here (it can now return a column that is only
        in selectable.c._all_columns and not otherwise named).
        The new collection is underscored as we still need to decide where this
        list might end up.   Theoretically it
        would become the result of iter(selectable.c), however this would mean
        that the length of the iteration would no longer match the length of
        keys(), and that behavior needs to be checked out.

    .. change::
        :tags: bug, sql

        Fixed issue in new :meth:`.TextClause.columns` method where the ordering
        of columns given positionally would not be preserved.   This could
        have potential impact in positional situations such as applying the
        resulting :class:`.TextAsFrom` object to a union.

    .. change::
        :tags: feature, sql
        :tickets: 2962, 2866

        The new dialect-level keyword argument system for schema-level
        constructs has been enhanced in order to assist with existing
        schemes that rely upon addition of ad-hoc keyword arguments to
        constructs.

        E.g., a construct such as :class:`.Index` will again accept
        ad-hoc keyword arguments within the :attr:`.Index.kwargs` collection,
        after construction::

            idx = Index('a', 'b')
            idx.kwargs['mysql_someargument'] = True

        To suit the use case of allowing custom arguments at construction time,
        the :meth:`.DialectKWArgs.argument_for` method now allows this registration::

            Index.argument_for('mysql', 'someargument', False)

            idx = Index('a', 'b', mysql_someargument=True)

        .. seealso::

            :meth:`.DialectKWArgs.argument_for`

    .. change::
        :tags: bug, orm, engine
        :tickets: 2973

        Fixed bug where events set to listen at the class
        level (e.g. on the :class:`.Mapper` or :class:`.ClassManager`
        level, as opposed to on an individual mapped class, and also on
        :class:`.Connection`) that also made use of internal argument conversion
        (which is most within those categories) would fail to be removable.

    .. change::
        :tags: bug, orm

        Fixed regression from 0.8 where using an option like
        :func:`.orm.lazyload` with the "wildcard" expression, e.g. ``"*"``,
        would raise an assertion error in the case where the query didn't
        contain any actual entities.  This assertion is meant for other cases
        and was catching this one inadvertently.

    .. change::
        :tags: bug, examples

        Fixed bug in the versioned_history example where column-level INSERT
        defaults would prevent history values of NULL from being written.

    .. change::
        :tags: orm, bug, sqlite
        :tickets: 2969

        More fixes to SQLite "join rewriting"; the fix from :ticket:`2967`
        implemented right before the release of 0.9.3 affected the case where
        a UNION contained nested joins in it.   "Join rewriting" is a feature
        with a wide range of possibilities and is the first intricate
        "SQL rewriting" feature we've introduced in years, so we're sort of
        going through a lot of iterations with it (not unlike eager loading
        back in the 0.2/0.3 series, polymorphic loading in 0.4/0.5). We should
        be there soon so thanks for bearing with us :).


.. changelog::
    :version: 0.9.3
    :released: February 19, 2014

    .. change::
        :tags: orm, bug, sqlite
        :tickets: 2967

        Fixed bug in SQLite "join rewriting" where usage of an exists() construct
        would fail to be rewritten properly, such as when the exists is
        mapped to a column_property in an intricate nested-join scenario.
        Also fixed a somewhat related issue where join rewriting would fail
        on the columns clause of the SELECT statement if the targets were
        aliased tables, as opposed to individual aliased columns.

    .. change::
        :tags: sqlite, bug

        The SQLite dialect will now skip unsupported arguments when reflecting
        types; such as if it encounters a string like ``INTEGER(5)``, the
        :class:`.INTEGER` type will be instantiated without the "5" being included,
        based on detecting a ``TypeError`` on the first attempt.

    .. change::
        :tags: sqlite, bug
        :pullreq: github:65

        Support has been added to SQLite type reflection to fully support
        the "type affinity" contract specified at http://www.sqlite.org/datatype3.html.
        In this scheme, keywords like ``INT``, ``CHAR``, ``BLOB`` or
        ``REAL`` located in the type name generically associate the type with
        one of five affinities.  Pull request courtesy Erich Blume.

        .. seealso::

            :ref:`sqlite_type_reflection`

    .. change::
        :tags: postgresql, feature
        :pullreq: github:64

        Added the :attr:`.TypeEngine.python_type` convenience accessor onto the
        :class:`.postgresql.ARRAY` type.  Pull request courtesy Alexey Terentev.

    .. change::
        :tags: examples, feature
        :pullreq: github:41

        Added optional "changed" column to the versioned rows example, as well
        as support for when the versioned :class:`.Table` has an explicit
        :paramref:`~.Table.schema` argument.   Pull request
        courtesy jplaverdure.

    .. change::
        :tags: bug, postgresql
        :tickets: 2946

        Added server version detection to the newly added dialect startup
        query for  "show standard_conforming_strings"; as this variable was
        added as of PG 8.2, we skip the query for PG versions who report a
        version string earlier than that.

    .. change::
        :tags: bug, orm, declarative
        :tickets: 2950

        Fixed bug where :class:`.AbstractConcreteBase` would fail to be
        fully usable within declarative relationship configuration, as its
        string classname would not be available in the registry of classnames
        at mapper configuration time.   The class now explicitly adds itself
        to the class regsitry, and additionally both :class:`.AbstractConcreteBase`
        as well as :class:`.ConcreteBase` set themselves up *before* mappers
        are configured within the :func:`.configure_mappers` setup, using
        the new :meth:`.MapperEvents.before_configured` event.

    .. change::
        :tags: feature, orm

        Added new :meth:`.MapperEvents.before_configured` event which allows
        an event at the start of :func:`.configure_mappers`, as well
        as ``__declare_first__()`` hook within declarative to complement
        ``__declare_last__()``.

    .. change::
        :tags: bug, mysql, cymysql
        :tickets: 2934
        :pullreq: github:69

        Fixed bug in cymysql dialect where a version string such as
        ``'33a-MariaDB'`` would fail to parse properly.  Pull request
        courtesy Matt Schmidt.

    .. change::
        :tags: bug, orm
        :tickets: 2949

        Fixed an 0.9 regression where ORM instance or mapper events applied
        to a base class such as a declarative base with the propagate=True
        flag would fail to apply to existing mapped classes which also
        used inheritance due to an assertion.  Addtionally, repaired an
        attribute error which could occur during removal of such an event,
        depending on how it was first assigned.

    .. change::
        :tags: bug, ext

        Fixed bug where the :class:`.AutomapBase` class of the
        new automap extension would fail if classes
        were pre-arranged in single or potentially joined inheritance patterns.
        The repaired joined inheritance issue could also potentially apply when
        using :class:`.DeferredReflection` as well.


    .. change::
        :tags: bug, sql
        :pullreq: github:67

        Fixed regression in new "naming convention" feature where conventions
        would fail if the referred table in a foreign key contained a schema
        name.  Pull request courtesy Thomas Farvour.

    .. change::
        :tags: bug, sql

        Fixed bug where so-called "literal render" of :func:`.bindparam`
        constructs would fail if the bind were constructed with a callable,
        rather than a direct value.  This prevented ORM expressions
        from being rendered with the "literal_binds" compiler flag.

    .. change::
        :tags: bug, orm
        :tickets: 2935

        Improved the initialization logic of composite attributes such that
        calling ``MyClass.attribute`` will not require that the configure
        mappers step has occurred, e.g. it will just work without throwing
        any error.

    .. change::
        :tags: bug, orm
        :tickets: 2932

        More issues with [ticket:2932] first resolved in 0.9.2 where
        using a column key of the form ``<tablename>_<columnname>``
        matching that of an aliased column in the text would still not
        match at the ORM level, which is ultimately due to a core
        column-matching issue.  Additional rules have been added so that the
        column ``_label`` is taken into account when working with a
        :class:`.TextAsFrom` construct or with literal columns.

.. changelog::
    :version: 0.9.2
    :released: February 2, 2014

    .. change::
        :tags: bug, examples

        Added a tweak to the "history_meta" example where the check for
        "history" on a relationship-bound attribute will now no longer emit
        any SQL if the relationship is unloaded.

    .. change::
        :tags: feature, sql

        Added :paramref:`.MetaData.reflect.**dialect_kwargs`
        to support dialect-level reflection options for all :class:`.Table`
        objects reflected.

    .. change::
        :tags: feature, postgresql
        :tickets: 2922

        Added a new dialect-level argument ``postgresql_ignore_search_path``;
        this argument is accepted by both the :class:`.Table` constructor
        as well as by the :meth:`.MetaData.reflect` method.  When in use
        against Postgresql, a foreign-key referenced table which specifies
        a remote schema name will retain that schema name even if the name
        is present in the ``search_path``; the default behavior since 0.7.3
        has been that schemas present in ``search_path`` would not be copied
        to reflected :class:`.ForeignKey` objects.  The documentation has been
        updated to describe in detail the behavior of the ``pg_get_constraintdef()``
        function and how the ``postgresql_ignore_search_path`` feature essentially
        determines if we will honor the schema qualification reported by
        this function or not.

        .. seealso::

            :ref:`postgresql_schema_reflection`

    .. change::
        :tags: bug, sql
        :tickets: 2913

        The behavior of :meth:`.Table.tometadata` has been adjusted such that
        the schema target of a :class:`.ForeignKey` will not be changed unless
        that schema matches that of the parent table.  That is, if
        a table "schema_a.user" has a foreign key to "schema_b.order.id",
        the "schema_b" target will be maintained whether or not the
        "schema" argument is passed to :meth:`.Table.tometadata`.  However
        if a table "schema_a.user" refers to "schema_a.order.id", the presence
        of "schema_a" will be updated on both the parent and referred tables.
        This is a behavioral change hence isn't likely to be backported to
        0.8; it is assumed that the previous behavior is pretty buggy
        however and that it's unlikely anyone was relying upon it.

        Additionally, a new parameter has been added
        :paramref:`.Table.tometadata.referred_schema_fn`.  This refers to a
        callable function which will be used to determine the new referred
        schema for any :class:`.ForeignKeyConstraint` encountered in the
        tometadata operation.  This callable can be used to revert to the
        previous behavior or to customize how referred schemas are treated
        on a per-constraint basis.

    .. change::
        :tags: bug, orm
        :tickets: 2932

        Fixed bug in new :class:`.TextAsFrom` construct where :class:`.Column`-
        oriented row lookups were not matching up to the ad-hoc :class:`.ColumnClause`
        objects that :class:`.TextAsFrom` generates, thereby making it not
        usable as a target in :meth:`.Query.from_statement`.  Also fixed
        :meth:`.Query.from_statement` mechanics to not mistake a :class:`.TextAsFrom`
        for a :class:`.Select` construct.  This bug is also an 0.9 regression
        as the :meth:`.Text.columns` method is called to accommodate the
        :paramref:`.text.typemap` argument.

    .. change::
        :tags: feature, sql
        :tickets: 2923

        Added a new feature which allows automated naming conventions to be
        applied to :class:`.Constraint` and :class:`.Index` objects.  Based
        on a recipe in the wiki, the new feature uses schema-events to set up
        names as various schema objects are associated with each other.  The
        events then expose a configuration system through a new argument
        :paramref:`.MetaData.naming_convention`.  This system allows production
        of both simple and custom naming schemes for constraints and indexes
        on a per-:class:`.MetaData` basis.

        .. seealso::

            :ref:`constraint_naming_conventions`

    .. change::
        :tags: bug, orm
        :tickets: 2921

        Added a new directive used within the scope of an attribute "set" operation
        to disable autoflush, in the case that the attribute needs to lazy-load
        the "old" value, as in when replacing one-to-one values or some
        kinds of many-to-one.  A flush at this point otherwise occurs
        at the point that the attribute is None and can cause NULL violations.

    .. change::
        :tags: feature, orm

        Added a new parameter :paramref:`.Operators.op.is_comparison`.  This
        flag allows a custom op from :meth:`.Operators.op` to be considered
        as a "comparison" operator, thus usable for custom
        :paramref:`.relationship.primaryjoin` conditions.

        .. seealso::

            :ref:`relationship_custom_operator`


    .. change::
        :tags: bug, sqlite

        Fixed bug whereby SQLite compiler failed to propagate compiler arguments
        such as "literal binds" into a CAST expression.

    .. change::
        :tags: bug, sql

        Fixed bug whereby binary type would fail in some cases
        if used with a "test" dialect, such as a DefaultDialect or other
        dialect with no DBAPI.

    .. change::
        :tags: bug, sql, py3k

        Fixed bug where "literal binds" wouldn't work with a bound parameter
        that's a binary type.  A similar, but different, issue is fixed
        in 0.8.

    .. change::
        :tags: bug, sql
        :tickets: 2927

        Fixed regression whereby the "annotation" system used by the ORM was leaking
        into the names used by standard functions in :mod:`sqlalchemy.sql.functions`,
        such as ``func.coalesce()`` and ``func.max()``.  Using these functions
        in ORM attributes and thus producing annotated versions of them could
        corrupt the actual function name rendered in the SQL.

    .. change::
        :tags: bug, sql
        :tickets: 2924, 2848

        Fixed 0.9 regression where the new sortable support for :class:`.RowProxy`
        would lead to ``TypeError`` when compared to non-tuple types as it attempted
        to apply tuple() to the "other" object unconditionally.  The
        full range of Python comparison operators have now been implemented on
        :class:`.RowProxy`, using an approach that guarantees a comparison
        system that is equivalent to that of a tuple, and the "other" object
        is only coerced if it's an instance of RowProxy.

    .. change::
        :tags: bug, orm
        :tickets: 2918

        Fixed an 0.9 regression where the automatic aliasing applied by
        :class:`.Query` and in other situations where selects or joins
        were aliased (such as joined table inheritance) could fail if a
        user-defined :class:`.Column` subclass were used in the expression.
        In this case, the subclass would fail to propagate ORM-specific
        "annotations" along needed by the adaptation.  The "expression
        annotations" system has been corrected to account for this case.

    .. change::
        :tags: feature, orm

        Support is improved for supplying a :func:`.join` construct as the
        target of :paramref:`.relationship.secondary` for the purposes
        of creating very complex :func:`.relationship` join conditions.
        The change includes adjustments to query joining, joined eager loading
        to not render a SELECT subquery, changes to lazy loading such that
        the "secondary" target is properly included in the SELECT, and
        changes to declarative to better support specification of a
        join() object with classes as targets.

        The new use case is somewhat experimental, but a new documentation section
        has been added.

        .. seealso::

            :ref:`composite_secondary_join`

    .. change::
        :tags: bug, mysql, sql
        :tickets: 2917

        Added new test coverage for so-called "down adaptions" of SQL types,
        where a more specific type is adapted to a more generic one - this
        use case is needed by some third party tools such as ``sqlacodegen``.
        The specific cases that needed repair within this test suite were that
        of :class:`.mysql.ENUM` being downcast into a :class:`.types.Enum`,
        and that of SQLite date types being cast into generic date types.
        The ``adapt()`` method needed to become more specific here to counteract
        the removal of a "catch all" ``**kwargs`` collection on the base
        :class:`.TypeEngine` class that was removed in 0.9.

    .. change::
        :tags: feature, sql
        :tickets: 2910

        Options can now be specified on a :class:`.PrimaryKeyConstraint` object
        independently of the specification of columns in the table with
        the ``primary_key=True`` flag; use a :class:`.PrimaryKeyConstraint`
        object with no columns in it to achieve this result.

        Previously, an explicit :class:`.PrimaryKeyConstraint` would have the
        effect of those columns marked as ``primary_key=True`` being ignored;
        since this is no longer the case, the :class:`.PrimaryKeyConstraint`
        will now assert that either one style or the other is used to specify
        the columns, or if both are present, that the column lists match
        exactly.  If an inconsistent set of columns in the
        :class:`.PrimaryKeyConstraint`
        and within the :class:`.Table` marked as ``primary_key=True`` are
        present, a warning is emitted, and the list of columns is taken
        only from the :class:`.PrimaryKeyConstraint` alone as was the case
        in previous releases.



        .. seealso::

            :class:`.PrimaryKeyConstraint`

    .. change::
        :tags: feature, sql
        :tickets: 2866

        The system by which schema constructs and certain SQL constructs
        accept dialect-specific keyword arguments has been enhanced.  This
        system includes commonly the :class:`.Table` and :class:`.Index` constructs,
        which accept a wide variety of dialect-specific arguments such as
        ``mysql_engine`` and ``postgresql_where``, as well as the constructs
        :class:`.PrimaryKeyConstraint`, :class:`.UniqueConstraint`,
        :class:`.Update`, :class:`.Insert` and :class:`.Delete`, and also
        newly added kwarg capability to :class:`.ForeignKeyConstraint`
        and :class:`.ForeignKey`.  The change is that participating dialects
        can now specify acceptable argument lists for these constructs, allowing
        an argument error to be raised if an invalid keyword is specified for
        a particular dialect.  If the dialect portion of the keyword is unrecognized,
        a warning is emitted only; while the system will actually make use
        of setuptools entrypoints in order to locate non-local dialects,
        the use case where certain dialect-specific arguments are used
        in an environment where that third-party dialect is uninstalled remains
        supported.  Dialects also have to explicitly opt-in to this system,
        so that external dialects which aren't making use of this system
        will remain unaffected.

    .. change::
        :tags: bug, sql
        :pullreq: bitbucket:11

        A :class:`.UniqueConstraint` created inline with a :class:`.Table`
        that has no columns within it will be skipped.  Pullreq courtesy
        Derek Harland.

    .. change::
        :tags: feature, mssql
        :pullreq: bitbucket:11

        Added an option ``mssql_clustered`` to the :class:`.UniqueConstraint`
        and :class:`.PrimaryKeyConstraint` constructs; on SQL Server, this adds
        the ``CLUSTERED`` keyword to the constraint construct within DDL.
        Pullreq courtesy Derek Harland.

    .. change::
        :tags: bug, sql, orm
        :tickets: 2912

        Fixed the multiple-table "UPDATE..FROM" construct, only usable on
        MySQL, to correctly render the SET clause among multiple columns
        with the same name across tables.  This also changes the name used for
        the bound parameter in the SET clause to "<tablename>_<colname>" for
        the non-primary table only; as this parameter is typically specified
        using the :class:`.Column` object directly this should not have an
        impact on applications.   The fix takes effect for both
        :meth:`.Table.update` as well as :meth:`.Query.update` in the ORM.

    .. change::
        :tags: bug, oracle
        :tickets: 2911

        It's been observed that the usage of a cx_Oracle "outputtypehandler"
        in Python 2.xx in order to coerce string values to Unicode is inordinately
        expensive; even though cx_Oracle is written in C, when you pass the
        Python ``unicode`` primitive to cursor.var() and associate with an output
        handler, the library counts every conversion as a Python function call
        with all the requisite overhead being recorded; this *despite* the fact
        when running in Python 3, all strings are also unconditionally coerced
        to unicode but it does *not* incur this overhead,
        meaning that cx_Oracle is failing to use performant techniques in Py2K.
        As SQLAlchemy cannot easily select for this style of type handler on a
        per-column basis, the handler was assembled unconditionally thereby
        adding the overhead to all string access.

        So this logic has been replaced with SQLAlchemy's own unicode
        conversion system, which now
        only takes effect in Py2K for columns that are requested as unicode.
        When C extensions are used, SQLAlchemy's system appears to be 2-3x faster than
        cx_Oracle's.  Additionally, SQLAlchemy's unicode conversion has been
        enhanced such that when the "conditional" converter is required
        (now needed for the Oracle backend), the check for "already unicode" is now
        performed in C and no longer introduces significant overhead.

        This change has two impacts on the cx_Oracle backend.  One is that
        string values in Py2K which aren't specifically requested with the
        Unicode type or convert_unicode=True will now come back as ``str``,
        not ``unicode`` - this behavior is similar to a backend such as
        MySQL.  Additionally, when unicode values are requested with the cx_Oracle
        backend, if the C extensions are *not* used, there is now an additional
        overhead of an isinstance() check per column.  This tradeoff has been
        made as it can be worked around and no longer places a performance burden
        on the likely majority of Oracle result columns that are non-unicode
        strings.

    .. change::
        :tags: bug, orm
        :tickets: 2908

        Fixed a bug involving the new flattened JOIN structures which
        are used with :func:`.joinedload()` (thereby causing a regression
        in joined eager loading) as well as :func:`.aliased`
        in conjunction with the ``flat=True`` flag and joined-table inheritance;
        basically multiple joins across a "parent JOIN sub" entity using different
        paths to get to a target class wouldn't form the correct ON conditions.
        An adjustment / simplification made in the mechanics of figuring
        out the "left side" of the join in the case of an aliased, joined-inh
        class repairs the issue.

    .. change::
        :tags: bug, mysql

        The MySQL CAST compilation now takes into account aspects of a string
        type such as "charset" and "collation".  While MySQL wants all character-
        based CAST calls to use the CHAR type, we now create a real CHAR
        object at CAST time and copy over all the parameters it has, so that
        an expression like ``cast(x, mysql.TEXT(charset='utf8'))`` will
        render ``CAST(t.col AS CHAR CHARACTER SET utf8)``.

    .. change::
        :tags: bug, mysql
        :tickets: 2906

        Added new "unicode returns" detection to the MySQL dialect and
        to the default dialect system overall, such that any dialect
        can add extra "tests" to the on-first-connect "does this DBAPI
        return unicode directly?" detection. In this case, we are
        adding a check specifically against the "utf8" encoding with
        an explicit "utf8_bin" collation type (after checking that
        this collation is available) to test for some buggy unicode
        behavior observed with MySQLdb version 1.2.3.  While MySQLdb
        has resolved this issue as of 1.2.4, the check here should
        guard against regressions.  The change also allows the "unicode"
        checks to log in the engine logs, which was not previously
        the case.

    .. change::
        :tags: bug, mysql, pool, engine
        :tickets: 2907

        :class:`.Connection` now associates a new
        :class:`.RootTransaction` or :class:`.TwoPhaseTransaction`
        with its immediate :class:`._ConnectionFairy` as a "reset handler"
        for the span of that transaction, which takes over the task
        of calling commit() or rollback() for the "reset on return" behavior
        of :class:`.Pool` if the transaction was not otherwise completed.
        This resolves the issue that a picky transaction
        like that of MySQL two-phase will be
        properly closed out when the connection is closed without an
        explicit rollback or commit (e.g. no longer raises "XAER_RMFAIL"
        in this case - note this only shows up in logging as the exception
        is not propagated within pool reset).
        This issue would arise e.g. when using an orm
        :class:`.Session` with ``twophase`` set, and then
        :meth:`.Session.close` is called without an explicit rollback or
        commit.   The change also has the effect that you will now see
        an explicit "ROLLBACK" in the logs when using a :class:`.Session`
        object in non-autocommit mode regardless of how that session was
        discarded.  Thanks to Jeff Dairiki and Laurence Rowe for isolating
        the issue here.

    .. change::
        :tags: feature, pool, engine

        Added a new pool event :meth:`.PoolEvents.invalidate`.  Called when
        a DBAPI connection is to be marked as "invaldated" and discarded
        from the pool.

    .. change::
        :tags: bug, pool

        The argument names for the :meth:`.PoolEvents.reset` event have been
        renamed to ``dbapi_connection`` and ``connection_record`` in order
        to maintain consistency with all the other pool events.  It is expected
        that any existing listeners for this relatively new and
        seldom-used event are using positional style to receive arguments in
        any case.

    .. change::
        :tags: bug, py3k, cextensions
        :pullreq: github:55

        Fixed an issue where the C extensions in Py3K are using the wrong API
        to specify the top-level module function, which breaks
        in Python 3.4b2.  Py3.4b2 changes PyMODINIT_FUNC to return
        "void" instead of "PyObject *", so we now make sure to use
        "PyMODINIT_FUNC" instead of "PyObject *" directly.  Pull request
        courtesy cgohlke.

    .. change::
        :tags: bug, schema
        :pullreq: github:57

        Restored :class:`sqlalchemy.schema.SchemaVisitor` to the ``.schema``
        module.  Pullreq courtesy Sean Dague.

.. changelog::
    :version: 0.9.1
    :released: January 5, 2014

    .. change::
        :tags: bug, orm, events
        :tickets: 2905

        Fixed regression where using a ``functools.partial()`` with the event
        system would cause a recursion overflow due to usage of inspect.getargspec()
        on it in order to detect a legacy calling signature for certain events,
        and apparently there's no way to do this with a partial object.  Instead
        we skip the legacy check and assume the modern style; the check itself
        now only occurs for the SessionEvents.after_bulk_update and
        SessionEvents.after_bulk_delete events.  Those two events will require
        the new signature style if assigned to a "partial" event listener.

    .. change::
        :tags: feature, orm, extensions

        A new, **experimental** extension :mod:`sqlalchemy.ext.automap` is added.
        This extension expands upon the functionality of Declarative as well as
        the :class:`.DeferredReflection` class to produce a base class which
        automatically generates mapped classes *and relationships* based on
        table metadata.

        .. seealso::

            :ref:`feature_automap`

            :ref:`automap_toplevel`

    .. change::
        :tags: feature, sql

        Conjunctions like :func:`.and_` and :func:`.or_` can now accept
        Python generators as a single argument, e.g.::

            and_(x == y for x, y in tuples)

        The logic here looks for a single argument ``*args`` where the first
        element is an instance of ``types.GeneratorType``.

    .. change::
        :tags: feature, schema

        The :paramref:`.Table.extend_existing` and :paramref:`.Table.autoload_replace`
        parameters are now available on the :meth:`.MetaData.reflect`
        method.

    .. change::
        :tags: bug, orm, declarative

        Fixed an extremely unlikely memory issue where when using
        :class:`.DeferredReflection`
        to define classes pending for reflection, if some subset of those
        classes were discarded before the :meth:`.DeferredReflection.prepare`
        method were called to reflect and map the class, a strong reference
        to the class would remain held within the declarative internals.
        This internal collection of "classes to map" now uses weak
        references against the classes themselves.

    .. change::
        :tags: bug, orm
        :pullreq: bitbucket:9

        Fixed bug where using new :attr:`.Session.info` attribute would fail
        if the ``.info`` argument were only passed to the :class:`.sessionmaker`
        creation call but not to the object itself.  Courtesy Robin Schoonover.

    .. change::
        :tags: bug, orm
        :tickets: 2901

        Fixed regression where we don't check the given name against the
        correct string class when setting up a backref based on a name,
        therefore causing the error "too many values to unpack".  This was
        related to the Py3k conversion.

    .. change::
        :tags: bug, orm, declarative
        :tickets: 2900

        A quasi-regression where apparently in 0.8 you can set a class-level
        attribute on declarative to simply refer directly to an :class:`.InstrumentedAttribute`
        on a superclass or on the class itself, and it
        acts more or less like a synonym; in 0.9, this fails to set up enough
        bookkeeping to keep up with the more liberalized backref logic
        from :ticket:`2789`.  Even though this use case was never directly
        considered, it is now detected by declarative at the "setattr()" level
        as well as when setting up a subclass, and the mirrored/renamed attribute
        is now set up as a :func:`.synonym` instead.

    .. change::
        :tags: bug, orm
        :tickets: 2903

        Fixed regression where we apparently still create an implicit
        alias when saying query(B).join(B.cs), where "C" is a joined inh
        class; however, this implicit alias was created only considering
        the immediate left side, and not a longer chain of joins along different
        joined-inh subclasses of the same base.   As long as we're still
        implicitly aliasing in this case, the behavior is dialed back a bit
        so that it will alias the right side in a wider variety of cases.

.. changelog::
    :version: 0.9.0
    :released: December 30, 2013

    .. change::
        :tags: bug, orm, declarative
        :tickets: 2828

        Declarative does an extra check to detect if the same
        :class:`.Column` is mapped multiple times under different properties
        (which typically should be a :func:`.synonym` instead) or if two
        or more :class:`.Column` objects are given the same name, raising
        a warning if this condition is detected.

    .. change::
        :tags: bug, firebird
        :tickets: 2898

        Changed the queries used by Firebird to list table and view names
        to query from the ``rdb$relations`` view instead of the
        ``rdb$relation_fields`` and ``rdb$view_relations`` views.
        Variants of both the old and new queries are mentioned on many
        FAQ and blogs, however the new queries are taken straight from
        the "Firebird FAQ" which appears to be the most official source
        of info.

    .. change::
        :tags: bug, mysql
        :tickets: 2893

        Improvements to the system by which SQL types generate within
        ``__repr__()``, particularly with regards to the MySQL integer/numeric/
        character types which feature a wide variety of keyword arguments.
        The ``__repr__()`` is important for use with Alembic autogenerate
        for when Python code is rendered in a migration script.

    .. change::
        :tags: feature, postgresql
        :tickets: 2581
        :pullreq: github:50

        Support for Postgresql JSON has been added, using the new
        :class:`.JSON` type.   Huge thanks to Nathan Rice for
        implementing and testing this.

    .. change::
        :tags: bug, sql

        The :func:`.cast` function, when given a plain literal value,
        will now apply the given type to the given literal value on the
        bind parameter side according to the type given to the cast,
        in the same manner as that of the :func:`.type_coerce` function.
        However unlike :func:`.type_coerce`, this only takes effect if a
        non-clauseelement value is passed to :func:`.cast`; an existing typed
        construct will retain its type.

    .. change::
        :tags: bug, postgresql

        Now using psycopg2 UNICODEARRAY extension for handling unicode arrays
        with psycopg2 + normal "native unicode" mode, in the same way the
        UNICODE extension is used.

    .. change::
        :tags: bug, sql
        :tickets: 2883

        The :class:`.ForeignKey` class more aggressively checks the given
        column argument.   If not a string, it checks that the object is
        at least a :class:`.ColumnClause`, or an object that resolves to one,
        and that the ``.table`` attribute, if present, refers to a
        :class:`.TableClause` or subclass, and not something like an
        :class:`.Alias`.  Otherwise, a :class:`.ArgumentError` is raised.


    .. change::
        :tags: feature, orm

        The :class:`.exc.StatementError` or DBAPI-related subclass
        now can accommodate additional information about the "reason" for
        the exception; the :class:`.Session` now adds some detail to it
        when the exception occurs within an autoflush.  This approach
        is taken as opposed to combining :class:`.FlushError` with
        a Python 3 style "chained exception" approach so as to maintain
        compatibility both with Py2K code as well as code that already
        catches ``IntegrityError`` or similar.

    .. change::
        :tags: feature, postgresql
        :pullreq: bitbucket:8

        Added support for Postgresql TSVECTOR via the
        :class:`.postgresql.TSVECTOR` type.  Pull request courtesy
        Noufal Ibrahim.

    .. change::
        :tags: feature, engine
        :tickets: 2875

        The :func:`.engine_from_config` function has been improved so that
        we will be able to parse dialect-specific arguments from string
        configuration dictionaries.  Dialect classes can now provide their
        own list of parameter types and string-conversion routines.
        The feature is not yet used by the built-in dialects, however.

    .. change::
        :tags: bug, sql
        :tickets: 2879

        The precedence rules for the :meth:`.ColumnOperators.collate` operator
        have been modified, such that the COLLATE operator is now of lower
        precedence than the comparison operators.  This has the effect that
        a COLLATE applied to a comparison will not render parenthesis
        around the comparison, which is not parsed by backends such as
        MSSQL.  The change is backwards incompatible for those setups that
        were working around the issue by applying :meth:`.Operators.collate`
        to an individual element of the comparison expression,
        rather than the comparison expression as a whole.

        .. seealso::

            :ref:`migration_2879`

    .. change::
        :tags: bug, orm, declarative
        :tickets: 2865

        The :class:`.DeferredReflection` class has been enhanced to provide
        automatic reflection support for the "secondary" table referred
        to by a :func:`.relationship`.   "secondary", when specified
        either as a string table name, or as a :class:`.Table` object with
        only a name and :class:`.MetaData` object will also be included
        in the reflection process when :meth:`.DeferredReflection.prepare`
        is called.

    .. change::
        :tags: feature, orm, backrefs
        :tickets: 1535

        Added new argument ``include_backrefs=True`` to the
        :func:`.validates` function; when set to False, a validation event
        will not be triggered if the event was initated as a backref to
        an attribute operation from the other side.

        .. seealso::

            :ref:`feature_1535`

    .. change::
        :tags: bug, orm, collections, py3k
        :pullreq: github:40

        Added support for the Python 3 method ``list.clear()`` within
        the ORM collection instrumentation system; pull request
        courtesy Eduardo Schettino.

    .. change::
        :tags: bug, postgresql
        :tickets: 2878

        Fixed bug where values within an ENUM weren't escaped for single
        quote signs.   Note that this is backwards-incompatible for existing
        workarounds that manually escape the single quotes.

        .. seealso::

            :ref:`migration_2878`

    .. change::
        :tags: bug, orm, declarative

        Fixed bug where in Py2K a unicode literal would not be accepted
        as the string name of a class or other argument within
        declarative using :func:`.relationship`.

    .. change::
        :tags: feature, sql
        :tickets: 2877, 2882

        New improvements to the :func:`.text` construct, including
        more flexible ways to set up bound parameters and return types;
        in particular, a :func:`.text` can now be turned into a full
        FROM-object, embeddable in other statements as an alias or CTE
        using the new method :meth:`.TextClause.columns`.   The :func:`.text`
        construct can also render "inline" bound parameters when the construct
        is compiled in a "literal bound" context.

        .. seealso::

            :ref:`feature_2877`

    .. change::
        :tags: feature, sql
        :pullreq: github:42

        A new API for specifying the ``FOR UPDATE`` clause of a ``SELECT``
        is added with the new :meth:`.GenerativeSelect.with_for_update` method.
        This method supports a more straightforward system of setting
        dialect-specific options compared to the ``for_update`` keyword
        argument of :func:`.select`, and also includes support for the
        SQL standard ``FOR UPDATE OF`` clause.   The ORM also includes
        a new corresponding method :meth:`.Query.with_for_update`.
        Pull request courtesy Mario Lassnig.

        .. seealso::

            :ref:`feature_github_42`

    .. change::
        :tags: feature, orm
        :pullreq: github:42

        A new API for specifying the ``FOR UPDATE`` clause of a ``SELECT``
        is added with the new :meth:`.Query.with_for_update` method,
        to complement the new :meth:`.GenerativeSelect.with_for_update` method.
        Pull request courtesy Mario Lassnig.

        .. seealso::

            :ref:`feature_github_42`

    .. change::
        :tags: bug, engine
        :tickets: 2873

        The :func:`.create_engine` routine and the related
        :func:`.make_url` function no longer considers the ``+`` sign
        to be a space within the password field.  The parsing has been
        adjuted to match RFC 1738 exactly, in that both ``username``
        and ``password`` expect only ``:``, ``@``, and ``/`` to be
        encoded.

        .. seealso::

            :ref:`migration_2873`


    .. change::
        :tags: bug, orm
        :tickets: 2872

        Some refinements to the :class:`.AliasedClass` construct with regards
        to descriptors, like hybrids, synonyms, composites, user-defined
        descriptors, etc.  The attribute
        adaptation which goes on has been made more robust, such that if a descriptor
        returns another instrumented attribute, rather than a compound SQL
        expression element, the operation will still proceed.
        Addtionally, the "adapted" operator will retain its class; previously,
        a change in class from ``InstrumentedAttribute`` to ``QueryableAttribute``
        (a superclass) would interact with Python's operator system such that
        an expression like ``aliased(MyClass.x) > MyClass.x`` would reverse itself
        to read ``myclass.x < myclass_1.x``.   The adapted attribute will also
        refer to the new :class:`.AliasedClass` as its parent which was not
        always the case before.

    .. change::
        :tags: feature, sql
        :tickets: 2867

        The precision used when coercing a returned floating point value to
        Python ``Decimal`` via string is now configurable.  The
        flag ``decimal_return_scale`` is now supported by all :class:`.Numeric`
        and :class:`.Float` types, which will ensure this many digits are taken
        from the native floating point value when it is converted to string.
        If not present, the type will make use of the value of ``.scale``, if
        the type supports this setting and it is non-None.  Otherwise the original
        default length of 10 is used.

        .. seealso::

            :ref:`feature_2867`

    .. change::
        :tags: bug, schema
        :tickets: 2868

        Fixed a regression caused by :ticket:`2812` where the repr() for
        table and column names would fail if the name contained non-ascii
        characters.

    .. change::
        :tags: bug, engine
        :tickets: 2848

        The :class:`.RowProxy` object is now sortable in Python as a regular
        tuple is; this is accomplished via ensuring tuple() conversion on
        both sides within the ``__eq__()`` method as well as
        the addition of a ``__lt__()`` method.

        .. seealso::

            :ref:`migration_2848`

    .. change::
        :tags: bug, orm
        :tickets: 2833

        The ``viewonly`` flag on :func:`.relationship` will now prevent
        attribute history from being written on behalf of the target attribute.
        This has the effect of the object not being written to the
        Session.dirty list if it is mutated.  Previously, the object would
        be present in Session.dirty, but no change would take place on behalf
        of the modified attribute during flush.   The attribute still emits
        events such as backref events and user-defined events and will still
        receive mutations from backrefs.

        .. seealso::

            :ref:`migration_2833`

    .. change::
        :tags: bug, orm

        Added support for new :attr:`.Session.info` attribute to
        :class:`.scoped_session`.

    .. change::
        :tags: removed

        The "informix" and "informixdb" dialects have been removed; the code
        is now available as a separate repository on Bitbucket.   The IBM-DB
        project has provided production-level Informix support since the
        informixdb dialect was first added.

    .. change::
        :tags: bug, orm

        Fixed bug where usage of new :class:`.Bundle` object would cause
        the :attr:`.Query.column_descriptions` attribute to fail.

    .. change::
        :tags: bug, examples

        Fixed bug which prevented history_meta recipe from working with
        joined inheritance schemes more than one level deep.

    .. change::
        :tags: bug, orm, sql, sqlite
        :tickets: 2858

        Fixed a regression introduced by the join rewriting feature of
        :ticket:`2369` and :ticket:`2587` where a nested join with one side
        already an aliased select would fail to translate the ON clause on the
        outside correctly; in the ORM this could be seen when using a
        SELECT statement as a "secondary" table.

.. changelog::
    :version: 0.9.0b1
    :released: October 26, 2013

    .. change::
        :tags: feature, orm
        :tickets: 2810

        The association proxy now returns ``None`` when fetching a scalar
        attribute off of a scalar relationship, where the scalar relationship
        itself points to ``None``, instead of raising an ``AttributeError``.

        .. seealso::

            :ref:`migration_2810`

    .. change::
        :tags: feature, sql, postgresql, mysql
        :tickets: 2183

        The Postgresql and MySQL dialects now support reflection/inspection
        of foreign key options, including ON UPDATE, ON DELETE.  Postgresql
        also reflects MATCH, DEFERRABLE, and INITIALLY.  Coutesy ijl.

    .. change::
        :tags: bug, mysql
        :tickets: 2839

        Fix and test parsing of MySQL foreign key options within reflection;
        this complements the work in :ticket:`2183` where we begin to support
        reflection of foreign key options such as ON UPDATE/ON DELETE
        cascade.

    .. change::
        :tags: bug, orm
        :tickets: 2787

        :func:`.attributes.get_history()` when used with a scalar column-mapped
        attribute will now honor the "passive" flag
        passed to it; as this defaults to ``PASSIVE_OFF``, the function will
        by default query the database if the value is not present.
        This is a behavioral change vs. 0.8.

        .. seealso::

            :ref:`change_2787`

    .. change::
        :tags: feature, orm
        :tickets: 2787

        Added new method :meth:`.AttributeState.load_history`, works like
        :attr:`.AttributeState.history` but also fires loader callables.

        .. seealso::

            :ref:`change_2787`


    .. change::
        :tags: feature, sql
        :tickets: 2850

        A :func:`.bindparam` construct with a "null" type (e.g. no type
        specified) is now copied when used in a typed expression, and the
        new copy is assigned the actual type of the compared column.  Previously,
        this logic would occur on the given :func:`.bindparam` in place.
        Additionally, a similar process now occurs for :func:`.bindparam` constructs
        passed to :meth:`.ValuesBase.values` for an :class:`.Insert` or
        :class:`.Update` construct, within the compilation phase of the
        construct.

        These are both subtle behavioral changes which may impact some
        usages.

        .. seealso::

            :ref:`migration_2850`

    .. change::
        :tags: feature, sql
        :tickets: 2804, 2823, 2734

        An overhaul of expression handling for special symbols particularly
        with conjunctions, e.g.
        ``None`` :func:`.expression.null` :func:`.expression.true`
        :func:`.expression.false`, including consistency in rendering NULL
        in conjunctions, "short-circuiting" of :func:`.and_` and :func:`.or_`
        expressions which contain boolean constants, and rendering of
        boolean constants and expressions as compared to "1" or "0" for backends
        that don't feature ``true``/``false`` constants.

        .. seealso::

            :ref:`migration_2804`

    .. change::
        :tags: feature, sql
        :tickets: 2838

        The typing system now handles the task of rendering "literal bind" values,
        e.g. values that are normally bound parameters but due to context must
        be rendered as strings, typically within DDL constructs such as
        CHECK constraints and indexes (note that "literal bind" values
        become used by DDL as of :ticket:`2742`).  A new method
        :meth:`.TypeEngine.literal_processor` serves as the base, and
        :meth:`.TypeDecorator.process_literal_param` is added to allow wrapping
        of a native literal rendering method.

        .. seealso::

            :ref:`change_2838`

    .. change::
        :tags: feature, sql
        :tickets: 2716

        The :meth:`.Table.tometadata` method now produces copies of
        all :attr:`.SchemaItem.info` dictionaries from all :class:`.SchemaItem`
        objects within the structure including columns, constraints,
        foreign keys, etc.   As these dictionaries
        are copies, they are independent of the original dictionary.
        Previously, only the ``.info`` dictionary of :class:`.Column` was transferred
        within this operation, and it was only linked in place, not copied.

    .. change::
        :tags: feature, postgresql
        :tickets: 2840

        Added support for rendering ``SMALLSERIAL`` when a :class:`.SmallInteger`
        type is used on a primary key autoincrement column, based on server
        version detection of Postgresql version 9.2 or greater.

    .. change::
        :tags: feature, mysql
        :tickets: 2817

        The MySQL :class:`.mysql.SET` type now features the same auto-quoting
        behavior as that of :class:`.mysql.ENUM`.  Quotes are not required when
        setting up the value, but quotes that are present will be auto-detected
        along with a warning.  This also helps with Alembic where
        the SET type doesn't render with quotes.

    .. change::
        :tags: feature, sql

        The ``default`` argument of :class:`.Column` now accepts a class
        or object method as an argument, in addition to a standalone function;
        will properly detect if the "context" argument is accepted or not.

    .. change::
        :tags: bug, sql
        :tickets: 2835

        The "name" attribute is set on :class:`.Index` before the "attach"
        events are called, so that attachment events can be used to dynamically
        generate a name for the index based on the parent table and/or
        columns.

    .. change::
        :tags: bug, engine
        :tickets: 2748

        The method signature of :meth:`.Dialect.reflecttable`, which in
        all known cases is provided by :class:`.DefaultDialect`, has been
        tightened to expect ``include_columns`` and ``exclude_columns``
        arguments without any kw option, reducing ambiguity - previously
        ``exclude_columns`` was missing.

    .. change::
        :tags: bug, sql
        :tickets: 2831

        The erroneous kw arg "schema" has been removed from the :class:`.ForeignKey`
        object. this was an accidental commit that did nothing; a warning is raised
        in 0.8.3 when this kw arg is used.

    .. change::
        :tags: feature, orm
        :tickets: 1418

        Added a new load option :func:`.orm.load_only`.  This allows a series
        of column names to be specified as loading "only" those attributes,
        deferring the rest.

    .. change::
        :tags: feature, orm
        :tickets: 1418

        The system of loader options has been entirely rearchitected to build
        upon a much more comprehensive base, the :class:`.Load` object.  This
        base allows any common loader option like :func:`.joinedload`,
        :func:`.defer`, etc. to be used in a "chained" style for the purpose
        of specifying options down a path, such as ``joinedload("foo").subqueryload("bar")``.
        The new system supersedes the usage of dot-separated path names,
        multiple attributes within options, and the usage of ``_all()`` options.

        .. seealso::

            :ref:`feature_1418`

    .. change::
        :tags: feature, orm
        :tickets: 2824

        The :func:`.composite` construct now maintains the return object
        when used in a column-oriented :class:`.Query`, rather than expanding
        out into individual columns.  This makes use of the new :class:`.Bundle`
        feature internally.  This behavior is backwards incompatible; to
        select from a composite column which will expand out, use
        ``MyClass.some_composite.clauses``.

        .. seealso::

            :ref:`migration_2824`

    .. change::
        :tags: feature, orm
        :tickets: 2824

        A new construct :class:`.Bundle` is added, which allows for specification
        of groups of column expressions to a :class:`.Query` construct.
        The group of columns are returned as a single tuple by default.  The
        behavior of :class:`.Bundle` can be overridden however to provide
        any sort of result processing to the returned row.  The behavior
        of :class:`.Bundle` is also embedded into composite attributes now
        when they are used in a column-oriented :class:`.Query`.

        .. seealso::

            :ref:`change_2824`

            :ref:`migration_2824`

    .. change::
        :tags: bug, sql
        :tickets: 2812

        A rework to the way that "quoted" identifiers are handled, in that
        instead of relying upon various ``quote=True`` flags being passed around,
        these flags are converted into rich string objects with quoting information
        included at the point at which they are passed to common schema constructs
        like :class:`.Table`, :class:`.Column`, etc.   This solves the issue
        of various methods that don't correctly honor the "quote" flag such
        as :meth:`.Engine.has_table` and related methods.  The :class:`.quoted_name`
        object is a string subclass that can also be used explicitly if needed;
        the object will hold onto the quoting preferences passed and will
        also bypass the "name normalization" performed by dialects that
        standardize on uppercase symbols, such as Oracle, Firebird and DB2.
        The upshot is that the "uppercase" backends can now work with force-quoted
        names, such as lowercase-quoted names and new reserved words.

        .. seealso::

            :ref:`change_2812`

    .. change::
        :tags: feature, orm
        :tickets: 2793

        The ``version_id_generator`` parameter of ``Mapper`` can now be specified
        to rely upon server generated version identifiers, using triggers
        or other database-provided versioning features, or via an optional programmatic
        value, by setting ``version_id_generator=False``.
        When using a server-generated version identfier, the ORM will use RETURNING when
        available to immediately
        load the new version value, else it will emit a second SELECT.

    .. change::
        :tags: feature, orm
        :tickets: 2793

        The ``eager_defaults`` flag of :class:`.Mapper` will now allow the
        newly generated default values to be fetched using an inline
        RETURNING clause, rather than a second SELECT statement, for backends
        that support RETURNING.

    .. change::
        :tags: feature, core
        :tickets: 2793

        Added a new variant to :meth:`.UpdateBase.returning` called
        :meth:`.ValuesBase.return_defaults`; this allows arbitrary columns
        to be added to the RETURNING clause of the statement without interfering
        with the compilers usual "implicit returning" feature, which is used to
        efficiently fetch newly generated primary key values.  For supporting
        backends, a dictionary of all fetched values is present at
        :attr:`.ResultProxy.returned_defaults`.

    .. change::
        :tags: bug, mysql

        Improved support for the cymysql driver, supporting version 0.6.5,
        courtesy Hajime Nakagami.

    .. change::
        :tags: general

        A large refactoring of packages has reorganized
        the import structure of many Core modules as well as some aspects
        of the ORM modules.  In particular ``sqlalchemy.sql`` has been broken
        out into several more modules than before so that the very large size
        of ``sqlalchemy.sql.expression`` is now pared down.   The effort
        has focused on a large reduction in import cycles.   Additionally,
        the system of API functions in ``sqlalchemy.sql.expression`` and
        ``sqlalchemy.orm`` has been reorganized to eliminate redundancy
        in documentation between the functions vs. the objects they produce.

    .. change::
        :tags: orm, feature, orm

        Added a new attribute :attr:`.Session.info` to :class:`.Session`;
        this is a dictionary where applications can store arbitrary
        data local to a :class:`.Session`.
        The contents of :attr:`.Session.info` can be also be initialized
        using the ``info`` argument of :class:`.Session` or
        :class:`.sessionmaker`.


    .. change::
        :tags: feature, general, py3k
        :tickets: 2161

        The C extensions are ported to Python 3 and will build under
        any supported CPython 2 or 3 environment.

    .. change::
        :tags: feature, orm
        :tickets: 2268

        Removal of event listeners is now implemented.    The feature is
        provided via the :func:`.event.remove` function.

        .. seealso::

            :ref:`feature_2268`

    .. change::
        :tags: feature, orm
        :tickets: 2789

        The mechanism by which attribute events pass along an
        :class:`.AttributeImpl` as an "initiator" token has been changed;
        the object is now an event-specific object called :class:`.attributes.Event`.
        Additionally, the attribute system no longer halts events based
        on a matching "initiator" token; this logic has been moved to be
        specific to ORM backref event handlers, which are the typical source
        of the re-propagation of an attribute event onto subsequent append/set/remove
        operations.  End user code which emulates the behavior of backrefs
        must now ensure that recursive event propagation schemes are halted,
        if the scheme does not use the backref handlers.   Using this new system,
        backref handlers can now perform a
        "two-hop" operation when an object is appended to a collection,
        associated with a new many-to-one, de-associated with the previous
        many-to-one, and then removed from a previous collection.   Before this
        change, the last step of removal from the previous collection would
        not occur.

        .. seealso::

            :ref:`migration_2789`

    .. change::
        :tags: feature, sql
        :tickets: 722

        Added new method to the :func:`.insert` construct
        :meth:`.Insert.from_select`.  Given a list of columns and
        a selectable, renders ``INSERT INTO (table) (columns) SELECT ..``.
        While this feature is highlighted as part of 0.9 it is also
        backported to 0.8.3.

        .. seealso::

            :ref:`feature_722`

    .. change::
        :tags: feature, engine
        :tickets: 2770

        New events added to :class:`.ConnectionEvents`:

        * :meth:`.ConnectionEvents.engine_connect`
        * :meth:`.ConnectionEvents.set_connection_execution_options`
        * :meth:`.ConnectionEvents.set_engine_execution_options`

    .. change::
        :tags: bug, sql
        :tickets: 1765

        The resolution of :class:`.ForeignKey` objects to their
        target :class:`.Column` has been reworked to be as
        immediate as possible, based on the moment that the
        target :class:`.Column` is associated with the same
        :class:`.MetaData` as this :class:`.ForeignKey`, rather
        than waiting for the first time a join is constructed,
        or similar. This along with other improvements allows
        earlier detection of some foreign key configuration
        issues.  Also included here is a rework of the
        type-propagation system, so that
        it should be reliable now to set the type as ``None``
        on any :class:`.Column` that refers to another via
        :class:`.ForeignKey` - the type will be copied from the
        target column as soon as that other column is associated,
        and now works for composite foreign keys as well.

        .. seealso::

            :ref:`migration_1765`

    .. change::
        :tags: feature, sql
        :tickets: 2744, 2734

        Provided a new attribute for :class:`.TypeDecorator`
        called :attr:`.TypeDecorator.coerce_to_is_types`,
        to make it easier to control how comparisons using
        ``==`` or ``!=`` to ``None`` and boolean types goes
        about producing an ``IS`` expression, or a plain
        equality expression with a bound parameter.

    .. change::
        :tags: feature, pool
        :tickets: 2752

        Added pool logging for "rollback-on-return" and the less used
        "commit-on-return".  This is enabled with the rest of pool
        "debug" logging.

    .. change::
        :tags: bug, orm, associationproxy
        :tickets: 2751

        Added additional criterion to the ==, != comparators, used with
        scalar values, for comparisons to None to also take into account
        the association record itself being non-present, in addition to the
        existing test for the scalar endpoint on the association record
        being NULL.  Previously, comparing ``Cls.scalar == None`` would return
        records for which ``Cls.associated`` were present and
        ``Cls.associated.scalar`` is None, but not rows for which
        ``Cls.associated`` is non-present.  More significantly, the
        inverse operation ``Cls.scalar != None`` *would* return ``Cls``
        rows for which ``Cls.associated`` was non-present.

        The case for ``Cls.scalar != 'somevalue'`` is also modified
        to act more like a direct SQL comparison; only rows for
        which ``Cls.associated`` is present and ``Associated.scalar``
        is non-NULL and not equal to ``'somevalue'`` are returned.
        Previously, this would be a simple ``NOT EXISTS``.

        Also added a special use case where you
        can call ``Cls.scalar.has()`` with no arguments,
        when ``Cls.scalar`` is a column-based value - this returns whether or
        not ``Cls.associated`` has any rows present, regardless of whether
        or not ``Cls.associated.scalar`` is NULL or not.

        .. seealso::

            :ref:`migration_2751`


    .. change::
        :tags: feature, orm
        :tickets: 2587

        A major change regarding how the ORM constructs joins where
        the right side is itself a join or left outer join.   The ORM
        is now configured to allow simple nesting of joins of
        the form ``a JOIN (b JOIN c ON b.id=c.id) ON a.id=b.id``,
        rather than forcing the right side into a ``SELECT`` subquery.
        This should allow significant performance improvements on most
        backends, most particularly MySQL.   The one database backend
        that has for many years held back this change, SQLite, is now addressed by
        moving the production of the ``SELECT`` subquery from the
        ORM to the SQL compiler; so that a right-nested join on SQLite will still
        ultimately render with a ``SELECT``, while all other backends
        are no longer impacted by this workaround.

        As part of this change, a new argument ``flat=True`` has been added
        to the :func:`.orm.aliased`, :meth:`.Join.alias`, and
        :func:`.orm.with_polymorphic` functions, which allows an "alias" of a
        JOIN to be produced which applies an anonymous alias to each component
        table within the join, rather than producing a subquery.

        .. seealso::

            :ref:`feature_joins_09`


    .. change::
        :tags: bug, orm
        :tickets: 2369

        Fixed an obscure bug where the wrong results would be
        fetched when joining/joinedloading across a many-to-many
        relationship to a single-table-inheriting
        subclass with a specific discriminator value, due to "secondary"
        rows that would come back.  The "secondary" and right-side
        tables are now inner joined inside of parenthesis for all
        ORM joins on many-to-many relationships so that the left->right
        join can accurately filtered.  This change was made possible
        by finally addressing the issue with right-nested joins
        outlined in :ticket:`2587`.

        .. seealso::

            :ref:`feature_joins_09`

    .. change::
        :tags: bug, mssql, pyodbc
        :tickets: 2355

        Fixes to MSSQL with Python 3 + pyodbc, including that statements
        are passed correctly.

    .. change::
        :tags: feature, sql
        :tickets: 1068

        A :func:`~sqlalchemy.sql.expression.label` construct will now render as its name alone
        in an ``ORDER BY`` clause, if that label is also referred to
        in the columns clause of the select, instead of rewriting the
        full expression.  This gives the database a better chance to
        optimize the evaulation of the same expression in two different
        contexts.

        .. seealso::

            :ref:`migration_1068`

    .. change::
        :tags: feature, firebird
        :tickets: 2504

        The ``fdb`` dialect is now the default dialect when
        specified without a dialect qualifier, i.e. ``firebird://``,
        per the Firebird project publishing ``fdb`` as their
        official Python driver.

    .. change::
    	:tags: feature, general, py3k
      	:tickets: 2671

        The codebase is now "in-place" for Python
        2 and 3, the need to run 2to3 has been removed.
        Compatibility is now against Python 2.6 on forward.

    .. change::
    	:tags: feature, oracle, py3k

    	The Oracle unit tests with cx_oracle now pass
    	fully under Python 3.

    .. change::
        :tags: bug, orm
        :tickets: 2736

        The "auto-aliasing" behavior of the :meth:`.Query.select_from`
        method has been turned off.  The specific behavior is now
        available via a new method :meth:`.Query.select_entity_from`.
        The auto-aliasing behavior here was never well documented and
        is generally not what's desired, as :meth:`.Query.select_from`
        has become more oriented towards controlling how a JOIN is
        rendered.  :meth:`.Query.select_entity_from` will also be made
        available in 0.8 so that applications which rely on the auto-aliasing
        can shift their applications to use this method.

        .. seealso::

            :ref:`migration_2736`
