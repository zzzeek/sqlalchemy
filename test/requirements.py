"""Requirements specific to SQLAlchemy's own unit tests.


"""

from sqlalchemy import util
import sys
from sqlalchemy.testing.requirements import SuiteRequirements
from sqlalchemy.testing import exclusions
from sqlalchemy.testing.exclusions import \
     skip, \
     skip_if,\
     only_if,\
     only_on,\
     fails_on_everything_except,\
     fails_on,\
     fails_if,\
     succeeds_if,\
     SpecPredicate,\
     against,\
     LambdaPredicate,\
     requires_tag


def no_support(db, reason):
    return SpecPredicate(db, description=reason)


def exclude(db, op, spec, description=None):
    return SpecPredicate(db, op, spec, description=description)


class DefaultRequirements(SuiteRequirements):
    @property
    def deferrable_or_no_constraints(self):
        """Target database must support deferrable constraints."""

        return skip_if([
            no_support('firebird', 'not supported by database'),
            no_support('mysql', 'not supported by database'),
            no_support('mssql', 'not supported by database'),
            ])

    @property
    def check_constraints(self):
        """Target database must support check constraints."""

        return exclusions.open()

    @property
    def enforces_check_constraints(self):
        """Target database must also enforce check constraints."""

        return self.check_constraints + fails_on(
            self._mysql_not_mariadb_102,
            "check constraints don't enforce on MySQL, MariaDB<10.2"
        )

    @property
    def named_constraints(self):
        """target database must support names for constraints."""

        return exclusions.open()

    @property
    def implicitly_named_constraints(self):
        """target database must apply names to unnamed constraints."""

        return skip_if([
            no_support('sqlite', 'not supported by database'),
            ])

    @property
    def foreign_keys(self):
        """Target database must support foreign keys."""

        return skip_if(
                no_support('sqlite', 'not supported by database')
            )

    @property
    def on_update_cascade(self):
        """target database must support ON UPDATE..CASCADE behavior in
        foreign keys."""

        return skip_if(
                    ['sqlite', 'oracle'],
                    'target backend %(doesnt_support)s ON UPDATE CASCADE'
                )

    @property
    def non_updating_cascade(self):
        """target database must *not* support ON UPDATE..CASCADE behavior in
        foreign keys."""

        return fails_on_everything_except('sqlite', 'oracle', '+zxjdbc') + \
            skip_if('mssql')

    @property
    def recursive_fk_cascade(self):
        """target database must support ON DELETE CASCADE on a self-referential
        foreign key"""

        return skip_if(["mssql"])

    @property
    def deferrable_fks(self):
        """target database must support deferrable fks"""

        return only_on(['oracle'])

    @property
    def foreign_key_constraint_option_reflection_ondelete(self):
        return only_on(['postgresql', 'mysql', 'sqlite', 'oracle'])

    @property
    def foreign_key_constraint_option_reflection_onupdate(self):
        return only_on(['postgresql', 'mysql', 'sqlite'])

    @property
    def comment_reflection(self):
        return only_on(['postgresql', 'mysql', 'oracle'])

    @property
    def unbounded_varchar(self):
        """Target database must support VARCHAR with no length"""

        return skip_if([
                "firebird", "oracle", "mysql"
            ], "not supported by database"
            )

    @property
    def boolean_col_expressions(self):
        """Target database must support boolean expressions as columns"""
        return skip_if([
            no_support('firebird', 'not supported by database'),
            no_support('oracle', 'not supported by database'),
            no_support('mssql', 'not supported by database'),
            no_support('sybase', 'not supported by database'),
        ])

    @property
    def non_native_boolean_unconstrained(self):
        """target database is not native boolean and allows arbitrary integers
        in it's "bool" column"""

        return skip_if([
            LambdaPredicate(
                lambda config: against(config, "mssql"),
                "SQL Server drivers / odbc seem to change their mind on this"
            ),
            LambdaPredicate(
                lambda config: config.db.dialect.supports_native_boolean,
                "native boolean dialect"
            )
        ])

    @property
    def standalone_binds(self):
        """target database/driver supports bound parameters as column expressions
        without being in the context of a typed column.

        """
        return skip_if(["firebird", "mssql+mxodbc"], "not supported by driver")

    @property
    def no_quoting_special_bind_names(self):
        """Target database will quote bound paramter names, doesn't support
        EXPANDING"""

        return skip_if(["oracle"])

    @property
    def identity(self):
        """Target database must support GENERATED AS IDENTITY or a facsimile.

        Includes GENERATED AS IDENTITY, AUTOINCREMENT, AUTO_INCREMENT, or other
        column DDL feature that fills in a DB-generated identifier at
        INSERT-time without requiring pre-execution of a SEQUENCE or other
        artifact.

        """
        return skip_if(["firebird", "oracle", "postgresql", "sybase"],
                       "not supported by database")

    @property
    def temporary_tables(self):
        """target database supports temporary tables"""
        return skip_if(
                    ["mssql", "firebird"], "not supported (?)"
                )

    @property
    def temp_table_reflection(self):
        return self.temporary_tables

    @property
    def reflectable_autoincrement(self):
        """Target database must support tables that can automatically generate
        PKs assuming they were reflected.

        this is essentially all the DBs in "identity" plus PostgreSQL, which
        has SERIAL support.  FB and Oracle (and sybase?) require the Sequence
        to be explicitly added, including if the table was reflected.
        """
        return skip_if(["firebird", "oracle", "sybase"],
                       "not supported by database")

    @property
    def insert_from_select(self):
        return skip_if(
                    ["firebird"], "crashes for unknown reason"
                )

    @property
    def fetch_rows_post_commit(self):
        return skip_if(
                    ["firebird"], "not supported"
                )

    @property
    def non_broken_binary(self):
        """target DBAPI must work fully with binary values"""

        # see https://github.com/pymssql/pymssql/issues/504
        return skip_if(["mssql+pymssql"])

    @property
    def binary_comparisons(self):
        """target database/driver can allow BLOB/BINARY fields to be compared
        against a bound parameter value.
        """
        return skip_if(["oracle", "mssql"], "not supported by database/driver")

    @property
    def binary_literals(self):
        """target backend supports simple binary literals, e.g. an
        expression like::

            SELECT CAST('foo' AS BINARY)

        Where ``BINARY`` is the type emitted from :class:`.LargeBinary`,
        e.g. it could be ``BLOB`` or similar.

        Basically fails on Oracle.

        """
        # adding mssql here since it doesn't support comparisons either,
        # have observed generally bad behavior with binary / mssql.

        return skip_if(["oracle", "mssql"], "not supported by database/driver")

    @property
    def tuple_in(self):
        return only_on(["mysql", "postgresql"])

    @property
    def independent_cursors(self):
        """Target must support simultaneous, independent database cursors
        on a single connection."""

        return skip_if(
            [
                "mssql",
                "mysql"], "no driver support"
        )

    @property
    def independent_connections(self):
        """
        Target must support simultaneous, independent database connections.
        """

        # This is also true of some configurations of UnixODBC and probably
        # win32 ODBC as well.
        return skip_if([
            no_support("sqlite",
                       "independent connections disabled "
                       "when :memory: connections are used"),
            exclude("mssql", "<", (9, 0, 0),
                    "SQL Server 2005+ is required for "
                    "independent connections")])

    @property
    def memory_process_intensive(self):
        """Driver is able to handle the memory tests which run in a subprocess
        and iterate through hundreds of connections

        """
        return skip_if([
            no_support("oracle", "Oracle XE usually can't handle these"),
            no_support("mssql+pyodbc", "MS ODBC drivers struggle")
        ])

    @property
    def updateable_autoincrement_pks(self):
        """Target must support UPDATE on autoincrement/integer primary key."""

        return skip_if(["mssql", "sybase"],
                       "IDENTITY columns can't be updated")

    @property
    def isolation_level(self):
        return only_on(
            ('postgresql', 'sqlite', 'mysql', 'mssql'),
            "DBAPI has no isolation level support") \
            + fails_on('postgresql+pypostgresql',
                       'pypostgresql bombs on multiple isolation level calls')

    @property
    def autocommit(self):
        """target dialect supports 'AUTOCOMMIT' as an isolation_level"""
        return only_on(
            ('postgresql', 'mysql', 'mssql+pyodbc', 'mssql+pymssql'),
            "dialect does not support AUTOCOMMIT isolation mode")

    @property
    def row_triggers(self):
        """Target must support standard statement-running EACH ROW triggers."""

        return skip_if([
            # no access to same table
            no_support('mysql', 'requires SUPER priv'),
            exclude('mysql', '<', (5, 0, 10), 'not supported by database'),

            # huh?  TODO: implement triggers for PG tests, remove this
            no_support('postgresql',
                       'PG triggers need to be implemented for tests'),
        ])

    @property
    def sequences_as_server_defaults(self):
        """Target database must support SEQUENCE as a server side default."""

        return only_on(
            'postgresql',
            "doesn't support sequences as a server side default.")

    @property
    def correlated_outer_joins(self):
        """Target must support an outer join to a subquery which
        correlates to the parent."""

        return skip_if("oracle", 'Raises "ORA-01799: a column may not be '
                       'outer-joined to a subquery"')

    @property
    def update_from(self):
        """Target must support UPDATE..FROM syntax"""

        return only_on(['postgresql', 'mssql', 'mysql'],
                       "Backend does not support UPDATE..FROM")

    @property
    def delete_from(self):
        """Target must support DELETE FROM..FROM or DELETE..USING syntax"""
        return only_on(['postgresql', 'mssql', 'mysql', 'sybase'],
                       "Backend does not support DELETE..FROM")

    @property
    def update_where_target_in_subquery(self):
        """Target must support UPDATE (or DELETE) where the same table is
        present in a subquery in the WHERE clause.

        This is an ANSI-standard syntax that apparently MySQL can't handle,
        such as:

        UPDATE documents SET flag=1 WHERE documents.title IN
            (SELECT max(documents.title) AS title
                FROM documents GROUP BY documents.user_id
            )
        """
        return fails_if(
            self._mysql_not_mariadb_103,
            'MySQL error 1093 "Cant specify target table '
            'for update in FROM clause", resolved by MariaDB 10.3')

    @property
    def savepoints(self):
        """Target database must support savepoints."""

        return skip_if([
                    "sqlite",
                    "sybase",
                    ("mysql", "<", (5, 0, 3)),
                    ], "savepoints not supported")

    @property
    def savepoints_w_release(self):
        return self.savepoints + skip_if(
            ["oracle", "mssql"],
            "database doesn't support release of savepoint"
        )


    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return skip_if([
                    "firebird"
                ], "no schema support")

    @property
    def cross_schema_fk_reflection(self):
        """target system must support reflection of inter-schema foreign keys
        """
        return only_on([
                    "postgresql",
                    "mysql",
                    "mssql",
                ])

    @property
    def implicit_default_schema(self):
        """target system has a strong concept of 'default' schema that can
           be referred to implicitly.

           basically, PostgreSQL.

        """
        return only_on([
                    "postgresql",
                ])


    @property
    def unique_constraint_reflection(self):
        return fails_on_everything_except(
                    "postgresql",
                    "mysql",
                    "sqlite",
                    "oracle"
                )

    @property
    def unique_constraint_reflection_no_index_overlap(self):
        return self.unique_constraint_reflection + \
            skip_if("mysql")  + skip_if("oracle")


    @property
    def check_constraint_reflection(self):
        return fails_on_everything_except(
            "postgresql", "sqlite", "oracle",
            self._mariadb_102
        )

    @property
    def temp_table_names(self):
        """target dialect supports listing of temporary table names"""

        return only_on(['sqlite', 'oracle'])

    @property
    def temporary_views(self):
        """target database supports temporary views"""
        return only_on(['sqlite', 'postgresql'])

    @property
    def update_nowait(self):
        """Target database must support SELECT...FOR UPDATE NOWAIT"""
        return skip_if(["firebird", "mssql", "mysql", "sqlite", "sybase"],
                       "no FOR UPDATE NOWAIT support")

    @property
    def subqueries(self):
        """Target database must support subqueries."""

        return skip_if(exclude('mysql', '<', (4, 1, 1)), 'no subquery support')

    @property
    def ctes(self):
        """Target database supports CTEs"""

        return only_on([
            lambda config: against(config, "mysql") and (
                config.db.dialect._is_mariadb and
                config.db.dialect._mariadb_normalized_version_info >=
                (10, 2)
            ),
            "postgresql",
            "mssql",
            "oracle"
        ])

    @property
    def ctes_with_update_delete(self):
        """target database supports CTES that ride on top of a normal UPDATE
        or DELETE statement which refers to the CTE in a correlated subquery.

        """
        return only_on([
            "postgresql",
            "mssql",
            # "oracle" - oracle can do this but SQLAlchemy doesn't support
            # their syntax yet
        ])

    @property
    def ctes_on_dml(self):
        """target database supports CTES which consist of INSERT, UPDATE
        or DELETE *within* the CTE, e.g. WITH x AS (UPDATE....)"""

        return only_if(
            ['postgresql']
        )

    @property
    def mod_operator_as_percent_sign(self):
        """target database must use a plain percent '%' as the 'modulus'
        operator."""

        return only_if(
                    ['mysql', 'sqlite', 'postgresql+psycopg2', 'mssql']
                )

    @property
    def intersect(self):
        """Target database must support INTERSECT or equivalent."""

        return fails_if([
            "firebird", self._mysql_not_mariadb_103,
            "sybase",
        ], 'no support for INTERSECT')

    @property
    def except_(self):
        """Target database must support EXCEPT or equivalent (i.e. MINUS)."""
        return fails_if([
            "firebird", self._mysql_not_mariadb_103,
            "sybase",
        ], 'no support for EXCEPT')

    @property
    def order_by_col_from_union(self):
        """target database supports ordering by a column from a SELECT
        inside of a UNION

        E.g.  (SELECT id, ...) UNION (SELECT id, ...) ORDER BY id

        Fails on SQL Server

        """
        return fails_if('mssql')

    @property
    def parens_in_union_contained_select_w_limit_offset(self):
        """Target database must support parenthesized SELECT in UNION
        when LIMIT/OFFSET is specifically present.

        E.g. (SELECT ... LIMIT ..) UNION (SELECT .. OFFSET ..)

        This is known to fail on SQLite.

        """
        return fails_if('sqlite')

    @property
    def parens_in_union_contained_select_wo_limit_offset(self):
        """Target database must support parenthesized SELECT in UNION
        when OFFSET/LIMIT is specifically not present.

        E.g. (SELECT ...) UNION (SELECT ..)

        This is known to fail on SQLite.  It also fails on Oracle
        because without LIMIT/OFFSET, there is currently no step that
        creates an additional subquery.

        """
        return fails_if(['sqlite', 'oracle'])

    @property
    def offset(self):
        """Target database must support some method of adding OFFSET or
        equivalent to a result set."""
        return fails_if([
                "sybase"
            ], 'no support for OFFSET or equivalent')

    @property
    def window_functions(self):
        return only_if([
                    "postgresql>=8.4", "mssql", "oracle"
                ], "Backend does not support window functions")

    @property
    def two_phase_transactions(self):
        """Target database must support two-phase transactions."""

        return skip_if([
            no_support('firebird', 'no SA implementation'),
            no_support('mssql', 'two-phase xact not supported by drivers'),
            no_support('oracle',
                       'two-phase xact not implemented in SQLA/oracle'),
            no_support('drizzle', 'two-phase xact not supported by database'),
            no_support('sqlite', 'two-phase xact not supported by database'),
            no_support('sybase',
                       'two-phase xact not supported by drivers/SQLA'),
            no_support('postgresql+zxjdbc',
                       'FIXME: JDBC driver confuses the transaction state, '
                       'may need separate XA implementation'),
            no_support('mysql',
                       'recent MySQL communiity editions have too many issues '
                       '(late 2016), disabling for now')])

    @property
    def two_phase_recovery(self):
        return self.two_phase_transactions + (
            skip_if(
               "mysql",
               "crashes on most mariadb and mysql versions"
            )
        )

    @property
    def views(self):
        """Target database must support VIEWs."""

        return skip_if("drizzle", "no VIEW support")

    @property
    def empty_strings_varchar(self):
        """
        target database can persist/return an empty string with a varchar.
        """

        return fails_if(["oracle"],
                        'oracle converts empty strings to a blank space')

    @property
    def empty_strings_text(self):
        """target database can persist/return an empty string with an
        unbounded text."""

        return exclusions.open()

    @property
    def unicode_data(self):
        """target drive must support unicode data stored in columns."""
        return skip_if([
            no_support("sybase", "no unicode driver support")
            ])

    @property
    def unicode_connections(self):
        """
        Target driver must support some encoding of Unicode across the wire.
        """
        # TODO: expand to exclude MySQLdb versions w/ broken unicode
        return skip_if([
            exclude('mysql', '<', (4, 1, 1), 'no unicode connection support'),
            ])

    @property
    def unicode_ddl(self):
        """Target driver must support some degree of non-ascii symbol names."""
        # TODO: expand to exclude MySQLdb versions w/ broken unicode

        return skip_if([
            no_support('oracle', 'FIXME: no support in database?'),
            no_support('sybase', 'FIXME: guessing, needs confirmation'),
            no_support('mssql+pymssql', 'no FreeTDS support'),
            LambdaPredicate(
                lambda config: against(config, "mysql+mysqlconnector") and
                config.db.dialect._mysqlconnector_version_info > (2, 0) and
                util.py2k,
                "bug in mysqlconnector 2.0"
            ),
            exclude('mysql', '<', (4, 1, 1), 'no unicode connection support'),
        ])

    @property
    def emulated_lastrowid(self):
        """"target dialect retrieves cursor.lastrowid or an equivalent
        after an insert() construct executes.
        """
        return fails_on_everything_except('mysql',
                                          'sqlite+pysqlite',
                                          'sqlite+pysqlcipher',
                                          'sybase',
                                          'mssql')

    @property
    def implements_get_lastrowid(self):
        return skip_if([
            no_support('sybase', 'not supported by database'),
            ])

    @property
    def dbapi_lastrowid(self):
        """"target backend includes a 'lastrowid' accessor on the DBAPI
        cursor object.

        """
        return skip_if('mssql+pymssql', 'crashes on pymssql') + \
            fails_on_everything_except('mysql',
                                       'sqlite+pysqlite',
                                       'sqlite+pysqlcipher')

    @property
    def nullsordering(self):
        """Target backends that support nulls ordering."""
        return fails_on_everything_except('postgresql', 'oracle', 'firebird')

    @property
    def reflects_pk_names(self):
        """Target driver reflects the name of primary key constraints."""

        return fails_on_everything_except('postgresql', 'oracle', 'mssql',
                                          'sybase', 'sqlite')

    @property
    def nested_aggregates(self):
        """target database can select an aggregate from a subquery that's
        also using an aggregate"""

        return skip_if(["mssql"])

    @property
    def array_type(self):
        return only_on([
            lambda config: against(config, "postgresql") and
            not against(config, "+pg8000") and not against(config, "+zxjdbc")
        ])

    @property
    def json_type(self):
        return only_on([
            lambda config:
                against(config, "mysql") and (
                    (
                        not config.db.dialect._is_mariadb and
                        against(config, "mysql >= 5.7")
                    )
                    or (
                        config.db.dialect._mariadb_normalized_version_info >=
                        (10, 2, 7)
                    )
                ),
            "postgresql >= 9.3",
            "sqlite >= 3.9"
        ])

    @property
    def reflects_json_type(self):
        return only_on([
            lambda config: against(config, "mysql >= 5.7") and
            not config.db.dialect._is_mariadb,
            "postgresql >= 9.3",
            "sqlite >= 3.9"
        ])

    @property
    def json_array_indexes(self):
        return self.json_type + fails_if("+pg8000")

    @property
    def datetime_literals(self):
        """target dialect supports rendering of a date, time, or datetime as a
        literal string, e.g. via the TypeEngine.literal_processor() method.

        """

        return fails_on_everything_except("sqlite")

    @property
    def datetime(self):
        """target dialect supports representation of Python
        datetime.datetime() objects."""

        return exclusions.open()

    @property
    def datetime_microseconds(self):
        """target dialect supports representation of Python
        datetime.datetime() with microsecond objects."""

        return skip_if(['mssql', 'mysql', 'firebird', '+zxjdbc',
                        'oracle', 'sybase'])

    @property
    def timestamp_microseconds(self):
        """target dialect supports representation of Python
        datetime.datetime() with microsecond objects but only
        if TIMESTAMP is used."""

        return only_on(['oracle'])

    @property
    def datetime_historic(self):
        """target dialect supports representation of Python
        datetime.datetime() objects with historic (pre 1900) values."""

        return succeeds_if(['sqlite', 'postgresql', 'firebird'])

    @property
    def date(self):
        """target dialect supports representation of Python
        datetime.date() objects."""

        return exclusions.open()

    @property
    def date_coerces_from_datetime(self):
        """target dialect accepts a datetime object as the target
        of a date column."""

        # does not work as of pyodbc 4.0.22
        return fails_on('mysql+mysqlconnector') + skip_if("mssql+pyodbc")

    @property
    def date_historic(self):
        """target dialect supports representation of Python
        datetime.datetime() objects with historic (pre 1900) values."""

        return succeeds_if(['sqlite', 'postgresql', 'firebird'])

    @property
    def time(self):
        """target dialect supports representation of Python
        datetime.time() objects."""

        return skip_if(['oracle'])

    @property
    def time_microseconds(self):
        """target dialect supports representation of Python
        datetime.time() with microsecond objects."""

        return skip_if(['mssql', 'mysql', 'firebird', '+zxjdbc',
                        'oracle', 'sybase'])

    @property
    def precision_numerics_general(self):
        """target backend has general support for moderately high-precision
        numerics."""
        return exclusions.open()

    @property
    def precision_numerics_enotation_small(self):
        """target backend supports Decimal() objects using E notation
        to represent very small values."""
        # NOTE: this exclusion isn't used in current tests.
        return exclusions.open()

    @property
    def precision_numerics_enotation_large(self):
        """target backend supports Decimal() objects using E notation
        to represent very large values."""

        return fails_if(
            [
                ("sybase+pyodbc", None, None,
                 "Don't know how do get these values through FreeTDS + Sybase"
                 ),
                ("firebird", None, None, "Precision must be from 1 to 18")
            ]
        )

    @property
    def precision_numerics_many_significant_digits(self):
        """target backend supports values with many digits on both sides,
        such as 319438950232418390.273596, 87673.594069654243

        """

        def broken_cx_oracle(config):
            return against(config, 'oracle+cx_oracle') and \
                config.db.dialect.cx_oracle_ver <= (6, 0, 2) and \
                config.db.dialect.cx_oracle_ver > (6, )

        return fails_if(
            [
                ('sqlite', None, None, 'TODO'),
                ("firebird", None, None, "Precision must be from 1 to 18"),
                ("sybase+pysybase", None, None, "TODO"),
            ]
        )

    @property
    def precision_numerics_retains_significant_digits(self):
        """A precision numeric type will return empty significant digits,
        i.e. a value such as 10.000 will come back in Decimal form with
        the .000 maintained."""

        return fails_if(
            [
                ("oracle", None, None, "driver doesn't do this automatically"),
                ("firebird", None, None,
                 "database and/or driver truncates decimal places.")
            ]
        )

    @property
    def precision_generic_float_type(self):
        """target backend will return native floating point numbers with at
        least seven decimal places when using the generic Float type."""

        return fails_if([
            ('mysql', None, None,
             'mysql FLOAT type only returns 4 decimals'),
            ('firebird', None, None,
             "firebird FLOAT type isn't high precision"),
        ])

    @property
    def floats_to_four_decimals(self):
        return fails_if([
            ("mysql+oursql", None, None, "Floating point error"),
            ("firebird", None, None,
             "Firebird still has FP inaccuracy even "
             "with only four decimal places"),
            ('mssql+pyodbc', None, None,
             'mssql+pyodbc has FP inaccuracy even with '
             'only four decimal places '),
            ('mssql+pymssql', None, None,
             'mssql+pymssql has FP inaccuracy even with '
             'only four decimal places '),
            ('postgresql+pg8000', None, None,
             'postgresql+pg8000 has FP inaccuracy even with '
             'only four decimal places '),
            ('postgresql+psycopg2cffi', None, None,
             'postgresql+psycopg2cffi has FP inaccuracy even with '
             'only four decimal places ')])

    @property
    def implicit_decimal_binds(self):
        """target backend will return a selected Decimal as a Decimal, not
        a string.

        e.g.::

            expr = decimal.Decimal("15.7563")

            value = e.scalar(
                select([literal(expr)])
            )

            assert value == expr

        See :ticket:`4036`

        """

        # fixed for mysqlclient in
        # https://github.com/PyMySQL/mysqlclient-python/commit/68b9662918577fc05be9610ef4824a00f2b051b0
        def check(config):
            if against(config, "mysql+mysqldb"):
                # can remove once post 1.3.13 is released
                try:
                    from MySQLdb import converters
                    from decimal import Decimal
                    return Decimal not in converters.conversions
                except:
                    return True

            return against(config, "mysql+mysqldb") and \
                config.db.dialect._mysql_dbapi_version <= (1, 3, 13)
        return exclusions.fails_on(check, "fixed for mysqlclient post 1.3.13")

    @property
    def fetch_null_from_numeric(self):
        return skip_if(
                    ("mssql+pyodbc", None, None, "crashes due to bug #351"),
                )

    @property
    def duplicate_key_raises_integrity_error(self):
        return fails_on("postgresql+pg8000")

    def _has_pg_extension(self, name):
        def check(config):
            if not against(config, "postgresql"):
                return False
            count = config.db.scalar(
                "SELECT count(*) FROM pg_extension "
                "WHERE extname='%s'" % name)
            return bool(count)
        return only_if(check, "needs %s extension" % name)

    @property
    def hstore(self):
        return self._has_pg_extension("hstore")

    @property
    def btree_gist(self):
        return self._has_pg_extension("btree_gist")

    @property
    def range_types(self):
        def check_range_types(config):
            if not against(
                    config,
                    ["postgresql+psycopg2", "postgresql+psycopg2cffi"]):
                return False
            try:
                config.db.scalar("select '[1,2)'::int4range;")
                return True
            except Exception:
                return False

        return only_if(check_range_types)

    @property
    def oracle_test_dblink(self):
        return skip_if(
                    lambda config: not config.file_config.has_option(
                        'sqla_testing', 'oracle_db_link'),
                    "oracle_db_link option not specified in config"
                )

    @property
    def postgresql_test_dblink(self):
        return skip_if(
                    lambda config: not config.file_config.has_option(
                        'sqla_testing', 'postgres_test_db_link'),
                    "postgres_test_db_link option not specified in config"
                )

    @property
    def postgresql_jsonb(self):
        return only_on("postgresql >= 9.4") + skip_if(
            lambda config:
            config.db.dialect.driver == "pg8000" and
            config.db.dialect._dbapi_version <= (1, 10, 1)
        )

    @property
    def psycopg2_native_json(self):
        return self.psycopg2_compatibility

    @property
    def psycopg2_native_hstore(self):
        return self.psycopg2_compatibility

    @property
    def psycopg2_compatibility(self):
        return only_on(
            ["postgresql+psycopg2", "postgresql+psycopg2cffi"]
        )

    @property
    def psycopg2_or_pg8000_compatibility(self):
        return only_on(
            ["postgresql+psycopg2", "postgresql+psycopg2cffi",
             "postgresql+pg8000"]
        )

    @property
    def percent_schema_names(self):
        return skip_if(
            [
                (
                    "+psycopg2", None, None,
                    "psycopg2 2.4 no longer accepts percent "
                    "sign in bind placeholders"),
                (
                    "+psycopg2cffi", None, None,
                    "psycopg2cffi does not accept percent signs in "
                    "bind placeholders"),
                ("mysql", None, None, "executemany() doesn't work here")
            ]
        )

    @property
    def order_by_label_with_expression(self):
        return fails_if([
            ('firebird', None, None,
             "kinterbasdb doesn't send full type information"),
            ('postgresql', None, None, 'only simple labels allowed'),
            ('sybase', None, None, 'only simple labels allowed'),
            ('mssql', None, None, 'only simple labels allowed')
        ])

    def get_order_by_collation(self, config):
        lookup = {

            # will raise without quoting
            "postgresql": "POSIX",

            # note MySQL databases need to be created w/ utf8mb3 charset
            # for the test suite
            "mysql": "utf8mb3_bin",
            "sqlite": "NOCASE",

            # will raise *with* quoting
            "mssql": "Latin1_General_CI_AS"
        }
        try:
            return lookup[config.db.name]
        except KeyError:
            raise NotImplementedError()

    @property
    def skip_mysql_on_windows(self):
        """Catchall for a large variety of MySQL on Windows failures"""

        return skip_if(self._has_mysql_on_windows,
                       "Not supported on MySQL + Windows")

    @property
    def mssql_freetds(self):
        return only_on(["mssql+pymssql"])

    @property
    def ad_hoc_engines(self):
        return exclusions.skip_if(
            ["oracle"],
            "works, but Oracle just gets tired with "
            "this much connection activity")

    @property
    def no_mssql_freetds(self):
        return self.mssql_freetds.not_()

    @property
    def pyodbc_fast_executemany(self):
        def has_fastexecutemany(config):
            if not against(config, "mssql+pyodbc"):
                return False
            if config.db.dialect._dbapi_version() < (4, 0, 19):
                return False
            with config.db.connect() as conn:
                drivername = conn.connection.connection.getinfo(
                    config.db.dialect.dbapi.SQL_DRIVER_NAME)
                # on linux this is 'libmsodbcsql-13.1.so.9.2'.
                # don't know what it is on windows
                return "msodbc" in drivername
        return only_if(
            has_fastexecutemany,
            "only on pyodbc > 4.0.19 w/ msodbc driver")

    @property
    def python_fixed_issue_8743(self):
        return exclusions.skip_if(
            lambda: sys.version_info < (2, 7, 8),
            "Python issue 8743 fixed in Python 2.7.8"
        )

    @property
    def selectone(self):
        """target driver must support the literal statement 'select 1'"""
        return skip_if(["oracle", "firebird"],
                       "non-standard SELECT scalar syntax")

    @property
    def mysql_for_update(self):
        return skip_if(
            "mysql+mysqlconnector",
           "lock-sensitive operations crash on mysqlconnector"
        )

    @property
    def mysql_fsp(self):
        return only_if('mysql >= 5.6.4')

    @property
    def mysql_fully_case_sensitive(self):
        return only_if(self._has_mysql_fully_case_sensitive)

    @property
    def mysql_zero_date(self):
        def check(config):
            if not against(config, 'mysql'):
                return False

            row = config.db.execute("show variables like 'sql_mode'").first()
            return not row or "NO_ZERO_DATE" not in row[1]

        return only_if(check)

    @property
    def mysql_non_strict(self):
        def check(config):
            if not against(config, 'mysql'):
                return False

            row = config.db.execute("show variables like 'sql_mode'").first()
            return not row or "STRICT_TRANS_TABLES" not in row[1]

        return only_if(check)

    @property
    def mysql_ngram_fulltext(self):
        def check(config):
            return against(config, "mysql") and \
                not config.db.dialect._is_mariadb and \
                config.db.dialect.server_version_info >= (5, 7)
        return only_if(check)

    def _mariadb_102(self, config):
        return against(config, "mysql") and \
                config.db.dialect._is_mariadb and \
                config.db.dialect._mariadb_normalized_version_info > (10, 2)

    def _mysql_not_mariadb_102(self, config):
        return against(config, "mysql") and (
            not config.db.dialect._is_mariadb or
            config.db.dialect._mariadb_normalized_version_info < (10, 2)
        )

    def _mysql_not_mariadb_103(self, config):
        return against(config, "mysql") and (
            not config.db.dialect._is_mariadb or
            config.db.dialect._mariadb_normalized_version_info < (10, 3)
        )

    def _has_mysql_on_windows(self, config):
        return against(config, 'mysql') and \
                config.db.dialect._detect_casing(config.db) == 1

    def _has_mysql_fully_case_sensitive(self, config):
        return against(config, 'mysql') and \
                config.db.dialect._detect_casing(config.db) == 0

    @property
    def postgresql_utf8_server_encoding(self):
        return only_if(
            lambda config: against(config, 'postgresql') and
            config.db.scalar("show server_encoding").lower() == "utf8"
        )

    @property
    def cxoracle6_or_greater(self):
        return only_if(
            lambda config: against(config, "oracle+cx_oracle") and
            config.db.dialect.cx_oracle_ver >= (6, )
        )

    @property
    def oracle5x(self):
        return only_if(
            lambda config: against(config, "oracle+cx_oracle") and
            config.db.dialect.cx_oracle_ver < (6, )
        )
