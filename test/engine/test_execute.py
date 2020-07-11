# coding: utf-8

from contextlib import contextmanager
import re
import weakref

import sqlalchemy as tsa
from sqlalchemy import bindparam
from sqlalchemy import create_engine
from sqlalchemy import create_mock_engine
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import INT
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy import Sequence
from sqlalchemy import String
from sqlalchemy import testing
from sqlalchemy import text
from sqlalchemy import TypeDecorator
from sqlalchemy import util
from sqlalchemy import VARCHAR
from sqlalchemy.engine import default
from sqlalchemy.engine.base import Connection
from sqlalchemy.engine.base import Engine
from sqlalchemy.sql import column
from sqlalchemy.sql import literal
from sqlalchemy.testing import assert_raises
from sqlalchemy.testing import assert_raises_message
from sqlalchemy.testing import config
from sqlalchemy.testing import engines
from sqlalchemy.testing import eq_
from sqlalchemy.testing import expect_warnings
from sqlalchemy.testing import fixtures
from sqlalchemy.testing import is_
from sqlalchemy.testing import is_false
from sqlalchemy.testing import is_not_
from sqlalchemy.testing import is_true
from sqlalchemy.testing import mock
from sqlalchemy.testing.assertsql import CompiledSQL
from sqlalchemy.testing.engines import testing_engine
from sqlalchemy.testing.mock import call
from sqlalchemy.testing.mock import Mock
from sqlalchemy.testing.mock import patch
from sqlalchemy.testing.schema import Column
from sqlalchemy.testing.schema import Table
from sqlalchemy.testing.util import gc_collect
from sqlalchemy.testing.util import picklers
from sqlalchemy.util import collections_abc


class SomeException(Exception):
    pass


class ExecuteTest(fixtures.TablesTest):
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "users",
            metadata,
            Column("user_id", INT, primary_key=True, autoincrement=False),
            Column("user_name", VARCHAR(20)),
        )
        Table(
            "users_autoinc",
            metadata,
            Column(
                "user_id", INT, primary_key=True, test_needs_autoincrement=True
            ),
            Column("user_name", VARCHAR(20)),
        )

    def test_no_params_option(self):
        stmt = (
            "SELECT '%'"
            + testing.db.dialect.statement_compiler(
                testing.db.dialect, None
            ).default_from()
        )

        conn = testing.db.connect()
        result = (
            conn.execution_options(no_parameters=True)
            .exec_driver_sql(stmt)
            .scalar()
        )
        eq_(result, "%")

    def test_raw_positional_invalid(self, connection):
        assert_raises_message(
            tsa.exc.ArgumentError,
            "List argument must consist only of tuples or dictionaries",
            connection.exec_driver_sql,
            "insert into users (user_id, user_name) " "values (?, ?)",
            [2, "fred"],
        )

        assert_raises_message(
            tsa.exc.ArgumentError,
            "List argument must consist only of tuples or dictionaries",
            connection.exec_driver_sql,
            "insert into users (user_id, user_name) " "values (?, ?)",
            [[3, "ed"], [4, "horse"]],
        )

    def test_raw_named_invalid(self, connection):
        # this is awkward b.c. this is just testing if regular Python
        # is raising TypeError if they happened to send arguments that
        # look like the legacy ones which also happen to conflict with
        # the positional signature for the method.   some combinations
        # can get through and fail differently
        assert_raises(
            TypeError,
            connection.exec_driver_sql,
            "insert into users (user_id, user_name) "
            "values (%(id)s, %(name)s)",
            {"id": 2, "name": "ed"},
            {"id": 3, "name": "horse"},
            {"id": 4, "name": "horse"},
        )
        assert_raises(
            TypeError,
            connection.exec_driver_sql,
            "insert into users (user_id, user_name) "
            "values (%(id)s, %(name)s)",
            id=4,
            name="sally",
        )

    @testing.requires.qmark_paramstyle
    def test_raw_qmark(self, connection):
        conn = connection
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (?, ?)",
            (1, "jack"),
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (?, ?)",
            (2, "fred"),
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (?, ?)",
            [(3, "ed"), (4, "horse")],
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (?, ?)",
            [(5, "barney"), (6, "donkey")],
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (?, ?)",
            (7, "sally"),
        )
        res = conn.exec_driver_sql("select * from users order by user_id")
        assert res.fetchall() == [
            (1, "jack"),
            (2, "fred"),
            (3, "ed"),
            (4, "horse"),
            (5, "barney"),
            (6, "donkey"),
            (7, "sally"),
        ]

        res = conn.exec_driver_sql(
            "select * from users where user_name=?", ("jack",)
        )
        assert res.fetchall() == [(1, "jack")]

    @testing.requires.format_paramstyle
    def test_raw_sprintf(self, connection):
        conn = connection
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (%s, %s)",
            (1, "jack"),
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (%s, %s)",
            [(2, "ed"), (3, "horse")],
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (%s, %s)",
            (4, "sally"),
        )
        conn.exec_driver_sql("insert into users (user_id) values (%s)", (5,))
        res = conn.exec_driver_sql("select * from users order by user_id")
        assert res.fetchall() == [
            (1, "jack"),
            (2, "ed"),
            (3, "horse"),
            (4, "sally"),
            (5, None),
        ]

        res = conn.exec_driver_sql(
            "select * from users where user_name=%s", ("jack",)
        )
        assert res.fetchall() == [(1, "jack")]

    @testing.requires.pyformat_paramstyle
    def test_raw_python(self, connection):
        conn = connection
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) "
            "values (%(id)s, %(name)s)",
            {"id": 1, "name": "jack"},
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) "
            "values (%(id)s, %(name)s)",
            [{"id": 2, "name": "ed"}, {"id": 3, "name": "horse"}],
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) "
            "values (%(id)s, %(name)s)",
            dict(id=4, name="sally"),
        )
        res = conn.exec_driver_sql("select * from users order by user_id")
        assert res.fetchall() == [
            (1, "jack"),
            (2, "ed"),
            (3, "horse"),
            (4, "sally"),
        ]

    @testing.requires.named_paramstyle
    def test_raw_named(self, connection):
        conn = connection
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (:id, :name)",
            {"id": 1, "name": "jack"},
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (:id, :name)",
            [{"id": 2, "name": "ed"}, {"id": 3, "name": "horse"}],
        )
        conn.exec_driver_sql(
            "insert into users (user_id, user_name) " "values (:id, :name)",
            {"id": 4, "name": "sally"},
        )
        res = conn.exec_driver_sql("select * from users order by user_id")
        assert res.fetchall() == [
            (1, "jack"),
            (2, "ed"),
            (3, "horse"),
            (4, "sally"),
        ]

    @testing.engines.close_open_connections
    def test_exception_wrapping_dbapi(self):
        conn = testing.db.connect()
        # engine does not have exec_driver_sql
        assert_raises_message(
            tsa.exc.DBAPIError,
            r"not_a_valid_statement",
            conn.exec_driver_sql,
            "not_a_valid_statement",
        )

    @testing.requires.sqlite
    def test_exception_wrapping_non_dbapi_error(self):
        e = create_engine("sqlite://")
        e.dialect.is_disconnect = is_disconnect = Mock()

        with e.connect() as c:
            c.connection.cursor = Mock(
                return_value=Mock(
                    execute=Mock(
                        side_effect=TypeError("I'm not a DBAPI error")
                    )
                )
            )

            assert_raises_message(
                TypeError,
                "I'm not a DBAPI error",
                c.exec_driver_sql,
                "select ",
            )
            eq_(is_disconnect.call_count, 0)

    def test_exception_wrapping_non_standard_dbapi_error(self):
        class DBAPIError(Exception):
            pass

        class OperationalError(DBAPIError):
            pass

        class NonStandardException(OperationalError):
            pass

        with patch.object(
            testing.db.dialect, "dbapi", Mock(Error=DBAPIError)
        ), patch.object(
            testing.db.dialect, "is_disconnect", lambda *arg: False
        ), patch.object(
            testing.db.dialect,
            "do_execute",
            Mock(side_effect=NonStandardException),
        ):
            with testing.db.connect() as conn:
                assert_raises(
                    tsa.exc.OperationalError, conn.exec_driver_sql, "select 1"
                )

    def test_exception_wrapping_non_dbapi_statement(self):
        class MyType(TypeDecorator):
            impl = Integer

            def process_bind_param(self, value, dialect):
                raise SomeException("nope")

        def _go(conn):
            assert_raises_message(
                tsa.exc.StatementError,
                r"\(.*.SomeException\) " r"nope\n\[SQL\: u?SELECT 1 ",
                conn.execute,
                select(1).where(column("foo") == literal("bar", MyType())),
            )

        with testing.db.connect() as conn:
            _go(conn)

    def test_not_an_executable(self):
        for obj in (
            Table("foo", MetaData(), Column("x", Integer)),
            Column("x", Integer),
            tsa.and_(True),
            tsa.and_(True).compile(),
            column("foo"),
            column("foo").compile(),
            MetaData(),
            Integer(),
            tsa.Index(name="foo"),
            tsa.UniqueConstraint("x"),
        ):
            with testing.db.connect() as conn:
                assert_raises_message(
                    tsa.exc.ObjectNotExecutableError,
                    "Not an executable object",
                    conn.execute,
                    obj,
                )

    def test_stmt_exception_bytestring_raised(self):
        name = util.u("méil")
        with testing.db.connect() as conn:
            assert_raises_message(
                tsa.exc.StatementError,
                util.u(
                    "A value is required for bind parameter 'uname'\n"
                    r".*SELECT users.user_name AS .m\xe9il."
                )
                if util.py2k
                else util.u(
                    "A value is required for bind parameter 'uname'\n"
                    ".*SELECT users.user_name AS .méil."
                ),
                conn.execute,
                select(users.c.user_name.label(name)).where(
                    users.c.user_name == bindparam("uname")
                ),
                {"uname_incorrect": "foo"},
            )

    def test_stmt_exception_bytestring_utf8(self):
        # uncommon case for Py3K, bytestring object passed
        # as the error message
        message = util.u("some message méil").encode("utf-8")

        err = tsa.exc.SQLAlchemyError(message)
        if util.py2k:
            # string passes it through
            eq_(str(err), message)

            # unicode accessor decodes to utf-8
            eq_(unicode(err), util.u("some message méil"))  # noqa
        else:
            eq_(str(err), util.u("some message méil"))

    def test_stmt_exception_bytestring_latin1(self):
        # uncommon case for Py3K, bytestring object passed
        # as the error message
        message = util.u("some message méil").encode("latin-1")

        err = tsa.exc.SQLAlchemyError(message)
        if util.py2k:
            # string passes it through
            eq_(str(err), message)

            # unicode accessor decodes to utf-8
            eq_(unicode(err), util.u("some message m\\xe9il"))  # noqa
        else:
            eq_(str(err), util.u("some message m\\xe9il"))

    def test_stmt_exception_unicode_hook_unicode(self):
        # uncommon case for Py2K, Unicode object passed
        # as the error message
        message = util.u("some message méil")

        err = tsa.exc.SQLAlchemyError(message)
        if util.py2k:
            eq_(unicode(err), util.u("some message méil"))  # noqa
        else:
            eq_(str(err), util.u("some message méil"))

    def test_stmt_exception_str_multi_args(self):
        err = tsa.exc.SQLAlchemyError("some message", 206)
        eq_(str(err), "('some message', 206)")

    def test_stmt_exception_str_multi_args_bytestring(self):
        message = util.u("some message méil").encode("utf-8")

        err = tsa.exc.SQLAlchemyError(message, 206)
        eq_(str(err), str((message, 206)))

    def test_stmt_exception_str_multi_args_unicode(self):
        message = util.u("some message méil")

        err = tsa.exc.SQLAlchemyError(message, 206)
        eq_(str(err), str((message, 206)))

    def test_stmt_exception_pickleable_no_dbapi(self):
        self._test_stmt_exception_pickleable(Exception("hello world"))

    @testing.crashes(
        "postgresql+psycopg2",
        "Older versions don't support cursor pickling, newer ones do",
    )
    @testing.fails_on(
        "mysql+oursql",
        "Exception doesn't come back exactly the same from pickle",
    )
    @testing.fails_on(
        "mysql+mysqlconnector",
        "Exception doesn't come back exactly the same from pickle",
    )
    @testing.fails_on(
        "oracle+cx_oracle",
        "cx_oracle exception seems to be having " "some issue with pickling",
    )
    def test_stmt_exception_pickleable_plus_dbapi(self):
        raw = testing.db.raw_connection()
        the_orig = None
        try:
            try:
                cursor = raw.cursor()
                cursor.execute("SELECTINCORRECT")
            except testing.db.dialect.dbapi.DatabaseError as orig:
                # py3k has "orig" in local scope...
                the_orig = orig
        finally:
            raw.close()
        self._test_stmt_exception_pickleable(the_orig)

    def _test_stmt_exception_pickleable(self, orig):
        for sa_exc in (
            tsa.exc.StatementError(
                "some error",
                "select * from table",
                {"foo": "bar"},
                orig,
                False,
            ),
            tsa.exc.InterfaceError(
                "select * from table", {"foo": "bar"}, orig, True
            ),
            tsa.exc.NoReferencedTableError("message", "tname"),
            tsa.exc.NoReferencedColumnError("message", "tname", "cname"),
            tsa.exc.CircularDependencyError(
                "some message", [1, 2, 3], [(1, 2), (3, 4)]
            ),
        ):
            for loads, dumps in picklers():
                repickled = loads(dumps(sa_exc))
                eq_(repickled.args[0], sa_exc.args[0])
                if isinstance(sa_exc, tsa.exc.StatementError):
                    eq_(repickled.params, {"foo": "bar"})
                    eq_(repickled.statement, sa_exc.statement)
                    if hasattr(sa_exc, "connection_invalidated"):
                        eq_(
                            repickled.connection_invalidated,
                            sa_exc.connection_invalidated,
                        )
                    eq_(repickled.orig.args[0], orig.args[0])

    def test_dont_wrap_mixin(self):
        class MyException(Exception, tsa.exc.DontWrapMixin):
            pass

        class MyType(TypeDecorator):
            impl = Integer

            def process_bind_param(self, value, dialect):
                raise MyException("nope")

        def _go(conn):
            assert_raises_message(
                MyException,
                "nope",
                conn.execute,
                select(1).where(column("foo") == literal("bar", MyType())),
            )

        conn = testing.db.connect()
        try:
            _go(conn)
        finally:
            conn.close()

    def test_empty_insert(self, connection):
        """test that execute() interprets [] as a list with no params"""
        users_autoinc = self.tables.users_autoinc

        connection.execute(
            users_autoinc.insert().values(user_name=bindparam("name", None)),
            [],
        )
        eq_(connection.execute(users_autoinc.select()).fetchall(), [(1, None)])

    @testing.only_on("sqlite")
    def test_execute_compiled_favors_compiled_paramstyle(self):
        with patch.object(testing.db.dialect, "do_execute") as do_exec:
            stmt = users.update().values(user_id=1, user_name="foo")

            d1 = default.DefaultDialect(paramstyle="format")
            d2 = default.DefaultDialect(paramstyle="pyformat")

            with testing.db.connect() as conn:
                conn.execute(stmt.compile(dialect=d1))
                conn.execute(stmt.compile(dialect=d2))

            eq_(
                do_exec.mock_calls,
                [
                    call(
                        mock.ANY,
                        "UPDATE users SET user_id=%s, user_name=%s",
                        (1, "foo"),
                        mock.ANY,
                    ),
                    call(
                        mock.ANY,
                        "UPDATE users SET user_id=%(user_id)s, "
                        "user_name=%(user_name)s",
                        {"user_name": "foo", "user_id": 1},
                        mock.ANY,
                    ),
                ],
            )

    @testing.requires.ad_hoc_engines
    def test_engine_level_options(self):
        eng = engines.testing_engine(
            options={"execution_options": {"foo": "bar"}}
        )
        with eng.connect() as conn:
            eq_(conn._execution_options["foo"], "bar")
            eq_(
                conn.execution_options(bat="hoho")._execution_options["foo"],
                "bar",
            )
            eq_(
                conn.execution_options(bat="hoho")._execution_options["bat"],
                "hoho",
            )
            eq_(
                conn.execution_options(foo="hoho")._execution_options["foo"],
                "hoho",
            )
            eng.update_execution_options(foo="hoho")
            conn = eng.connect()
            eq_(conn._execution_options["foo"], "hoho")

    @testing.requires.ad_hoc_engines
    def test_generative_engine_execution_options(self):
        eng = engines.testing_engine(
            options={"execution_options": {"base": "x1"}}
        )

        is_(eng.engine, eng)

        eng1 = eng.execution_options(foo="b1")
        is_(eng1.engine, eng1)
        eng2 = eng.execution_options(foo="b2")
        eng1a = eng1.execution_options(bar="a1")
        eng2a = eng2.execution_options(foo="b3", bar="a2")
        is_(eng2a.engine, eng2a)

        eq_(eng._execution_options, {"base": "x1"})
        eq_(eng1._execution_options, {"base": "x1", "foo": "b1"})
        eq_(eng2._execution_options, {"base": "x1", "foo": "b2"})
        eq_(eng1a._execution_options, {"base": "x1", "foo": "b1", "bar": "a1"})
        eq_(eng2a._execution_options, {"base": "x1", "foo": "b3", "bar": "a2"})
        is_(eng1a.pool, eng.pool)

        # test pool is shared
        eng2.dispose()
        is_(eng1a.pool, eng2.pool)
        is_(eng.pool, eng2.pool)

    @testing.requires.ad_hoc_engines
    def test_autocommit_option_no_issue_first_connect(self):
        eng = create_engine(testing.db.url)
        eng.update_execution_options(autocommit=True)
        conn = eng.connect()
        eq_(conn._execution_options, {"autocommit": True})
        conn.close()

    def test_initialize_rollback(self):
        """test a rollback happens during first connect"""
        eng = create_engine(testing.db.url)
        with patch.object(eng.dialect, "do_rollback") as do_rollback:
            assert do_rollback.call_count == 0
            connection = eng.connect()
            assert do_rollback.call_count == 1
        connection.close()

    @testing.requires.ad_hoc_engines
    def test_dialect_init_uses_options(self):
        eng = create_engine(testing.db.url)

        def my_init(connection):
            connection.execution_options(foo="bar").execute(select(1))

        with patch.object(eng.dialect, "initialize", my_init):
            conn = eng.connect()
            eq_(conn._execution_options, {})
            conn.close()

    @testing.requires.ad_hoc_engines
    def test_generative_engine_event_dispatch_hasevents(self):
        def l1(*arg, **kw):
            pass

        eng = create_engine(testing.db.url)
        assert not eng._has_events
        event.listen(eng, "before_execute", l1)
        eng2 = eng.execution_options(foo="bar")
        assert eng2._has_events

    def test_works_after_dispose(self):
        eng = create_engine(testing.db.url)
        for i in range(3):
            with eng.connect() as conn:
                eq_(conn.scalar(select(1)), 1)
            eng.dispose()

    def test_works_after_dispose_testing_engine(self):
        eng = engines.testing_engine()
        for i in range(3):
            with eng.connect() as conn:
                eq_(conn.scalar(select(1)), 1)
            eng.dispose()


class UnicodeReturnsTest(fixtures.TestBase):
    @testing.requires.python3
    def test_unicode_test_not_in_python3(self):
        eng = engines.testing_engine()
        eng.dialect.returns_unicode_strings = String.RETURNS_UNKNOWN

        assert_raises_message(
            tsa.exc.InvalidRequestError,
            "RETURNS_UNKNOWN is unsupported in Python 3",
            eng.connect,
        )

    @testing.requires.python2
    def test_unicode_test_fails_warning(self):
        class MockCursor(engines.DBAPIProxyCursor):
            def execute(self, stmt, params=None, **kw):
                if "test unicode returns" in stmt:
                    raise self.engine.dialect.dbapi.DatabaseError("boom")
                else:
                    return super(MockCursor, self).execute(stmt, params, **kw)

        eng = engines.proxying_engine(cursor_cls=MockCursor)
        with testing.expect_warnings(
            "Exception attempting to detect unicode returns"
        ):
            eng.connect()

        # because plain varchar passed, we don't know the correct answer
        eq_(eng.dialect.returns_unicode_strings, String.RETURNS_CONDITIONAL)
        eng.dispose()


class ConvenienceExecuteTest(fixtures.TablesTest):
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        cls.table = Table(
            "exec_test",
            metadata,
            Column("a", Integer),
            Column("b", Integer),
            test_needs_acid=True,
        )

    def _trans_fn(self, is_transaction=False):
        def go(conn, x, value=None):
            if is_transaction:
                conn = conn.connection
            conn.execute(self.table.insert().values(a=x, b=value))

        return go

    def _trans_rollback_fn(self, is_transaction=False):
        def go(conn, x, value=None):
            if is_transaction:
                conn = conn.connection
            conn.execute(self.table.insert().values(a=x, b=value))
            raise SomeException("breakage")

        return go

    def _assert_no_data(self):
        with testing.db.connect() as conn:
            eq_(
                conn.scalar(select(func.count("*")).select_from(self.table)),
                0,
            )

    def _assert_fn(self, x, value=None):
        with testing.db.connect() as conn:
            eq_(conn.execute(self.table.select()).fetchall(), [(x, value)])

    def test_transaction_engine_ctx_commit(self):
        fn = self._trans_fn()
        ctx = testing.db.begin()
        testing.run_as_contextmanager(ctx, fn, 5, value=8)
        self._assert_fn(5, value=8)

    def test_transaction_engine_ctx_begin_fails(self):
        engine = engines.testing_engine()

        mock_connection = Mock(
            return_value=Mock(begin=Mock(side_effect=Exception("boom")))
        )
        engine._connection_cls = mock_connection
        assert_raises(Exception, engine.begin)

        eq_(mock_connection.return_value.close.mock_calls, [call()])

    def test_transaction_engine_ctx_rollback(self):
        fn = self._trans_rollback_fn()
        ctx = testing.db.begin()
        assert_raises_message(
            Exception,
            "breakage",
            testing.run_as_contextmanager,
            ctx,
            fn,
            5,
            value=8,
        )
        self._assert_no_data()

    def test_transaction_connection_ctx_commit(self):
        fn = self._trans_fn(True)
        with testing.db.connect() as conn:
            ctx = conn.begin()
            testing.run_as_contextmanager(ctx, fn, 5, value=8)
            self._assert_fn(5, value=8)

    def test_transaction_connection_ctx_rollback(self):
        fn = self._trans_rollback_fn(True)
        with testing.db.connect() as conn:
            ctx = conn.begin()
            assert_raises_message(
                Exception,
                "breakage",
                testing.run_as_contextmanager,
                ctx,
                fn,
                5,
                value=8,
            )
            self._assert_no_data()

    def test_connection_as_ctx(self):
        fn = self._trans_fn()
        ctx = testing.db.connect()
        testing.run_as_contextmanager(ctx, fn, 5, value=8)
        # autocommit is on
        self._assert_fn(5, value=8)

    @testing.fails_on("mysql+oursql", "oursql bug ?  getting wrong rowcount")
    def test_connect_as_ctx_noautocommit(self):
        fn = self._trans_fn()
        self._assert_no_data()

        with testing.db.connect() as conn:
            ctx = conn.execution_options(autocommit=False)
            testing.run_as_contextmanager(ctx, fn, 5, value=8)
            # autocommit is off
            self._assert_no_data()


class CompiledCacheTest(fixtures.TestBase):
    __backend__ = True

    @classmethod
    def setup_class(cls):
        global users, metadata
        metadata = MetaData(testing.db)
        users = Table(
            "users",
            metadata,
            Column(
                "user_id", INT, primary_key=True, test_needs_autoincrement=True
            ),
            Column("user_name", VARCHAR(20)),
            Column("extra_data", VARCHAR(20)),
        )
        metadata.create_all()

    @engines.close_first
    def teardown(self):
        with testing.db.connect() as conn:
            conn.execute(users.delete())

    @classmethod
    def teardown_class(cls):
        metadata.drop_all()

    def test_cache(self):
        conn = testing.db.connect()
        cache = {}
        cached_conn = conn.execution_options(compiled_cache=cache)

        ins = users.insert()
        with patch.object(
            ins, "_compiler", Mock(side_effect=ins._compiler)
        ) as compile_mock:
            cached_conn.execute(ins, {"user_name": "u1"})
            cached_conn.execute(ins, {"user_name": "u2"})
            cached_conn.execute(ins, {"user_name": "u3"})
        eq_(compile_mock.call_count, 1)
        assert len(cache) == 1
        eq_(conn.exec_driver_sql("select count(*) from users").scalar(), 3)

    @testing.only_on(
        ["sqlite", "mysql", "postgresql"],
        "uses blob value that is problematic for some DBAPIs",
    )
    @testing.provide_metadata
    def test_cache_noleak_on_statement_values(self):
        # This is a non regression test for an object reference leak caused
        # by the compiled_cache.

        metadata = self.metadata
        photo = Table(
            "photo",
            metadata,
            Column(
                "id", Integer, primary_key=True, test_needs_autoincrement=True
            ),
            Column("photo_blob", LargeBinary()),
        )
        metadata.create_all()

        conn = testing.db.connect()
        cache = {}
        cached_conn = conn.execution_options(compiled_cache=cache)

        class PhotoBlob(bytearray):
            pass

        blob = PhotoBlob(100)
        ref_blob = weakref.ref(blob)

        ins = photo.insert()
        with patch.object(
            ins, "_compiler", Mock(side_effect=ins._compiler)
        ) as compile_mock:
            cached_conn.execute(ins, {"photo_blob": blob})
        eq_(compile_mock.call_count, 1)
        eq_(len(cache), 1)
        eq_(conn.exec_driver_sql("select count(*) from photo").scalar(), 1)

        del blob

        gc_collect()

        # The compiled statement cache should not hold any reference to the
        # the statement values (only the keys).
        eq_(ref_blob(), None)

    def test_keys_independent_of_ordering(self):
        conn = testing.db.connect()
        conn.execute(
            users.insert(),
            {"user_id": 1, "user_name": "u1", "extra_data": "e1"},
        )
        cache = {}
        cached_conn = conn.execution_options(compiled_cache=cache)

        upd = users.update().where(users.c.user_id == bindparam("b_user_id"))

        with patch.object(
            upd, "_compiler", Mock(side_effect=upd._compiler)
        ) as compile_mock:
            cached_conn.execute(
                upd,
                util.OrderedDict(
                    [
                        ("b_user_id", 1),
                        ("user_name", "u2"),
                        ("extra_data", "e2"),
                    ]
                ),
            )
            cached_conn.execute(
                upd,
                util.OrderedDict(
                    [
                        ("b_user_id", 1),
                        ("extra_data", "e3"),
                        ("user_name", "u3"),
                    ]
                ),
            )
            cached_conn.execute(
                upd,
                util.OrderedDict(
                    [
                        ("extra_data", "e4"),
                        ("user_name", "u4"),
                        ("b_user_id", 1),
                    ]
                ),
            )
        eq_(compile_mock.call_count, 1)
        eq_(len(cache), 1)

    @testing.requires.schemas
    @testing.provide_metadata
    def test_schema_translate_in_key(self):
        Table("x", self.metadata, Column("q", Integer))
        Table(
            "x", self.metadata, Column("q", Integer), schema=config.test_schema
        )
        self.metadata.create_all()

        m = MetaData()
        t1 = Table("x", m, Column("q", Integer))
        ins = t1.insert()
        stmt = select(t1.c.q)

        cache = {}
        with config.db.connect().execution_options(
            compiled_cache=cache
        ) as conn:
            conn.execute(ins, {"q": 1})
            eq_(conn.scalar(stmt), 1)

        with config.db.connect().execution_options(
            compiled_cache=cache,
            schema_translate_map={None: config.test_schema},
        ) as conn:
            conn.execute(ins, {"q": 2})
            eq_(conn.scalar(stmt), 2)

        with config.db.connect().execution_options(
            compiled_cache=cache, schema_translate_map={None: None},
        ) as conn:
            # should use default schema again even though statement
            # was compiled with test_schema in the map
            eq_(conn.scalar(stmt), 1)

        with config.db.connect().execution_options(
            compiled_cache=cache
        ) as conn:
            eq_(conn.scalar(stmt), 1)


class MockStrategyTest(fixtures.TestBase):
    def _engine_fixture(self):
        buf = util.StringIO()

        def dump(sql, *multiparams, **params):
            buf.write(util.text_type(sql.compile(dialect=engine.dialect)))

        engine = create_mock_engine("postgresql://", executor=dump)
        return engine, buf

    def test_sequence_not_duped(self):
        engine, buf = self._engine_fixture()
        metadata = MetaData()
        t = Table(
            "testtable",
            metadata,
            Column(
                "pk", Integer, Sequence("testtable_pk_seq"), primary_key=True,
            ),
        )

        t.create(engine)
        t.drop(engine)

        eq_(re.findall(r"CREATE (\w+)", buf.getvalue()), ["SEQUENCE", "TABLE"])

        eq_(re.findall(r"DROP (\w+)", buf.getvalue()), ["TABLE", "SEQUENCE"])


class SchemaTranslateTest(fixtures.TestBase, testing.AssertsExecutionResults):
    __requires__ = ("schemas",)
    __backend__ = True

    def test_create_table(self):
        map_ = {
            None: config.test_schema,
            "foo": config.test_schema,
            "bar": None,
        }

        metadata = MetaData()
        t1 = Table("t1", metadata, Column("x", Integer))
        t2 = Table("t2", metadata, Column("x", Integer), schema="foo")
        t3 = Table("t3", metadata, Column("x", Integer), schema="bar")

        with self.sql_execution_asserter(config.db) as asserter:
            with config.db.connect().execution_options(
                schema_translate_map=map_
            ) as conn:

                t1.create(conn)
                t2.create(conn)
                t3.create(conn)

                t3.drop(conn)
                t2.drop(conn)
                t1.drop(conn)

        asserter.assert_(
            CompiledSQL("CREATE TABLE [SCHEMA__none].t1 (x INTEGER)"),
            CompiledSQL("CREATE TABLE [SCHEMA_foo].t2 (x INTEGER)"),
            CompiledSQL("CREATE TABLE [SCHEMA_bar].t3 (x INTEGER)"),
            CompiledSQL("DROP TABLE [SCHEMA_bar].t3"),
            CompiledSQL("DROP TABLE [SCHEMA_foo].t2"),
            CompiledSQL("DROP TABLE [SCHEMA__none].t1"),
        )

    def _fixture(self):
        metadata = self.metadata
        Table("t1", metadata, Column("x", Integer), schema=config.test_schema)
        Table("t2", metadata, Column("x", Integer), schema=config.test_schema)
        Table("t3", metadata, Column("x", Integer), schema=None)
        metadata.create_all()

    def test_ddl_hastable(self):

        map_ = {
            None: config.test_schema,
            "foo": config.test_schema,
            "bar": None,
        }

        metadata = MetaData()
        Table("t1", metadata, Column("x", Integer))
        Table("t2", metadata, Column("x", Integer), schema="foo")
        Table("t3", metadata, Column("x", Integer), schema="bar")

        with config.db.connect().execution_options(
            schema_translate_map=map_
        ) as conn:
            metadata.create_all(conn)

        insp = inspect(config.db)
        is_true(insp.has_table("t1", schema=config.test_schema))
        is_true(insp.has_table("t2", schema=config.test_schema))
        is_true(insp.has_table("t3", schema=None))

        with config.db.connect().execution_options(
            schema_translate_map=map_
        ) as conn:
            metadata.drop_all(conn)

        insp = inspect(config.db)
        is_false(insp.has_table("t1", schema=config.test_schema))
        is_false(insp.has_table("t2", schema=config.test_schema))
        is_false(insp.has_table("t3", schema=None))

    @testing.provide_metadata
    def test_option_on_execute(self):
        self._fixture()

        map_ = {
            None: config.test_schema,
            "foo": config.test_schema,
            "bar": None,
        }

        metadata = MetaData()
        t1 = Table("t1", metadata, Column("x", Integer))
        t2 = Table("t2", metadata, Column("x", Integer), schema="foo")
        t3 = Table("t3", metadata, Column("x", Integer), schema="bar")

        with self.sql_execution_asserter(config.db) as asserter:
            with config.db.connect() as conn:

                execution_options = {"schema_translate_map": map_}
                conn._execute_20(
                    t1.insert(), {"x": 1}, execution_options=execution_options
                )
                conn._execute_20(
                    t2.insert(), {"x": 1}, execution_options=execution_options
                )
                conn._execute_20(
                    t3.insert(), {"x": 1}, execution_options=execution_options
                )

                conn._execute_20(
                    t1.update().values(x=1).where(t1.c.x == 1),
                    execution_options=execution_options,
                )
                conn._execute_20(
                    t2.update().values(x=2).where(t2.c.x == 1),
                    execution_options=execution_options,
                )
                conn._execute_20(
                    t3.update().values(x=3).where(t3.c.x == 1),
                    execution_options=execution_options,
                )

                eq_(
                    conn._execute_20(
                        select(t1.c.x), execution_options=execution_options
                    ).scalar(),
                    1,
                )
                eq_(
                    conn._execute_20(
                        select(t2.c.x), execution_options=execution_options
                    ).scalar(),
                    2,
                )
                eq_(
                    conn._execute_20(
                        select(t3.c.x), execution_options=execution_options
                    ).scalar(),
                    3,
                )

                conn._execute_20(
                    t1.delete(), execution_options=execution_options
                )
                conn._execute_20(
                    t2.delete(), execution_options=execution_options
                )
                conn._execute_20(
                    t3.delete(), execution_options=execution_options
                )

        asserter.assert_(
            CompiledSQL("INSERT INTO [SCHEMA__none].t1 (x) VALUES (:x)"),
            CompiledSQL("INSERT INTO [SCHEMA_foo].t2 (x) VALUES (:x)"),
            CompiledSQL("INSERT INTO [SCHEMA_bar].t3 (x) VALUES (:x)"),
            CompiledSQL(
                "UPDATE [SCHEMA__none].t1 SET x=:x WHERE "
                "[SCHEMA__none].t1.x = :x_1"
            ),
            CompiledSQL(
                "UPDATE [SCHEMA_foo].t2 SET x=:x WHERE "
                "[SCHEMA_foo].t2.x = :x_1"
            ),
            CompiledSQL(
                "UPDATE [SCHEMA_bar].t3 SET x=:x WHERE "
                "[SCHEMA_bar].t3.x = :x_1"
            ),
            CompiledSQL("SELECT [SCHEMA__none].t1.x FROM [SCHEMA__none].t1"),
            CompiledSQL("SELECT [SCHEMA_foo].t2.x FROM [SCHEMA_foo].t2"),
            CompiledSQL("SELECT [SCHEMA_bar].t3.x FROM [SCHEMA_bar].t3"),
            CompiledSQL("DELETE FROM [SCHEMA__none].t1"),
            CompiledSQL("DELETE FROM [SCHEMA_foo].t2"),
            CompiledSQL("DELETE FROM [SCHEMA_bar].t3"),
        )

    @testing.provide_metadata
    def test_crud(self):
        self._fixture()

        map_ = {
            None: config.test_schema,
            "foo": config.test_schema,
            "bar": None,
        }

        metadata = MetaData()
        t1 = Table("t1", metadata, Column("x", Integer))
        t2 = Table("t2", metadata, Column("x", Integer), schema="foo")
        t3 = Table("t3", metadata, Column("x", Integer), schema="bar")

        with self.sql_execution_asserter(config.db) as asserter:
            with config.db.connect().execution_options(
                schema_translate_map=map_
            ) as conn:

                conn.execute(t1.insert(), {"x": 1})
                conn.execute(t2.insert(), {"x": 1})
                conn.execute(t3.insert(), {"x": 1})

                conn.execute(t1.update().values(x=1).where(t1.c.x == 1))
                conn.execute(t2.update().values(x=2).where(t2.c.x == 1))
                conn.execute(t3.update().values(x=3).where(t3.c.x == 1))

                eq_(conn.scalar(select(t1.c.x)), 1)
                eq_(conn.scalar(select(t2.c.x)), 2)
                eq_(conn.scalar(select(t3.c.x)), 3)

                conn.execute(t1.delete())
                conn.execute(t2.delete())
                conn.execute(t3.delete())

        asserter.assert_(
            CompiledSQL("INSERT INTO [SCHEMA__none].t1 (x) VALUES (:x)"),
            CompiledSQL("INSERT INTO [SCHEMA_foo].t2 (x) VALUES (:x)"),
            CompiledSQL("INSERT INTO [SCHEMA_bar].t3 (x) VALUES (:x)"),
            CompiledSQL(
                "UPDATE [SCHEMA__none].t1 SET x=:x WHERE "
                "[SCHEMA__none].t1.x = :x_1"
            ),
            CompiledSQL(
                "UPDATE [SCHEMA_foo].t2 SET x=:x WHERE "
                "[SCHEMA_foo].t2.x = :x_1"
            ),
            CompiledSQL(
                "UPDATE [SCHEMA_bar].t3 SET x=:x WHERE "
                "[SCHEMA_bar].t3.x = :x_1"
            ),
            CompiledSQL("SELECT [SCHEMA__none].t1.x FROM [SCHEMA__none].t1"),
            CompiledSQL("SELECT [SCHEMA_foo].t2.x FROM [SCHEMA_foo].t2"),
            CompiledSQL("SELECT [SCHEMA_bar].t3.x FROM [SCHEMA_bar].t3"),
            CompiledSQL("DELETE FROM [SCHEMA__none].t1"),
            CompiledSQL("DELETE FROM [SCHEMA_foo].t2"),
            CompiledSQL("DELETE FROM [SCHEMA_bar].t3"),
        )

    @testing.provide_metadata
    def test_via_engine(self):
        self._fixture()

        map_ = {
            None: config.test_schema,
            "foo": config.test_schema,
            "bar": None,
        }

        metadata = MetaData()
        t2 = Table("t2", metadata, Column("x", Integer), schema="foo")

        with self.sql_execution_asserter(config.db) as asserter:
            eng = config.db.execution_options(schema_translate_map=map_)
            conn = eng.connect()
            conn.execute(select(t2.c.x))
        asserter.assert_(
            CompiledSQL("SELECT [SCHEMA_foo].t2.x FROM [SCHEMA_foo].t2")
        )


class ExecutionOptionsTest(fixtures.TestBase):
    def test_dialect_conn_options(self):
        engine = testing_engine("sqlite://", options=dict(_initialize=False))
        engine.dialect = Mock()
        conn = engine.connect()
        c2 = conn.execution_options(foo="bar")
        eq_(
            engine.dialect.set_connection_execution_options.mock_calls,
            [call(c2, {"foo": "bar"})],
        )

    def test_dialect_engine_options(self):
        engine = testing_engine("sqlite://")
        engine.dialect = Mock()
        e2 = engine.execution_options(foo="bar")
        eq_(
            engine.dialect.set_engine_execution_options.mock_calls,
            [call(e2, {"foo": "bar"})],
        )

    def test_dialect_engine_construction_options(self):
        dialect = Mock()
        engine = Engine(
            Mock(), dialect, Mock(), execution_options={"foo": "bar"}
        )
        eq_(
            dialect.set_engine_execution_options.mock_calls,
            [call(engine, {"foo": "bar"})],
        )

    def test_propagate_engine_to_connection(self):
        engine = testing_engine(
            "sqlite://", options=dict(execution_options={"foo": "bar"})
        )
        conn = engine.connect()
        eq_(conn._execution_options, {"foo": "bar"})

    def test_propagate_option_engine_to_connection(self):
        e1 = testing_engine(
            "sqlite://", options=dict(execution_options={"foo": "bar"})
        )
        e2 = e1.execution_options(bat="hoho")
        c1 = e1.connect()
        c2 = e2.connect()
        eq_(c1._execution_options, {"foo": "bar"})
        eq_(c2._execution_options, {"foo": "bar", "bat": "hoho"})

    def test_get_engine_execution_options(self):
        engine = testing_engine("sqlite://")
        engine.dialect = Mock()
        e2 = engine.execution_options(foo="bar")

        eq_(e2.get_execution_options(), {"foo": "bar"})

    def test_get_connection_execution_options(self):
        engine = testing_engine("sqlite://", options=dict(_initialize=False))
        engine.dialect = Mock()
        conn = engine.connect()
        c = conn.execution_options(foo="bar")

        eq_(c.get_execution_options(), {"foo": "bar"})


class EngineEventsTest(fixtures.TestBase):
    __requires__ = ("ad_hoc_engines",)
    __backend__ = True

    def tearDown(self):
        Engine.dispatch._clear()
        Engine._has_events = False

    def _assert_stmts(self, expected, received):
        list(received)

        for stmt, params, posn in expected:
            if not received:
                assert False, "Nothing available for stmt: %s" % stmt
            while received:
                teststmt, testparams, testmultiparams = received.pop(0)
                teststmt = (
                    re.compile(r"[\n\t ]+", re.M).sub(" ", teststmt).strip()
                )
                if teststmt.startswith(stmt) and (
                    testparams == params or testparams == posn
                ):
                    break

    def test_per_engine_independence(self):
        e1 = testing_engine(config.db_url)
        e2 = testing_engine(config.db_url)

        canary = Mock()
        event.listen(e1, "before_execute", canary)
        s1 = select(1)
        s2 = select(2)

        with e1.connect() as conn:
            conn.execute(s1)

        with e2.connect() as conn:
            conn.execute(s2)
        eq_([arg[1][1] for arg in canary.mock_calls], [s1])
        event.listen(e2, "before_execute", canary)

        with e1.connect() as conn:
            conn.execute(s1)

        with e2.connect() as conn:
            conn.execute(s2)
        eq_([arg[1][1] for arg in canary.mock_calls], [s1, s1, s2])

    def test_per_engine_plus_global(self):
        canary = Mock()
        event.listen(Engine, "before_execute", canary.be1)
        e1 = testing_engine(config.db_url)
        e2 = testing_engine(config.db_url)

        event.listen(e1, "before_execute", canary.be2)

        event.listen(Engine, "before_execute", canary.be3)
        e1.connect()
        e2.connect()

        with e1.connect() as conn:
            conn.execute(select(1))
        eq_(canary.be1.call_count, 1)
        eq_(canary.be2.call_count, 1)

        with e2.connect() as conn:
            conn.execute(select(1))

        eq_(canary.be1.call_count, 2)
        eq_(canary.be2.call_count, 1)
        eq_(canary.be3.call_count, 2)

    def test_per_connection_plus_engine(self):
        canary = Mock()
        e1 = testing_engine(config.db_url)

        event.listen(e1, "before_execute", canary.be1)

        conn = e1.connect()
        event.listen(conn, "before_execute", canary.be2)
        conn.execute(select(1))

        eq_(canary.be1.call_count, 1)
        eq_(canary.be2.call_count, 1)

        if testing.requires.legacy_engine.enabled:
            conn._branch().execute(select(1))
            eq_(canary.be1.call_count, 2)
            eq_(canary.be2.call_count, 2)

    def test_add_event_after_connect(self):
        # new feature as of #2978
        canary = Mock()
        e1 = create_engine(config.db_url)
        assert not e1._has_events

        conn = e1.connect()

        event.listen(e1, "before_execute", canary.be1)
        conn.execute(select(1))

        eq_(canary.be1.call_count, 1)

        conn._branch().execute(select(1))
        eq_(canary.be1.call_count, 2)

    def test_force_conn_events_false(self):
        canary = Mock()
        e1 = create_engine(config.db_url)
        assert not e1._has_events

        event.listen(e1, "before_execute", canary.be1)

        conn = e1._connection_cls(
            e1, connection=e1.raw_connection(), _has_events=False
        )

        conn.execute(select(1))

        eq_(canary.be1.call_count, 0)

        conn._branch().execute(select(1))
        eq_(canary.be1.call_count, 0)

    def test_cursor_events_ctx_execute_scalar(self):
        canary = Mock()
        e1 = testing_engine(config.db_url)

        event.listen(e1, "before_cursor_execute", canary.bce)
        event.listen(e1, "after_cursor_execute", canary.ace)

        stmt = str(select(1).compile(dialect=e1.dialect))

        with e1.connect() as conn:
            dialect = conn.dialect

            ctx = dialect.execution_ctx_cls._init_statement(
                dialect, conn, conn.connection, {}, stmt, {}
            )

            ctx._execute_scalar(stmt, Integer())

        eq_(
            canary.bce.mock_calls,
            [call(conn, ctx.cursor, stmt, ctx.parameters[0], ctx, False)],
        )
        eq_(
            canary.ace.mock_calls,
            [call(conn, ctx.cursor, stmt, ctx.parameters[0], ctx, False)],
        )

    def test_cursor_events_execute(self):
        canary = Mock()
        e1 = testing_engine(config.db_url)

        event.listen(e1, "before_cursor_execute", canary.bce)
        event.listen(e1, "after_cursor_execute", canary.ace)

        stmt = str(select(1).compile(dialect=e1.dialect))

        with e1.connect() as conn:

            result = conn.exec_driver_sql(stmt)

        ctx = result.context
        eq_(
            canary.bce.mock_calls,
            [call(conn, ctx.cursor, stmt, ctx.parameters[0], ctx, False)],
        )
        eq_(
            canary.ace.mock_calls,
            [call(conn, ctx.cursor, stmt, ctx.parameters[0], ctx, False)],
        )

    def test_argument_format_execute(self):
        def before_execute(
            conn, clauseelement, multiparams, params, execution_options
        ):
            assert isinstance(multiparams, (list, tuple))
            assert isinstance(params, collections_abc.Mapping)

        def after_execute(
            conn, clauseelement, multiparams, params, result, execution_options
        ):
            assert isinstance(multiparams, (list, tuple))
            assert isinstance(params, collections_abc.Mapping)

        e1 = testing_engine(config.db_url)
        event.listen(e1, "before_execute", before_execute)
        event.listen(e1, "after_execute", after_execute)

        with e1.connect() as conn:
            conn.execute(select(1))
            conn.execute(select(1).compile(dialect=e1.dialect).statement)
            conn.execute(select(1).compile(dialect=e1.dialect))

            conn._execute_compiled(
                select(1).compile(dialect=e1.dialect), (), {}, {}
            )

    def test_execute_events(self):

        stmts = []
        cursor_stmts = []

        def execute(
            conn, clauseelement, multiparams, params, execution_options
        ):
            stmts.append((str(clauseelement), params, multiparams))

        def cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            cursor_stmts.append((str(statement), parameters, None))

        # TODO: this test is kind of a mess

        for engine in [
            engines.testing_engine(options=dict(implicit_returning=False)),
            engines.testing_engine(
                options=dict(implicit_returning=False)
            ).connect(),
        ]:
            event.listen(engine, "before_execute", execute)
            event.listen(engine, "before_cursor_execute", cursor_execute)
            m = MetaData(engine)
            t1 = Table(
                "t1",
                m,
                Column("c1", Integer, primary_key=True),
                Column(
                    "c2",
                    String(50),
                    default=func.lower("Foo"),
                    primary_key=True,
                ),
            )

            if isinstance(engine, Connection):
                ctx = None
                conn = engine
            else:
                ctx = conn = engine.connect()

            try:
                m.create_all(conn, checkfirst=False)
                try:
                    conn.execute(t1.insert(), dict(c1=5, c2="some data"))
                    conn.execute(t1.insert(), dict(c1=6))
                    eq_(
                        conn.execute(text("select * from t1")).fetchall(),
                        [(5, "some data"), (6, "foo")],
                    )
                finally:
                    m.drop_all(conn)
                    if engine._is_future:
                        conn.commit()
            finally:
                if ctx:
                    ctx.close()

            if engine._is_future:
                compiled = [
                    ("CREATE TABLE t1", {}, None),
                    (
                        "INSERT INTO t1 (c1, c2)",
                        {"c2": "some data", "c1": 5},
                        None,
                    ),
                    ("INSERT INTO t1 (c1, c2)", {"c1": 6}, None),
                    ("select * from t1", {}, None),
                    ("DROP TABLE t1", {}, None),
                ]
            else:
                compiled = [
                    ("CREATE TABLE t1", {}, None),
                    (
                        "INSERT INTO t1 (c1, c2)",
                        {},
                        ({"c2": "some data", "c1": 5},),
                    ),
                    ("INSERT INTO t1 (c1, c2)", {}, ({"c1": 6},)),
                    ("select * from t1", {}, None),
                    ("DROP TABLE t1", {}, None),
                ]

            cursor = [
                ("CREATE TABLE t1", {}, ()),
                (
                    "INSERT INTO t1 (c1, c2)",
                    {"c2": "some data", "c1": 5},
                    (5, "some data"),
                ),
                ("SELECT lower", {"lower_1": "Foo"}, ("Foo",)),
                (
                    "INSERT INTO t1 (c1, c2)",
                    {"c2": "foo", "c1": 6},
                    (6, "foo"),
                ),
                ("select * from t1", {}, ()),
                ("DROP TABLE t1", {}, ()),
            ]
            self._assert_stmts(compiled, stmts)
            self._assert_stmts(cursor, cursor_stmts)

    def test_options(self):
        canary = []

        def execute(conn, *args, **kw):
            canary.append("execute")

        def cursor_execute(conn, *args, **kw):
            canary.append("cursor_execute")

        engine = engines.testing_engine()
        event.listen(engine, "before_execute", execute)
        event.listen(engine, "before_cursor_execute", cursor_execute)
        conn = engine.connect()
        c2 = conn.execution_options(foo="bar")
        eq_(c2._execution_options, {"foo": "bar"})
        c2.execute(select(1))
        c3 = c2.execution_options(bar="bat")
        eq_(c3._execution_options, {"foo": "bar", "bar": "bat"})
        eq_(canary, ["execute", "cursor_execute"])

    @testing.requires.ad_hoc_engines
    def test_generative_engine_event_dispatch(self):
        canary = []

        def l1(*arg, **kw):
            canary.append("l1")

        def l2(*arg, **kw):
            canary.append("l2")

        def l3(*arg, **kw):
            canary.append("l3")

        eng = engines.testing_engine(
            options={"execution_options": {"base": "x1"}}
        )
        event.listen(eng, "before_execute", l1)

        eng1 = eng.execution_options(foo="b1")
        event.listen(eng, "before_execute", l2)
        event.listen(eng1, "before_execute", l3)

        with eng.connect() as conn:
            conn.execute(select(1))

        eq_(canary, ["l1", "l2"])

        with eng1.connect() as conn:
            conn.execute(select(1))

        eq_(canary, ["l1", "l2", "l3", "l1", "l2"])

    @testing.requires.ad_hoc_engines
    def test_clslevel_engine_event_options(self):
        canary = []

        def l1(*arg, **kw):
            canary.append("l1")

        def l2(*arg, **kw):
            canary.append("l2")

        def l3(*arg, **kw):
            canary.append("l3")

        def l4(*arg, **kw):
            canary.append("l4")

        event.listen(Engine, "before_execute", l1)

        eng = engines.testing_engine(
            options={"execution_options": {"base": "x1"}}
        )
        event.listen(eng, "before_execute", l2)

        eng1 = eng.execution_options(foo="b1")
        event.listen(eng, "before_execute", l3)
        event.listen(eng1, "before_execute", l4)

        with eng.connect() as conn:
            conn.execute(select(1))

        eq_(canary, ["l1", "l2", "l3"])

        with eng1.connect() as conn:
            conn.execute(select(1))

        eq_(canary, ["l1", "l2", "l3", "l4", "l1", "l2", "l3"])

        canary[:] = []

        event.remove(Engine, "before_execute", l1)
        event.remove(eng1, "before_execute", l4)
        event.remove(eng, "before_execute", l3)

        with eng1.connect() as conn:
            conn.execute(select(1))
        eq_(canary, ["l2"])

    @testing.requires.ad_hoc_engines
    def test_cant_listen_to_option_engine(self):
        from sqlalchemy.engine import base

        def evt(*arg, **kw):
            pass

        assert_raises_message(
            tsa.exc.InvalidRequestError,
            r"Can't assign an event directly to the "
            "<class 'sqlalchemy.engine.base.OptionEngine'> class",
            event.listen,
            base.OptionEngine,
            "before_cursor_execute",
            evt,
        )

    @testing.requires.ad_hoc_engines
    def test_dispose_event(self):
        canary = Mock()
        eng = create_engine(testing.db.url)
        event.listen(eng, "engine_disposed", canary)

        conn = eng.connect()
        conn.close()
        eng.dispose()

        conn = eng.connect()
        conn.close()

        eq_(canary.mock_calls, [call(eng)])

        eng.dispose()

        eq_(canary.mock_calls, [call(eng), call(eng)])

    def test_retval_flag(self):
        canary = []

        def tracker(name):
            def go(conn, *args, **kw):
                canary.append(name)

            return go

        def execute(
            conn, clauseelement, multiparams, params, execution_options
        ):
            canary.append("execute")
            return clauseelement, multiparams, params

        def cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            canary.append("cursor_execute")
            return statement, parameters

        engine = engines.testing_engine()

        assert_raises(
            tsa.exc.ArgumentError,
            event.listen,
            engine,
            "begin",
            tracker("begin"),
            retval=True,
        )

        event.listen(engine, "before_execute", execute, retval=True)
        event.listen(
            engine, "before_cursor_execute", cursor_execute, retval=True
        )
        with engine.connect() as conn:
            conn.execute(select(1))
        eq_(canary, ["execute", "cursor_execute"])

    @testing.requires.legacy_engine
    def test_engine_connect(self):
        engine = engines.testing_engine()

        tracker = Mock()
        event.listen(engine, "engine_connect", tracker)

        c1 = engine.connect()
        c2 = c1._branch()
        c1.close()
        eq_(tracker.mock_calls, [call(c1, False), call(c2, True)])

    def test_execution_options(self):
        engine = engines.testing_engine()

        engine_tracker = Mock()
        conn_tracker = Mock()

        event.listen(engine, "set_engine_execution_options", engine_tracker)
        event.listen(engine, "set_connection_execution_options", conn_tracker)

        e2 = engine.execution_options(e1="opt_e1")
        c1 = engine.connect()
        c2 = c1.execution_options(c1="opt_c1")
        c3 = e2.connect()
        c4 = c3.execution_options(c3="opt_c3")
        eq_(engine_tracker.mock_calls, [call(e2, {"e1": "opt_e1"})])
        eq_(
            conn_tracker.mock_calls,
            [call(c2, {"c1": "opt_c1"}), call(c4, {"c3": "opt_c3"})],
        )

    @testing.requires.sequences
    @testing.provide_metadata
    def test_cursor_execute(self):
        canary = []

        def tracker(name):
            def go(conn, cursor, statement, parameters, context, executemany):
                canary.append((statement, context))

            return go

        engine = engines.testing_engine()

        t = Table(
            "t",
            self.metadata,
            Column(
                "x",
                testing.db.dialect.sequence_default_column_type,
                Sequence("t_id_seq"),
                primary_key=True,
            ),
            implicit_returning=False,
        )
        self.metadata.create_all(engine)

        with engine.begin() as conn:
            event.listen(
                conn, "before_cursor_execute", tracker("cursor_execute")
            )
            conn.execute(t.insert())

        if testing.requires.supports_lastrowid.enabled:
            # new MariaDB 10.3 supports sequences + lastrowid; only
            # one statement
            assert "INSERT" in canary[0][0]
        else:
            # we see the sequence pre-executed in the first call
            assert "t_id_seq" in canary[0][0]
            assert "INSERT" in canary[1][0]
            # same context
            is_(canary[0][1], canary[1][1])

    def test_transactional(self):
        canary = []

        def tracker(name):
            def go(conn, *args, **kw):
                canary.append(name)

            return go

        engine = engines.testing_engine()
        event.listen(engine, "before_execute", tracker("execute"))
        event.listen(
            engine, "before_cursor_execute", tracker("cursor_execute")
        )
        event.listen(engine, "begin", tracker("begin"))
        event.listen(engine, "commit", tracker("commit"))
        event.listen(engine, "rollback", tracker("rollback"))

        conn = engine.connect()
        trans = conn.begin()
        conn.execute(select(1))
        trans.rollback()
        trans = conn.begin()
        conn.execute(select(1))
        trans.commit()

        eq_(
            canary,
            [
                "begin",
                "execute",
                "cursor_execute",
                "rollback",
                "begin",
                "execute",
                "cursor_execute",
                "commit",
            ],
        )

    def test_transactional_named(self):
        canary = []

        def tracker(name):
            def go(*args, **kw):
                canary.append((name, set(kw)))

            return go

        engine = engines.testing_engine()
        event.listen(engine, "before_execute", tracker("execute"), named=True)
        event.listen(
            engine,
            "before_cursor_execute",
            tracker("cursor_execute"),
            named=True,
        )
        event.listen(engine, "begin", tracker("begin"), named=True)
        event.listen(engine, "commit", tracker("commit"), named=True)
        event.listen(engine, "rollback", tracker("rollback"), named=True)

        conn = engine.connect()
        trans = conn.begin()
        conn.execute(select(1))
        trans.rollback()
        trans = conn.begin()
        conn.execute(select(1))
        trans.commit()

        eq_(
            canary,
            [
                ("begin", set(["conn"])),
                (
                    "execute",
                    set(
                        [
                            "conn",
                            "clauseelement",
                            "multiparams",
                            "params",
                            "execution_options",
                        ]
                    ),
                ),
                (
                    "cursor_execute",
                    set(
                        [
                            "conn",
                            "cursor",
                            "executemany",
                            "statement",
                            "parameters",
                            "context",
                        ]
                    ),
                ),
                ("rollback", set(["conn"])),
                ("begin", set(["conn"])),
                (
                    "execute",
                    set(
                        [
                            "conn",
                            "clauseelement",
                            "multiparams",
                            "params",
                            "execution_options",
                        ]
                    ),
                ),
                (
                    "cursor_execute",
                    set(
                        [
                            "conn",
                            "cursor",
                            "executemany",
                            "statement",
                            "parameters",
                            "context",
                        ]
                    ),
                ),
                ("commit", set(["conn"])),
            ],
        )

    @testing.requires.savepoints
    @testing.requires.two_phase_transactions
    def test_transactional_advanced(self):
        canary1 = []

        def tracker1(name):
            def go(*args, **kw):
                canary1.append(name)

            return go

        canary2 = []

        def tracker2(name):
            def go(*args, **kw):
                canary2.append(name)

            return go

        engine = engines.testing_engine()
        for name in [
            "begin",
            "savepoint",
            "rollback_savepoint",
            "release_savepoint",
            "rollback",
            "begin_twophase",
            "prepare_twophase",
            "commit_twophase",
        ]:
            event.listen(engine, "%s" % name, tracker1(name))

        conn = engine.connect()
        for name in [
            "begin",
            "savepoint",
            "rollback_savepoint",
            "release_savepoint",
            "rollback",
            "begin_twophase",
            "prepare_twophase",
            "commit_twophase",
        ]:
            event.listen(conn, "%s" % name, tracker2(name))

        trans = conn.begin()
        trans2 = conn.begin_nested()
        conn.execute(select(1))
        trans2.rollback()
        trans2 = conn.begin_nested()
        conn.execute(select(1))
        trans2.commit()
        trans.rollback()

        trans = conn.begin_twophase()
        conn.execute(select(1))
        trans.prepare()
        trans.commit()

        eq_(
            canary1,
            [
                "begin",
                "savepoint",
                "rollback_savepoint",
                "savepoint",
                "release_savepoint",
                "rollback",
                "begin_twophase",
                "prepare_twophase",
                "commit_twophase",
            ],
        )
        eq_(
            canary2,
            [
                "begin",
                "savepoint",
                "rollback_savepoint",
                "savepoint",
                "release_savepoint",
                "rollback",
                "begin_twophase",
                "prepare_twophase",
                "commit_twophase",
            ],
        )


class FutureEngineEventsTest(fixtures.FutureEngineMixin, EngineEventsTest):
    pass


class HandleErrorTest(fixtures.TestBase):
    __requires__ = ("ad_hoc_engines",)
    __backend__ = True

    def tearDown(self):
        Engine.dispatch._clear()
        Engine._has_events = False

    def test_handle_error(self):
        engine = engines.testing_engine()
        canary = Mock(return_value=None)

        event.listen(engine, "handle_error", canary)

        with engine.connect() as conn:
            try:
                conn.exec_driver_sql("SELECT FOO FROM I_DONT_EXIST")
                assert False
            except tsa.exc.DBAPIError as e:
                ctx = canary.mock_calls[0][1][0]

                eq_(ctx.original_exception, e.orig)
                is_(ctx.sqlalchemy_exception, e)
                eq_(ctx.statement, "SELECT FOO FROM I_DONT_EXIST")

    def test_exception_event_reraise(self):
        engine = engines.testing_engine()

        class MyException(Exception):
            pass

        @event.listens_for(engine, "handle_error", retval=True)
        def err(context):
            stmt = context.statement
            exception = context.original_exception
            if "ERROR ONE" in str(stmt):
                return MyException("my exception")
            elif "ERROR TWO" in str(stmt):
                return exception
            else:
                return None

        conn = engine.connect()
        # case 1: custom exception
        assert_raises_message(
            MyException,
            "my exception",
            conn.exec_driver_sql,
            "SELECT 'ERROR ONE' FROM I_DONT_EXIST",
        )
        # case 2: return the DBAPI exception we're given;
        # no wrapping should occur
        assert_raises(
            conn.dialect.dbapi.Error,
            conn.exec_driver_sql,
            "SELECT 'ERROR TWO' FROM I_DONT_EXIST",
        )
        # case 3: normal wrapping
        assert_raises(
            tsa.exc.DBAPIError,
            conn.exec_driver_sql,
            "SELECT 'ERROR THREE' FROM I_DONT_EXIST",
        )

    def test_exception_event_reraise_chaining(self):
        engine = engines.testing_engine()

        class MyException1(Exception):
            pass

        class MyException2(Exception):
            pass

        class MyException3(Exception):
            pass

        @event.listens_for(engine, "handle_error", retval=True)
        def err1(context):
            stmt = context.statement

            if (
                "ERROR ONE" in str(stmt)
                or "ERROR TWO" in str(stmt)
                or "ERROR THREE" in str(stmt)
            ):
                return MyException1("my exception")
            elif "ERROR FOUR" in str(stmt):
                raise MyException3("my exception short circuit")

        @event.listens_for(engine, "handle_error", retval=True)
        def err2(context):
            stmt = context.statement
            if (
                "ERROR ONE" in str(stmt) or "ERROR FOUR" in str(stmt)
            ) and isinstance(context.chained_exception, MyException1):
                raise MyException2("my exception chained")
            elif "ERROR TWO" in str(stmt):
                return context.chained_exception
            else:
                return None

        conn = engine.connect()

        with patch.object(
            engine.dialect.execution_ctx_cls, "handle_dbapi_exception"
        ) as patched:
            assert_raises_message(
                MyException2,
                "my exception chained",
                conn.exec_driver_sql,
                "SELECT 'ERROR ONE' FROM I_DONT_EXIST",
            )
            eq_(patched.call_count, 1)

        with patch.object(
            engine.dialect.execution_ctx_cls, "handle_dbapi_exception"
        ) as patched:
            assert_raises(
                MyException1,
                conn.exec_driver_sql,
                "SELECT 'ERROR TWO' FROM I_DONT_EXIST",
            )
            eq_(patched.call_count, 1)

        with patch.object(
            engine.dialect.execution_ctx_cls, "handle_dbapi_exception"
        ) as patched:
            # test that non None from err1 isn't cancelled out
            # by err2
            assert_raises(
                MyException1,
                conn.exec_driver_sql,
                "SELECT 'ERROR THREE' FROM I_DONT_EXIST",
            )
            eq_(patched.call_count, 1)

        with patch.object(
            engine.dialect.execution_ctx_cls, "handle_dbapi_exception"
        ) as patched:
            assert_raises(
                tsa.exc.DBAPIError,
                conn.exec_driver_sql,
                "SELECT 'ERROR FIVE' FROM I_DONT_EXIST",
            )
            eq_(patched.call_count, 1)

        with patch.object(
            engine.dialect.execution_ctx_cls, "handle_dbapi_exception"
        ) as patched:
            assert_raises_message(
                MyException3,
                "my exception short circuit",
                conn.exec_driver_sql,
                "SELECT 'ERROR FOUR' FROM I_DONT_EXIST",
            )
            eq_(patched.call_count, 1)

    def test_exception_autorollback_fails(self):
        engine = engines.testing_engine()
        conn = engine.connect()

        def boom(connection):
            raise engine.dialect.dbapi.OperationalError("rollback failed")

        with expect_warnings(
            r"An exception has occurred during handling of a previous "
            r"exception.  The previous exception "
            r"is.*(?:i_dont_exist|does not exist)",
            py2konly=True,
        ):
            with patch.object(conn.dialect, "do_rollback", boom):
                assert_raises_message(
                    tsa.exc.OperationalError,
                    "rollback failed",
                    conn.exec_driver_sql,
                    "insert into i_dont_exist (x) values ('y')",
                )

    def test_exception_event_ad_hoc_context(self):
        """test that handle_error is called with a context in
        cases where _handle_dbapi_error() is normally called without
        any context.

        """

        engine = engines.testing_engine()

        listener = Mock(return_value=None)
        event.listen(engine, "handle_error", listener)

        nope = SomeException("nope")

        class MyType(TypeDecorator):
            impl = Integer

            def process_bind_param(self, value, dialect):
                raise nope

        with engine.connect() as conn:
            assert_raises_message(
                tsa.exc.StatementError,
                r"\(.*.SomeException\) " r"nope\n\[SQL\: u?SELECT 1 ",
                conn.execute,
                select(1).where(column("foo") == literal("bar", MyType())),
            )

        ctx = listener.mock_calls[0][1][0]
        assert ctx.statement.startswith("SELECT 1 ")
        is_(ctx.is_disconnect, False)
        is_(ctx.original_exception, nope)

    def test_exception_event_non_dbapi_error(self):
        """test that handle_error is called with a context in
        cases where DBAPI raises an exception that is not a DBAPI
        exception, e.g. internal errors or encoding problems.

        """
        engine = engines.testing_engine()

        listener = Mock(return_value=None)
        event.listen(engine, "handle_error", listener)

        nope = TypeError("I'm not a DBAPI error")
        with engine.connect() as c:
            c.connection.cursor = Mock(
                return_value=Mock(execute=Mock(side_effect=nope))
            )

            assert_raises_message(
                TypeError,
                "I'm not a DBAPI error",
                c.exec_driver_sql,
                "select ",
            )
        ctx = listener.mock_calls[0][1][0]
        eq_(ctx.statement, "select ")
        is_(ctx.is_disconnect, False)
        is_(ctx.original_exception, nope)

    def test_exception_event_disable_handlers(self):
        engine = engines.testing_engine()

        class MyException1(Exception):
            pass

        @event.listens_for(engine, "handle_error")
        def err1(context):
            stmt = context.statement

            if "ERROR_ONE" in str(stmt):
                raise MyException1("my exception short circuit")

        with engine.connect() as conn:
            assert_raises(
                tsa.exc.DBAPIError,
                conn.execution_options(
                    skip_user_error_events=True
                ).exec_driver_sql,
                "SELECT ERROR_ONE FROM I_DONT_EXIST",
            )

            assert_raises(
                MyException1,
                conn.execution_options(
                    skip_user_error_events=False
                ).exec_driver_sql,
                "SELECT ERROR_ONE FROM I_DONT_EXIST",
            )

    def _test_alter_disconnect(self, orig_error, evt_value):
        engine = engines.testing_engine()

        @event.listens_for(engine, "handle_error")
        def evt(ctx):
            ctx.is_disconnect = evt_value

        with patch.object(
            engine.dialect, "is_disconnect", Mock(return_value=orig_error)
        ):

            with engine.connect() as c:
                try:
                    c.exec_driver_sql("SELECT x FROM nonexistent")
                    assert False
                except tsa.exc.StatementError as st:
                    eq_(st.connection_invalidated, evt_value)

    def test_alter_disconnect_to_true(self):
        self._test_alter_disconnect(False, True)
        self._test_alter_disconnect(True, True)

    def test_alter_disconnect_to_false(self):
        self._test_alter_disconnect(True, False)
        self._test_alter_disconnect(False, False)

    @testing.requires.independent_connections
    def _test_alter_invalidate_pool_to_false(self, set_to_false):
        orig_error = True

        engine = engines.testing_engine()

        @event.listens_for(engine, "handle_error")
        def evt(ctx):
            if set_to_false:
                ctx.invalidate_pool_on_disconnect = False

        c1, c2, c3 = (
            engine.pool.connect(),
            engine.pool.connect(),
            engine.pool.connect(),
        )
        crecs = [conn._connection_record for conn in (c1, c2, c3)]
        c1.close()
        c2.close()
        c3.close()

        with patch.object(
            engine.dialect, "is_disconnect", Mock(return_value=orig_error)
        ):

            with engine.connect() as c:
                target_crec = c.connection._connection_record
                try:
                    c.exec_driver_sql("SELECT x FROM nonexistent")
                    assert False
                except tsa.exc.StatementError as st:
                    eq_(st.connection_invalidated, True)

        for crec in crecs:
            if crec is target_crec or not set_to_false:
                is_not_(crec.connection, crec.get_connection())
            else:
                is_(crec.connection, crec.get_connection())

    def test_alter_invalidate_pool_to_false(self):
        self._test_alter_invalidate_pool_to_false(True)

    def test_alter_invalidate_pool_stays_true(self):
        self._test_alter_invalidate_pool_to_false(False)

    def test_handle_error_event_connect_isolation_level(self):
        engine = engines.testing_engine()

        class MySpecialException(Exception):
            pass

        @event.listens_for(engine, "handle_error")
        def handle_error(ctx):
            raise MySpecialException("failed operation")

        ProgrammingError = engine.dialect.dbapi.ProgrammingError
        with engine.connect() as conn:
            with patch.object(
                conn.dialect,
                "get_isolation_level",
                Mock(side_effect=ProgrammingError("random error")),
            ):
                assert_raises(MySpecialException, conn.get_isolation_level)

    @testing.only_on("sqlite")
    def test_cursor_close_resultset_failed_connectionless(self):
        engine = engines.testing_engine()

        the_conn = []
        the_cursor = []

        @event.listens_for(engine, "after_cursor_execute")
        def go(
            connection, cursor, statement, parameters, context, executemany
        ):
            the_cursor.append(cursor)
            the_conn.append(connection)

        with mock.patch(
            "sqlalchemy.engine.cursor.BaseCursorResult.__init__",
            Mock(side_effect=tsa.exc.InvalidRequestError("duplicate col")),
        ):
            with engine.connect() as conn:
                assert_raises(
                    tsa.exc.InvalidRequestError,
                    conn.execute,
                    text("select 1"),
                )

        # cursor is closed
        assert_raises_message(
            engine.dialect.dbapi.ProgrammingError,
            "Cannot operate on a closed cursor",
            the_cursor[0].execute,
            "select 1",
        )

        # connection is closed
        assert the_conn[0].closed

    @testing.only_on("sqlite")
    def test_cursor_close_resultset_failed_explicit(self):
        engine = engines.testing_engine()

        the_cursor = []

        @event.listens_for(engine, "after_cursor_execute")
        def go(
            connection, cursor, statement, parameters, context, executemany
        ):
            the_cursor.append(cursor)

        conn = engine.connect()

        with mock.patch(
            "sqlalchemy.engine.cursor.BaseCursorResult.__init__",
            Mock(side_effect=tsa.exc.InvalidRequestError("duplicate col")),
        ):
            assert_raises(
                tsa.exc.InvalidRequestError, conn.execute, text("select 1"),
            )

        # cursor is closed
        assert_raises_message(
            engine.dialect.dbapi.ProgrammingError,
            "Cannot operate on a closed cursor",
            the_cursor[0].execute,
            "select 1",
        )

        # connection not closed
        assert not conn.closed

        conn.close()


class HandleInvalidatedOnConnectTest(fixtures.TestBase):
    __requires__ = ("sqlite",)

    def setUp(self):
        e = create_engine("sqlite://")

        connection = Mock(get_server_version_info=Mock(return_value="5.0"))

        def connect(*args, **kwargs):
            return connection

        dbapi = Mock(
            sqlite_version_info=(99, 9, 9),
            version_info=(99, 9, 9),
            sqlite_version="99.9.9",
            paramstyle="named",
            connect=Mock(side_effect=connect),
        )

        sqlite3 = e.dialect.dbapi
        dbapi.Error = (sqlite3.Error,)
        dbapi.ProgrammingError = sqlite3.ProgrammingError

        self.dbapi = dbapi
        self.ProgrammingError = sqlite3.ProgrammingError

    def test_wraps_connect_in_dbapi(self):
        dbapi = self.dbapi
        dbapi.connect = Mock(side_effect=self.ProgrammingError("random error"))
        try:
            create_engine("sqlite://", module=dbapi).connect()
            assert False
        except tsa.exc.DBAPIError as de:
            assert not de.connection_invalidated

    def test_handle_error_event_connect(self):
        dbapi = self.dbapi
        dbapi.connect = Mock(side_effect=self.ProgrammingError("random error"))

        class MySpecialException(Exception):
            pass

        eng = create_engine("sqlite://", module=dbapi)

        @event.listens_for(eng, "handle_error")
        def handle_error(ctx):
            assert ctx.engine is eng
            assert ctx.connection is None
            raise MySpecialException("failed operation")

        assert_raises(MySpecialException, eng.connect)

    def test_handle_error_event_revalidate(self):
        dbapi = self.dbapi

        class MySpecialException(Exception):
            pass

        eng = create_engine("sqlite://", module=dbapi, _initialize=False)

        @event.listens_for(eng, "handle_error")
        def handle_error(ctx):
            assert ctx.engine is eng
            assert ctx.connection is conn
            assert isinstance(
                ctx.sqlalchemy_exception, tsa.exc.ProgrammingError
            )
            raise MySpecialException("failed operation")

        conn = eng.connect()
        conn.invalidate()

        dbapi.connect = Mock(side_effect=self.ProgrammingError("random error"))

        assert_raises(MySpecialException, getattr, conn, "connection")

    def test_handle_error_event_implicit_revalidate(self):
        dbapi = self.dbapi

        class MySpecialException(Exception):
            pass

        eng = create_engine("sqlite://", module=dbapi, _initialize=False)

        @event.listens_for(eng, "handle_error")
        def handle_error(ctx):
            assert ctx.engine is eng
            assert ctx.connection is conn
            assert isinstance(
                ctx.sqlalchemy_exception, tsa.exc.ProgrammingError
            )
            raise MySpecialException("failed operation")

        conn = eng.connect()
        conn.invalidate()

        dbapi.connect = Mock(side_effect=self.ProgrammingError("random error"))

        assert_raises(MySpecialException, conn.execute, select(1))

    def test_handle_error_custom_connect(self):
        dbapi = self.dbapi

        class MySpecialException(Exception):
            pass

        def custom_connect():
            raise self.ProgrammingError("random error")

        eng = create_engine("sqlite://", module=dbapi, creator=custom_connect)

        @event.listens_for(eng, "handle_error")
        def handle_error(ctx):
            assert ctx.engine is eng
            assert ctx.connection is None
            raise MySpecialException("failed operation")

        assert_raises(MySpecialException, eng.connect)

    def test_handle_error_event_connect_invalidate_flag(self):
        dbapi = self.dbapi
        dbapi.connect = Mock(
            side_effect=self.ProgrammingError(
                "Cannot operate on a closed database."
            )
        )

        class MySpecialException(Exception):
            pass

        eng = create_engine("sqlite://", module=dbapi)

        @event.listens_for(eng, "handle_error")
        def handle_error(ctx):
            assert ctx.is_disconnect
            ctx.is_disconnect = False

        try:
            eng.connect()
            assert False
        except tsa.exc.DBAPIError as de:
            assert not de.connection_invalidated

    def test_cant_connect_stay_invalidated(self):
        class MySpecialException(Exception):
            pass

        eng = create_engine("sqlite://")

        @event.listens_for(eng, "handle_error")
        def handle_error(ctx):
            assert ctx.is_disconnect

        conn = eng.connect()

        conn.invalidate()

        eng.pool._creator = Mock(
            side_effect=self.ProgrammingError(
                "Cannot operate on a closed database."
            )
        )

        try:
            conn.connection
            assert False
        except tsa.exc.DBAPIError:
            assert conn.invalidated

    def test_dont_touch_non_dbapi_exception_on_connect(self):
        dbapi = self.dbapi
        dbapi.connect = Mock(side_effect=TypeError("I'm not a DBAPI error"))

        e = create_engine("sqlite://", module=dbapi)
        e.dialect.is_disconnect = is_disconnect = Mock()
        assert_raises_message(TypeError, "I'm not a DBAPI error", e.connect)
        eq_(is_disconnect.call_count, 0)

    def test_ensure_dialect_does_is_disconnect_no_conn(self):
        """test that is_disconnect() doesn't choke if no connection,
        cursor given."""
        dialect = testing.db.dialect
        dbapi = dialect.dbapi
        assert not dialect.is_disconnect(
            dbapi.OperationalError("test"), None, None
        )

    def test_invalidate_on_connect(self):
        """test that is_disconnect() is called during connect.

        interpretation of connection failures are not supported by
        every backend.

        """
        dbapi = self.dbapi
        dbapi.connect = Mock(
            side_effect=self.ProgrammingError(
                "Cannot operate on a closed database."
            )
        )
        e = create_engine("sqlite://", module=dbapi)
        try:
            e.connect()
            assert False
        except tsa.exc.DBAPIError as de:
            assert de.connection_invalidated


class DialectEventTest(fixtures.TestBase):
    @contextmanager
    def _run_test(self, retval):
        m1 = Mock()

        m1.do_execute.return_value = retval
        m1.do_executemany.return_value = retval
        m1.do_execute_no_params.return_value = retval
        e = engines.testing_engine(options={"_initialize": False})

        event.listen(e, "do_execute", m1.do_execute)
        event.listen(e, "do_executemany", m1.do_executemany)
        event.listen(e, "do_execute_no_params", m1.do_execute_no_params)

        e.dialect.do_execute = m1.real_do_execute
        e.dialect.do_executemany = m1.real_do_executemany
        e.dialect.do_execute_no_params = m1.real_do_execute_no_params

        def mock_the_cursor(cursor, *arg):
            arg[-1].get_result_proxy = Mock(return_value=Mock(context=arg[-1]))
            return retval

        m1.real_do_execute.side_effect = (
            m1.do_execute.side_effect
        ) = mock_the_cursor
        m1.real_do_executemany.side_effect = (
            m1.do_executemany.side_effect
        ) = mock_the_cursor
        m1.real_do_execute_no_params.side_effect = (
            m1.do_execute_no_params.side_effect
        ) = mock_the_cursor

        with e.connect() as conn:
            yield conn, m1

    def _assert(self, retval, m1, m2, mock_calls):
        eq_(m1.mock_calls, mock_calls)
        if retval:
            eq_(m2.mock_calls, [])
        else:
            eq_(m2.mock_calls, mock_calls)

    def _test_do_execute(self, retval):
        with self._run_test(retval) as (conn, m1):
            result = conn.exec_driver_sql(
                "insert into table foo", {"foo": "bar"}
            )
        self._assert(
            retval,
            m1.do_execute,
            m1.real_do_execute,
            [
                call(
                    result.context.cursor,
                    "insert into table foo",
                    {"foo": "bar"},
                    result.context,
                )
            ],
        )

    def _test_do_executemany(self, retval):
        with self._run_test(retval) as (conn, m1):
            result = conn.exec_driver_sql(
                "insert into table foo", [{"foo": "bar"}, {"foo": "bar"}]
            )
        self._assert(
            retval,
            m1.do_executemany,
            m1.real_do_executemany,
            [
                call(
                    result.context.cursor,
                    "insert into table foo",
                    [{"foo": "bar"}, {"foo": "bar"}],
                    result.context,
                )
            ],
        )

    def _test_do_execute_no_params(self, retval):
        with self._run_test(retval) as (conn, m1):
            result = conn.execution_options(
                no_parameters=True
            ).exec_driver_sql("insert into table foo")
        self._assert(
            retval,
            m1.do_execute_no_params,
            m1.real_do_execute_no_params,
            [
                call(
                    result.context.cursor,
                    "insert into table foo",
                    result.context,
                )
            ],
        )

    def _test_cursor_execute(self, retval):
        with self._run_test(retval) as (conn, m1):
            dialect = conn.dialect

            stmt = "insert into table foo"
            params = {"foo": "bar"}
            ctx = dialect.execution_ctx_cls._init_statement(
                dialect, conn, conn.connection, {}, stmt, [params],
            )

            conn._cursor_execute(ctx.cursor, stmt, params, ctx)

        self._assert(
            retval,
            m1.do_execute,
            m1.real_do_execute,
            [call(ctx.cursor, "insert into table foo", {"foo": "bar"}, ctx)],
        )

    def test_do_execute_w_replace(self):
        self._test_do_execute(True)

    def test_do_execute_wo_replace(self):
        self._test_do_execute(False)

    def test_do_executemany_w_replace(self):
        self._test_do_executemany(True)

    def test_do_executemany_wo_replace(self):
        self._test_do_executemany(False)

    def test_do_execute_no_params_w_replace(self):
        self._test_do_execute_no_params(True)

    def test_do_execute_no_params_wo_replace(self):
        self._test_do_execute_no_params(False)

    def test_cursor_execute_w_replace(self):
        self._test_cursor_execute(True)

    def test_cursor_execute_wo_replace(self):
        self._test_cursor_execute(False)

    def test_connect_replace_params(self):
        e = engines.testing_engine(options={"_initialize": False})

        @event.listens_for(e, "do_connect")
        def evt(dialect, conn_rec, cargs, cparams):
            cargs[:] = ["foo", "hoho"]
            cparams.clear()
            cparams["bar"] = "bat"
            conn_rec.info["boom"] = "bap"

        m1 = Mock()
        e.dialect.connect = m1.real_connect

        with e.connect() as conn:
            eq_(m1.mock_calls, [call.real_connect("foo", "hoho", bar="bat")])
            eq_(conn.info["boom"], "bap")

    def test_connect_do_connect(self):
        e = engines.testing_engine(options={"_initialize": False})

        m1 = Mock()

        @event.listens_for(e, "do_connect")
        def evt1(dialect, conn_rec, cargs, cparams):
            cargs[:] = ["foo", "hoho"]
            cparams.clear()
            cparams["bar"] = "bat"
            conn_rec.info["boom"] = "one"

        @event.listens_for(e, "do_connect")
        def evt2(dialect, conn_rec, cargs, cparams):
            conn_rec.info["bap"] = "two"
            return m1.our_connect(cargs, cparams)

        with e.connect() as conn:
            # called with args
            eq_(
                m1.mock_calls,
                [call.our_connect(["foo", "hoho"], {"bar": "bat"})],
            )

            eq_(conn.info["boom"], "one")
            eq_(conn.info["bap"], "two")

            # returned our mock connection
            is_(conn.connection.connection, m1.our_connect())

    def test_connect_do_connect_info_there_after_recycle(self):
        # test that info is maintained after the do_connect()
        # event for a soft invalidation.

        e = engines.testing_engine(options={"_initialize": False})

        @event.listens_for(e, "do_connect")
        def evt1(dialect, conn_rec, cargs, cparams):
            conn_rec.info["boom"] = "one"

        conn = e.connect()
        eq_(conn.info["boom"], "one")

        conn.connection.invalidate(soft=True)
        conn.close()
        conn = e.connect()
        eq_(conn.info["boom"], "one")

    def test_connect_do_connect_info_there_after_invalidate(self):
        # test that info is maintained after the do_connect()
        # event for a hard invalidation.

        e = engines.testing_engine(options={"_initialize": False})

        @event.listens_for(e, "do_connect")
        def evt1(dialect, conn_rec, cargs, cparams):
            assert not conn_rec.info
            conn_rec.info["boom"] = "one"

        conn = e.connect()
        eq_(conn.info["boom"], "one")

        conn.connection.invalidate()
        conn = e.connect()
        eq_(conn.info["boom"], "one")


class AutocommitTextTest(fixtures.TestBase):
    __backend__ = True

    def _test_keyword(self, keyword, expected=True):
        dbapi = Mock(
            connect=Mock(
                return_value=Mock(
                    cursor=Mock(return_value=Mock(description=()))
                )
            )
        )
        engine = engines.testing_engine(
            options={"_initialize": False, "pool_reset_on_return": None}
        )
        engine.dialect.dbapi = dbapi

        with engine.connect() as conn:
            conn.exec_driver_sql("%s something table something" % keyword)

            if expected:
                eq_(dbapi.connect().mock_calls, [call.cursor(), call.commit()])
            else:
                eq_(dbapi.connect().mock_calls, [call.cursor()])

    def test_update(self):
        self._test_keyword("UPDATE")

    def test_insert(self):
        self._test_keyword("INSERT")

    def test_delete(self):
        self._test_keyword("DELETE")

    def test_alter(self):
        self._test_keyword("ALTER TABLE")

    def test_create(self):
        self._test_keyword("CREATE TABLE foobar")

    def test_drop(self):
        self._test_keyword("DROP TABLE foobar")

    def test_select(self):
        self._test_keyword("SELECT foo FROM table", False)


class FutureExecuteTest(fixtures.FutureEngineMixin, fixtures.TablesTest):
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "users",
            metadata,
            Column("user_id", INT, primary_key=True, autoincrement=False),
            Column("user_name", VARCHAR(20)),
            test_needs_acid=True,
        )
        Table(
            "users_autoinc",
            metadata,
            Column(
                "user_id", INT, primary_key=True, test_needs_autoincrement=True
            ),
            Column("user_name", VARCHAR(20)),
            test_needs_acid=True,
        )

    @testing.combinations(
        ({}, {}, {}),
        ({"a": "b"}, {}, {"a": "b"}),
        ({"a": "b", "d": "e"}, {"a": "c"}, {"a": "c", "d": "e"}),
        argnames="conn_opts, exec_opts, expected",
    )
    def test_execution_opts_per_invoke(
        self, connection, conn_opts, exec_opts, expected
    ):
        opts = []

        @event.listens_for(connection, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            opts.append(context.execution_options)

        if conn_opts:
            connection = connection.execution_options(**conn_opts)

        if exec_opts:
            connection.execute(select(1), execution_options=exec_opts)
        else:
            connection.execute(select(1))

        eq_(opts, [expected])

    @testing.combinations(
        ({}, {}, {}, {}),
        ({}, {"a": "b"}, {}, {"a": "b"}),
        ({}, {"a": "b", "d": "e"}, {"a": "c"}, {"a": "c", "d": "e"}),
        (
            {"q": "z", "p": "r"},
            {"a": "b", "p": "x", "d": "e"},
            {"a": "c"},
            {"q": "z", "p": "x", "a": "c", "d": "e"},
        ),
        argnames="stmt_opts, conn_opts, exec_opts, expected",
    )
    def test_execution_opts_per_invoke_execute_events(
        self, connection, stmt_opts, conn_opts, exec_opts, expected
    ):
        opts = []

        @event.listens_for(connection, "before_execute")
        def before_execute(
            conn, clauseelement, multiparams, params, execution_options
        ):
            opts.append(("before", execution_options))

        @event.listens_for(connection, "after_execute")
        def after_execute(
            conn,
            clauseelement,
            multiparams,
            params,
            execution_options,
            result,
        ):
            opts.append(("after", execution_options))

        stmt = select(1)

        if stmt_opts:
            stmt = stmt.execution_options(**stmt_opts)

        if conn_opts:
            connection = connection.execution_options(**conn_opts)

        if exec_opts:
            connection.execute(stmt, execution_options=exec_opts)
        else:
            connection.execute(stmt)

        eq_(opts, [("before", expected), ("after", expected)])

    def test_no_branching(self, connection):
        with testing.expect_deprecated(
            r"The Connection.connect\(\) function/method is considered legacy"
        ):
            assert_raises_message(
                NotImplementedError,
                "sqlalchemy.future.Connection does not support "
                "'branching' of new connections.",
                connection.connect,
            )
