# coding: utf-8

from sqlalchemy.testing import eq_, is_, assert_raises, assert_raises_message
from sqlalchemy import *
from sqlalchemy import sql, exc, schema
from sqlalchemy.util import u
from sqlalchemy import util
from sqlalchemy.dialects.mysql import base as mysql
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.testing import AssertsCompiledSQL, AssertsExecutionResults
from sqlalchemy.testing import engines, fixtures
from sqlalchemy import testing
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import datetime
import decimal


class TypesTest(fixtures.TestBase, AssertsExecutionResults, AssertsCompiledSQL):
    """Test MySQL column types"""

    __dialect__ = mysql.dialect()
    __only_on__ = 'mysql'
    __backend__ = True

    def test_numeric(self):
        """Exercise type specification and options for numeric types."""

        columns = [
            # column type, args, kwargs, expected ddl
            # e.g. Column(Integer(10, unsigned=True)) ==
            # 'INTEGER(10) UNSIGNED'
            (mysql.MSNumeric, [], {},
             'NUMERIC'),
            (mysql.MSNumeric, [None], {},
             'NUMERIC'),
            (mysql.MSNumeric, [12], {},
             'NUMERIC(12)'),
            (mysql.MSNumeric, [12, 4], {'unsigned':True},
             'NUMERIC(12, 4) UNSIGNED'),
            (mysql.MSNumeric, [12, 4], {'zerofill':True},
             'NUMERIC(12, 4) ZEROFILL'),
            (mysql.MSNumeric, [12, 4], {'zerofill':True, 'unsigned':True},
             'NUMERIC(12, 4) UNSIGNED ZEROFILL'),

            (mysql.MSDecimal, [], {},
             'DECIMAL'),
            (mysql.MSDecimal, [None], {},
             'DECIMAL'),
            (mysql.MSDecimal, [12], {},
             'DECIMAL(12)'),
            (mysql.MSDecimal, [12, None], {},
             'DECIMAL(12)'),
            (mysql.MSDecimal, [12, 4], {'unsigned':True},
             'DECIMAL(12, 4) UNSIGNED'),
            (mysql.MSDecimal, [12, 4], {'zerofill':True},
             'DECIMAL(12, 4) ZEROFILL'),
            (mysql.MSDecimal, [12, 4], {'zerofill':True, 'unsigned':True},
             'DECIMAL(12, 4) UNSIGNED ZEROFILL'),

            (mysql.MSDouble, [None, None], {},
             'DOUBLE'),
            (mysql.MSDouble, [12, 4], {'unsigned':True},
             'DOUBLE(12, 4) UNSIGNED'),
            (mysql.MSDouble, [12, 4], {'zerofill':True},
             'DOUBLE(12, 4) ZEROFILL'),
            (mysql.MSDouble, [12, 4], {'zerofill':True, 'unsigned':True},
             'DOUBLE(12, 4) UNSIGNED ZEROFILL'),

            (mysql.MSReal, [None, None], {},
             'REAL'),
            (mysql.MSReal, [12, 4], {'unsigned':True},
             'REAL(12, 4) UNSIGNED'),
            (mysql.MSReal, [12, 4], {'zerofill':True},
             'REAL(12, 4) ZEROFILL'),
            (mysql.MSReal, [12, 4], {'zerofill':True, 'unsigned':True},
             'REAL(12, 4) UNSIGNED ZEROFILL'),

            (mysql.MSFloat, [], {},
             'FLOAT'),
            (mysql.MSFloat, [None], {},
             'FLOAT'),
            (mysql.MSFloat, [12], {},
             'FLOAT(12)'),
            (mysql.MSFloat, [12, 4], {},
             'FLOAT(12, 4)'),
            (mysql.MSFloat, [12, 4], {'unsigned':True},
             'FLOAT(12, 4) UNSIGNED'),
            (mysql.MSFloat, [12, 4], {'zerofill':True},
             'FLOAT(12, 4) ZEROFILL'),
            (mysql.MSFloat, [12, 4], {'zerofill':True, 'unsigned':True},
             'FLOAT(12, 4) UNSIGNED ZEROFILL'),

            (mysql.MSInteger, [], {},
             'INTEGER'),
            (mysql.MSInteger, [4], {},
             'INTEGER(4)'),
            (mysql.MSInteger, [4], {'unsigned':True},
             'INTEGER(4) UNSIGNED'),
            (mysql.MSInteger, [4], {'zerofill':True},
             'INTEGER(4) ZEROFILL'),
            (mysql.MSInteger, [4], {'zerofill':True, 'unsigned':True},
             'INTEGER(4) UNSIGNED ZEROFILL'),

            (mysql.MSBigInteger, [], {},
             'BIGINT'),
            (mysql.MSBigInteger, [4], {},
             'BIGINT(4)'),
            (mysql.MSBigInteger, [4], {'unsigned':True},
             'BIGINT(4) UNSIGNED'),
            (mysql.MSBigInteger, [4], {'zerofill':True},
             'BIGINT(4) ZEROFILL'),
            (mysql.MSBigInteger, [4], {'zerofill':True, 'unsigned':True},
             'BIGINT(4) UNSIGNED ZEROFILL'),

             (mysql.MSMediumInteger, [], {},
              'MEDIUMINT'),
             (mysql.MSMediumInteger, [4], {},
              'MEDIUMINT(4)'),
             (mysql.MSMediumInteger, [4], {'unsigned':True},
              'MEDIUMINT(4) UNSIGNED'),
             (mysql.MSMediumInteger, [4], {'zerofill':True},
              'MEDIUMINT(4) ZEROFILL'),
             (mysql.MSMediumInteger, [4], {'zerofill':True, 'unsigned':True},
              'MEDIUMINT(4) UNSIGNED ZEROFILL'),

            (mysql.MSTinyInteger, [], {},
             'TINYINT'),
            (mysql.MSTinyInteger, [1], {},
             'TINYINT(1)'),
            (mysql.MSTinyInteger, [1], {'unsigned':True},
             'TINYINT(1) UNSIGNED'),
            (mysql.MSTinyInteger, [1], {'zerofill':True},
             'TINYINT(1) ZEROFILL'),
            (mysql.MSTinyInteger, [1], {'zerofill':True, 'unsigned':True},
             'TINYINT(1) UNSIGNED ZEROFILL'),

            (mysql.MSSmallInteger, [], {},
             'SMALLINT'),
            (mysql.MSSmallInteger, [4], {},
             'SMALLINT(4)'),
            (mysql.MSSmallInteger, [4], {'unsigned':True},
             'SMALLINT(4) UNSIGNED'),
            (mysql.MSSmallInteger, [4], {'zerofill':True},
             'SMALLINT(4) ZEROFILL'),
            (mysql.MSSmallInteger, [4], {'zerofill':True, 'unsigned':True},
             'SMALLINT(4) UNSIGNED ZEROFILL'),
           ]

        for type_, args, kw, res in columns:
            type_inst = type_(*args, **kw)
            self.assert_compile(
                type_inst,
                res
            )
            # test that repr() copies out all arguments
            self.assert_compile(
                eval("mysql.%r" % type_inst),
                res
            )

    # fixed in mysql-connector as of 2.0.1,
    # see http://bugs.mysql.com/bug.php?id=73266
    @testing.provide_metadata
    def test_precision_float_roundtrip(self):
        t = Table('t', self.metadata,
                    Column('scale_value', mysql.DOUBLE(
                            precision=15, scale=12, asdecimal=True)),
                    Column('unscale_value', mysql.DOUBLE(
                            decimal_return_scale=12, asdecimal=True))
            )
        t.create(testing.db)
        testing.db.execute(
            t.insert(), scale_value=45.768392065789,
            unscale_value=45.768392065789
        )
        result = testing.db.scalar(select([t.c.scale_value]))
        eq_(result, decimal.Decimal("45.768392065789"))

        result = testing.db.scalar(select([t.c.unscale_value]))
        eq_(result, decimal.Decimal("45.768392065789"))

    @testing.exclude('mysql', '<', (4, 1, 1), 'no charset support')
    def test_charset(self):
        """Exercise CHARACTER SET and COLLATE-ish options on string types."""

        columns = [
            (mysql.MSChar, [1], {},
             'CHAR(1)'),
             (mysql.NCHAR, [1], {},
              'NATIONAL CHAR(1)'),
            (mysql.MSChar, [1], {'binary':True},
             'CHAR(1) BINARY'),
            (mysql.MSChar, [1], {'ascii':True},
             'CHAR(1) ASCII'),
            (mysql.MSChar, [1], {'unicode':True},
             'CHAR(1) UNICODE'),
            (mysql.MSChar, [1], {'ascii':True, 'binary':True},
             'CHAR(1) ASCII BINARY'),
            (mysql.MSChar, [1], {'unicode':True, 'binary':True},
             'CHAR(1) UNICODE BINARY'),
            (mysql.MSChar, [1], {'charset':'utf8'},
             'CHAR(1) CHARACTER SET utf8'),
            (mysql.MSChar, [1], {'charset':'utf8', 'binary':True},
             'CHAR(1) CHARACTER SET utf8 BINARY'),
            (mysql.MSChar, [1], {'charset':'utf8', 'unicode':True},
             'CHAR(1) CHARACTER SET utf8'),
            (mysql.MSChar, [1], {'charset':'utf8', 'ascii':True},
             'CHAR(1) CHARACTER SET utf8'),
            (mysql.MSChar, [1], {'collation': 'utf8_bin'},
             'CHAR(1) COLLATE utf8_bin'),
            (mysql.MSChar, [1], {'charset': 'utf8', 'collation': 'utf8_bin'},
             'CHAR(1) CHARACTER SET utf8 COLLATE utf8_bin'),
            (mysql.MSChar, [1], {'charset': 'utf8', 'binary': True},
             'CHAR(1) CHARACTER SET utf8 BINARY'),
            (mysql.MSChar, [1], {'charset': 'utf8', 'collation': 'utf8_bin',
                              'binary': True},
             'CHAR(1) CHARACTER SET utf8 COLLATE utf8_bin'),
            (mysql.MSChar, [1], {'national':True},
             'NATIONAL CHAR(1)'),
            (mysql.MSChar, [1], {'national':True, 'charset':'utf8'},
             'NATIONAL CHAR(1)'),
            (mysql.MSChar, [1], {'national':True, 'charset':'utf8',
                                'binary':True},
             'NATIONAL CHAR(1) BINARY'),
            (mysql.MSChar, [1], {'national':True, 'binary':True,
                                'unicode':True},
             'NATIONAL CHAR(1) BINARY'),
            (mysql.MSChar, [1], {'national':True, 'collation':'utf8_bin'},
             'NATIONAL CHAR(1) COLLATE utf8_bin'),

            (mysql.MSString, [1], {'charset':'utf8', 'collation':'utf8_bin'},
             'VARCHAR(1) CHARACTER SET utf8 COLLATE utf8_bin'),
            (mysql.MSString, [1], {'national':True, 'collation':'utf8_bin'},
             'NATIONAL VARCHAR(1) COLLATE utf8_bin'),

            (mysql.MSTinyText, [], {'charset':'utf8', 'collation':'utf8_bin'},
             'TINYTEXT CHARACTER SET utf8 COLLATE utf8_bin'),

            (mysql.MSMediumText, [], {'charset':'utf8', 'binary':True},
             'MEDIUMTEXT CHARACTER SET utf8 BINARY'),

            (mysql.MSLongText, [], {'ascii':True},
             'LONGTEXT ASCII'),

            (mysql.ENUM, ["foo", "bar"], {'unicode':True},
             '''ENUM('foo','bar') UNICODE'''),

            (String, [20], {"collation": "utf8"}, 'VARCHAR(20) COLLATE utf8')


           ]

        for type_, args, kw, res in columns:
            type_inst = type_(*args, **kw)
            self.assert_compile(
                type_inst,
                res
            )
            # test that repr() copies out all arguments
            self.assert_compile(
                eval("mysql.%r" % type_inst)
                    if type_ is not String
                    else eval("%r" % type_inst),
                res
            )

    @testing.only_if('mysql')
    @testing.fails_on('mysql+mysqlconnector', "different unicode behavior")
    @testing.exclude('mysql', '<', (5, 0, 5), 'a 5.0+ feature')
    @testing.provide_metadata
    def test_charset_collate_table(self):
        t = Table('foo', self.metadata,
            Column('id', Integer),
            Column('data', UnicodeText),
            mysql_default_charset='utf8',
            mysql_collate='utf8_bin'
        )
        t.create()
        m2 = MetaData(testing.db)
        t2 = Table('foo', m2, autoload=True)
        eq_(t2.kwargs['mysql_collate'], 'utf8_bin')
        eq_(t2.kwargs['mysql_default charset'], 'utf8')

        # test [ticket:2906]
        # in order to test the condition here, need to use
        # MySQLdb 1.2.3 and also need to pass either use_unicode=1
        # or charset=utf8 to the URL.
        t.insert().execute(id=1, data=u('some text'))
        assert isinstance(testing.db.scalar(select([t.c.data])), util.text_type)

    def test_bit_50(self):
        """Exercise BIT types on 5.0+ (not valid for all engine types)"""

        for type_, expected in [
            (mysql.MSBit(), "BIT"),
            (mysql.MSBit(1), "BIT(1)"),
            (mysql.MSBit(63), "BIT(63)"),
        ]:
            self.assert_compile(type_, expected)

    @testing.exclude('mysql', '<', (5, 0, 5), 'a 5.0+ feature')
    @testing.provide_metadata
    def test_bit_50_roundtrip(self):
        bit_table = Table('mysql_bits', self.metadata,
                          Column('b1', mysql.MSBit),
                          Column('b2', mysql.MSBit()),
                          Column('b3', mysql.MSBit(), nullable=False),
                          Column('b4', mysql.MSBit(1)),
                          Column('b5', mysql.MSBit(8)),
                          Column('b6', mysql.MSBit(32)),
                          Column('b7', mysql.MSBit(63)),
                          Column('b8', mysql.MSBit(64)))
        self.metadata.create_all()

        meta2 = MetaData(testing.db)
        reflected = Table('mysql_bits', meta2, autoload=True)

        for table in bit_table, reflected:

            def roundtrip(store, expected=None):
                expected = expected or store
                table.insert(store).execute()
                row = table.select().execute().first()
                try:
                    self.assert_(list(row) == expected)
                except:
                    print("Storing %s" % store)
                    print("Expected %s" % expected)
                    print("Found %s" % list(row))
                    raise
                table.delete().execute().close()

            roundtrip([0] * 8)
            roundtrip([None, None, 0, None, None, None, None, None])
            roundtrip([1] * 8)
            roundtrip([sql.text("b'1'")] * 8, [1] * 8)

            i = 255
            roundtrip([0, 0, 0, 0, i, i, i, i])
            i = 2 ** 32 - 1
            roundtrip([0, 0, 0, 0, 0, i, i, i])
            i = 2 ** 63 - 1
            roundtrip([0, 0, 0, 0, 0, 0, i, i])
            i = 2 ** 64 - 1
            roundtrip([0, 0, 0, 0, 0, 0, 0, i])

    def test_boolean(self):
        for type_, expected in [
            (BOOLEAN(), "BOOL"),
            (Boolean(), "BOOL"),
            (mysql.TINYINT(1), "TINYINT(1)"),
            (mysql.TINYINT(1, unsigned=True), "TINYINT(1) UNSIGNED")
        ]:
            self.assert_compile(type_, expected)

    @testing.provide_metadata
    def test_boolean_roundtrip(self):
        bool_table = Table(
            'mysql_bool',
            self.metadata,
            Column('b1', BOOLEAN),
            Column('b2', Boolean),
            Column('b3', mysql.MSTinyInteger(1)),
            Column('b4', mysql.MSTinyInteger(1, unsigned=True)),
            Column('b5', mysql.MSTinyInteger),
            )
        self.metadata.create_all()
        table = bool_table

        def roundtrip(store, expected=None):
            expected = expected or store
            table.insert(store).execute()
            row = table.select().execute().first()
            self.assert_(list(row) == expected)
            for i, val in enumerate(expected):
                if isinstance(val, bool):
                    self.assert_(val is row[i])
            table.delete().execute()

        roundtrip([None, None, None, None, None])
        roundtrip([True, True, 1, 1, 1])
        roundtrip([False, False, 0, 0, 0])
        roundtrip([True, True, True, True, True], [True, True, 1,
                  1, 1])
        roundtrip([False, False, 0, 0, 0], [False, False, 0, 0, 0])

        meta2 = MetaData(testing.db)
        table = Table('mysql_bool', meta2, autoload=True)
        eq_(colspec(table.c.b3), 'b3 TINYINT(1)')
        eq_(colspec(table.c.b4), 'b4 TINYINT(1) UNSIGNED')
        meta2 = MetaData(testing.db)
        table = Table(
            'mysql_bool',
            meta2,
            Column('b1', BOOLEAN),
            Column('b2', Boolean),
            Column('b3', BOOLEAN),
            Column('b4', BOOLEAN),
            autoload=True,
            )
        eq_(colspec(table.c.b3), 'b3 BOOL')
        eq_(colspec(table.c.b4), 'b4 BOOL')
        roundtrip([None, None, None, None, None])
        roundtrip([True, True, 1, 1, 1], [True, True, True, True,
                  1])
        roundtrip([False, False, 0, 0, 0], [False, False, False,
                  False, 0])
        roundtrip([True, True, True, True, True], [True, True,
                  True, True, 1])
        roundtrip([False, False, 0, 0, 0], [False, False, False,
                  False, 0])

    def test_timestamp_fsp(self):
        self.assert_compile(
                mysql.TIMESTAMP(fsp=5),
                "TIMESTAMP(5)"
        )

    def test_timestamp_defaults(self):
        """Exercise funky TIMESTAMP default syntax when used in columns."""

        columns = [
            ([TIMESTAMP], {},
             'TIMESTAMP NULL'),

            ([mysql.MSTimeStamp], {},
             'TIMESTAMP NULL'),

            ([mysql.MSTimeStamp(),
              DefaultClause(sql.text('CURRENT_TIMESTAMP'))],
             {},
             "TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP"),

            ([mysql.MSTimeStamp,
              DefaultClause(sql.text('CURRENT_TIMESTAMP'))],
             {'nullable': False},
             "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),

            ([mysql.MSTimeStamp,
              DefaultClause(sql.text("'1999-09-09 09:09:09'"))],
             {'nullable': False},
             "TIMESTAMP NOT NULL DEFAULT '1999-09-09 09:09:09'"),

            ([mysql.MSTimeStamp(),
              DefaultClause(sql.text("'1999-09-09 09:09:09'"))],
             {},
             "TIMESTAMP NULL DEFAULT '1999-09-09 09:09:09'"),

            ([mysql.MSTimeStamp(),
              DefaultClause(sql.text(
                  "'1999-09-09 09:09:09' "
                  "ON UPDATE CURRENT_TIMESTAMP"))],
             {},
             "TIMESTAMP NULL DEFAULT '1999-09-09 09:09:09' "
             "ON UPDATE CURRENT_TIMESTAMP"),

            ([mysql.MSTimeStamp,
              DefaultClause(sql.text(
                  "'1999-09-09 09:09:09' "
                  "ON UPDATE CURRENT_TIMESTAMP"))],
             {'nullable': False},
             "TIMESTAMP NOT NULL DEFAULT '1999-09-09 09:09:09' "
             "ON UPDATE CURRENT_TIMESTAMP"),

            ([mysql.MSTimeStamp(),
              DefaultClause(sql.text(
                  "CURRENT_TIMESTAMP "
                  "ON UPDATE CURRENT_TIMESTAMP"))],
             {},
             "TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP "
             "ON UPDATE CURRENT_TIMESTAMP"),

            ([mysql.MSTimeStamp,
              DefaultClause(sql.text(
                  "CURRENT_TIMESTAMP "
                  "ON UPDATE CURRENT_TIMESTAMP"))],
             {'nullable': False},
             "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP "
             "ON UPDATE CURRENT_TIMESTAMP"),
        ]
        for spec, kw, expected in columns:
            c = Column('t', *spec, **kw)
            Table('t', MetaData(), c)
            self.assert_compile(
                schema.CreateColumn(c),
                "t %s" % expected

            )

    @testing.provide_metadata
    def test_timestamp_nullable(self):
        ts_table = Table(
            'mysql_timestamp', self.metadata,
            Column('t1', TIMESTAMP),
            Column('t2', TIMESTAMP, nullable=False),
            mysql_engine='InnoDB'
        )
        self.metadata.create_all()

        # TIMESTAMP without NULL inserts current time when passed
        # NULL.  when not passed, generates 0000-00-00 quite
        # annoyingly.
        # the flag http://dev.mysql.com/doc/refman/5.6/en/\
        # server-system-variables.html#sysvar_explicit_defaults_for_timestamp
        # changes this for 5.6 if set.

        # normalize dates that are over the second boundary
        def normalize(dt):
            if dt is None:
                return None
            elif (dt - now).seconds < 5:
                return now
            else:
                return dt

        with testing.db.begin() as conn:
            now = conn.scalar("select now()")

            conn.execute(
                ts_table.insert(), {'t1': now, 't2': None})
            conn.execute(
                ts_table.insert(), {'t1': None, 't2': None})
            conn.execute(
                ts_table.insert(), {'t2': None})

            eq_(
                [tuple([normalize(dt) for dt in row])
                 for row in conn.execute(ts_table.select())],
                [
                    (now, now),
                    (None, now),
                    (None, now)
                ]
            )

    def test_datetime_generic(self):
        self.assert_compile(
                mysql.DATETIME(),
                "DATETIME"
        )

    def test_datetime_fsp(self):
        self.assert_compile(
                mysql.DATETIME(fsp=4),
                "DATETIME(4)"
        )

    def test_time_generic(self):
        """"Exercise TIME."""

        self.assert_compile(
                mysql.TIME(),
                "TIME"
        )

    def test_time_fsp(self):
        self.assert_compile(
                mysql.TIME(fsp=5),
                "TIME(5)"
        )

    def test_time_result_processor(self):
        eq_(
            mysql.TIME().result_processor(None, None)(
                    datetime.timedelta(seconds=35, minutes=517,
                            microseconds=450
                    )),
            datetime.time(8, 37, 35, 450)
        )

    @testing.fails_on("mysql+oursql", "TODO: probable OurSQL bug")
    @testing.provide_metadata
    def test_time_roundtrip(self):
        t = Table('mysql_time', self.metadata,
                Column('t1', mysql.TIME())
            )
        t.create()
        t.insert().values(t1=datetime.time(8, 37, 35)).execute()
        eq_(select([t.c.t1]).scalar(), datetime.time(8, 37, 35))

    @testing.provide_metadata
    def test_year(self):
        """Exercise YEAR."""

        year_table = Table('mysql_year', self.metadata,
                           Column('y1', mysql.MSYear),
                           Column('y2', mysql.MSYear),
                           Column('y3', mysql.MSYear),
                           Column('y5', mysql.MSYear(4)))

        for col in year_table.c:
            self.assert_(repr(col))
        year_table.create()
        reflected = Table('mysql_year', MetaData(testing.db),
                          autoload=True)

        for table in year_table, reflected:
            table.insert(['1950', '50', None, 1950]).execute()
            row = table.select().execute().first()
            eq_(list(row), [1950, 2050, None, 1950])
            table.delete().execute()
            self.assert_(colspec(table.c.y1).startswith('y1 YEAR'))
            eq_(colspec(table.c.y5), 'y5 YEAR(4)')


class EnumSetTest(
        fixtures.TestBase, AssertsExecutionResults, AssertsCompiledSQL):

    __only_on__ = 'mysql'
    __dialect__ = mysql.dialect()
    __backend__ = True

    @testing.provide_metadata
    def test_enum(self):
        """Exercise the ENUM type."""

        with testing.expect_deprecated('Manually quoting ENUM value literals'):
            e1, e2 = mysql.ENUM("'a'", "'b'"), mysql.ENUM("'a'", "'b'")
            e3 = mysql.ENUM("'a'", "'b'", strict=True)
            e4 = mysql.ENUM("'a'", "'b'", strict=True)

        enum_table = Table(
            'mysql_enum', self.metadata,
            Column('e1', e1),
            Column('e2', e2, nullable=False),
            Column('e2generic', Enum("a", "b"), nullable=False),
            Column('e3', e3),
            Column('e4', e4,
                   nullable=False),
            Column('e5', mysql.ENUM("a", "b")),
            Column('e5generic', Enum("a", "b")),
            Column('e6', mysql.ENUM("'a'", "b")),
        )

        eq_(
            colspec(enum_table.c.e1),
            "e1 ENUM('a','b')")
        eq_(
            colspec(enum_table.c.e2),
            "e2 ENUM('a','b') NOT NULL")
        eq_(
            colspec(enum_table.c.e2generic),
            "e2generic ENUM('a','b') NOT NULL")
        eq_(
            colspec(enum_table.c.e3),
            "e3 ENUM('a','b')")
        eq_(
            colspec(enum_table.c.e4),
            "e4 ENUM('a','b') NOT NULL")
        eq_(
            colspec(enum_table.c.e5),
            "e5 ENUM('a','b')")
        eq_(
            colspec(enum_table.c.e5generic),
            "e5generic ENUM('a','b')")
        eq_(
            colspec(enum_table.c.e6),
            "e6 ENUM('''a''','b')")
        enum_table.create()

        assert_raises(
            exc.DBAPIError, enum_table.insert().execute,
            e1=None, e2=None, e3=None, e4=None)

        assert_raises(
            exc.StatementError,
            enum_table.insert().execute,
            e1='c', e2='c', e2generic='c', e3='c',
            e4='c', e5='c', e5generic='c', e6='c')

        enum_table.insert().execute()
        enum_table.insert().execute(e1='a', e2='a', e2generic='a', e3='a',
                                    e4='a', e5='a', e5generic='a', e6="'a'")
        enum_table.insert().execute(e1='b', e2='b', e2generic='b', e3='b',
                                    e4='b', e5='b', e5generic='b', e6='b')

        res = enum_table.select().execute().fetchall()

        expected = [(None, 'a', 'a', None, 'a', None, None, None),
                    ('a', 'a', 'a', 'a', 'a', 'a', 'a', "'a'"),
                    ('b', 'b', 'b', 'b', 'b', 'b', 'b', 'b')]

        eq_(res, expected)

    def _set_fixture_one(self):
        with testing.expect_deprecated('Manually quoting SET value literals'):
            e1, e2 = mysql.SET("'a'", "'b'"), mysql.SET("'a'", "'b'")
            e4 = mysql.SET("'a'", "b")
            e5 = mysql.SET("'a'", "'b'", quoting="quoted")

        set_table = Table(
            'mysql_set', self.metadata,
            Column('e1', e1),
            Column('e2', e2, nullable=False),
            Column('e3', mysql.SET("a", "b")),
            Column('e4', e4),
            Column('e5', e5)
        )
        return set_table

    def test_set_colspec(self):
        self.metadata = MetaData()
        set_table = self._set_fixture_one()
        eq_(
            colspec(set_table.c.e1),
            "e1 SET('a','b')")
        eq_(colspec(
            set_table.c.e2),
            "e2 SET('a','b') NOT NULL")
        eq_(
            colspec(set_table.c.e3),
            "e3 SET('a','b')")
        eq_(
            colspec(set_table.c.e4),
            "e4 SET('''a''','b')")
        eq_(
            colspec(set_table.c.e5),
            "e5 SET('a','b')")

    @testing.provide_metadata
    def test_no_null(self):
        set_table = self._set_fixture_one()
        set_table.create()
        assert_raises(
            exc.DBAPIError, set_table.insert().execute,
            e1=None, e2=None, e3=None, e4=None)

    @testing.only_on('+oursql')
    @testing.provide_metadata
    def test_oursql_error_one(self):
        set_table = self._set_fixture_one()
        set_table.create()
        assert_raises(
            exc.StatementError, set_table.insert().execute,
            e1='c', e2='c', e3='c', e4='c')

    @testing.fails_on("+oursql", "oursql raises on the truncate warning")
    @testing.provide_metadata
    def test_empty_set_no_empty_string(self):
        t = Table(
            't', self.metadata,
            Column('id', Integer),
            Column('data', mysql.SET("a", "b"))
        )
        t.create()
        with testing.db.begin() as conn:
            conn.execute(
                t.insert(),
                {'id': 1, 'data': set()},
                {'id': 2, 'data': set([''])},
                {'id': 3, 'data': set(['a', ''])},
                {'id': 4, 'data': set(['b'])},
            )
            eq_(
                conn.execute(t.select().order_by(t.c.id)).fetchall(),
                [
                    (1, set()),
                    (2, set()),
                    (3, set(['a'])),
                    (4, set(['b'])),
                ]
            )

    def test_bitwise_required_for_empty(self):
        assert_raises_message(
            exc.ArgumentError,
            "Can't use the blank value '' in a SET without setting "
            "retrieve_as_bitwise=True",
            mysql.SET, "a", "b", ''
        )

    @testing.provide_metadata
    def test_empty_set_empty_string(self):
        t = Table(
            't', self.metadata,
            Column('id', Integer),
            Column('data', mysql.SET("a", "b", '', retrieve_as_bitwise=True))
        )
        t.create()
        with testing.db.begin() as conn:
            conn.execute(
                t.insert(),
                {'id': 1, 'data': set()},
                {'id': 2, 'data': set([''])},
                {'id': 3, 'data': set(['a', ''])},
                {'id': 4, 'data': set(['b'])},
            )
            eq_(
                conn.execute(t.select().order_by(t.c.id)).fetchall(),
                [
                    (1, set()),
                    (2, set([''])),
                    (3, set(['a', ''])),
                    (4, set(['b'])),
                ]
            )

    @testing.provide_metadata
    def test_string_roundtrip(self):
        set_table = self._set_fixture_one()
        set_table.create()
        with testing.db.begin() as conn:
            conn.execute(
                set_table.insert(),
                dict(e1='a', e2='a', e3='a', e4="'a'", e5="a,b"))
            conn.execute(
                set_table.insert(),
                dict(e1='b', e2='b', e3='b', e4='b', e5="a,b"))

            expected = [
                (set(['a']), set(['a']), set(['a']),
                 set(["'a'"]), set(['a', 'b'])),
                (set(['b']), set(['b']), set(['b']),
                 set(['b']), set(['a', 'b']))
            ]
            res = conn.execute(
                set_table.select()
            ).fetchall()

            eq_(res, expected)

    @testing.provide_metadata
    def test_unicode_roundtrip(self):
        set_table = Table(
            't', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('data', mysql.SET(
                u('réveillé'), u('drôle'), u('S’il'), convert_unicode=True)),
        )

        set_table.create()
        with testing.db.begin() as conn:
            conn.execute(
                set_table.insert(),
                {"data": set([u('réveillé'), u('drôle')])})

            row = conn.execute(
                set_table.select()
            ).first()

            eq_(
                row,
                (1, set([u('réveillé'), u('drôle')]))
            )

    @testing.provide_metadata
    def test_int_roundtrip(self):
        set_table = self._set_fixture_one()
        set_table.create()
        with testing.db.begin() as conn:
            conn.execute(
                set_table.insert(),
                dict(e1=1, e2=2, e3=3, e4=3, e5=0)
            )
            res = conn.execute(set_table.select()).first()
            eq_(
                res,
                (
                    set(['a']), set(['b']), set(['a', 'b']),
                    set(["'a'", 'b']), set([]))
            )

    @testing.provide_metadata
    def test_set_roundtrip_plus_reflection(self):
        set_table = Table(
            'mysql_set', self.metadata,
            Column('s1', mysql.SET("dq", "sq")),
            Column('s2', mysql.SET("a")),
            Column('s3', mysql.SET("5", "7", "9")))

        eq_(colspec(set_table.c.s1), "s1 SET('dq','sq')")
        eq_(colspec(set_table.c.s2), "s2 SET('a')")
        eq_(colspec(set_table.c.s3), "s3 SET('5','7','9')")
        set_table.create()
        reflected = Table('mysql_set', MetaData(testing.db),
                          autoload=True)
        for table in set_table, reflected:

            def roundtrip(store, expected=None):
                expected = expected or store
                table.insert(store).execute()
                row = table.select().execute().first()
                eq_(row, tuple(expected))
                table.delete().execute()

            roundtrip([None, None, None], [None] * 3)
            roundtrip(['', '', ''], [set([])] * 3)
            roundtrip([set(['dq']), set(['a']), set(['5'])])
            roundtrip(['dq', 'a', '5'], [set(['dq']), set(['a']),
                      set(['5'])])
            roundtrip([1, 1, 1], [set(['dq']), set(['a']), set(['5'])])
            roundtrip([set(['dq', 'sq']), None, set(['9', '5', '7'])])
        set_table.insert().execute(
            {'s3': set(['5'])},
            {'s3': set(['5', '7'])},
            {'s3': set(['5', '7', '9'])},
            {'s3': set(['7', '9'])})

        rows = select(
            [set_table.c.s3],
            set_table.c.s3.in_([set(['5']), ['5', '7']])
        ).execute().fetchall()
        found = set([frozenset(row[0]) for row in rows])
        eq_(found, set([frozenset(['5']), frozenset(['5', '7'])]))

    @testing.provide_metadata
    def test_unicode_enum(self):
        metadata = self.metadata
        t1 = Table(
            'table', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', Enum(u('réveillé'), u('drôle'), u('S’il'))),
            Column('value2', mysql.ENUM(u('réveillé'), u('drôle'), u('S’il')))
        )
        metadata.create_all()
        t1.insert().execute(value=u('drôle'), value2=u('drôle'))
        t1.insert().execute(value=u('réveillé'), value2=u('réveillé'))
        t1.insert().execute(value=u('S’il'), value2=u('S’il'))
        eq_(t1.select().order_by(t1.c.id).execute().fetchall(),
            [
                (1, u('drôle'), u('drôle')),
                (2, u('réveillé'), u('réveillé')),
                (3, u('S’il'), u('S’il'))
            ])

        # test reflection of the enum labels

        m2 = MetaData(testing.db)
        t2 = Table('table', m2, autoload=True)

        # TODO: what's wrong with the last element ?  is there
        # latin-1 stuff forcing its way in ?

        eq_(
            t2.c.value.type.enums[0:2],
            (u('réveillé'), u('drôle'))  # u'S’il') # eh ?
        )

        eq_(
            t2.c.value2.type.enums[0:2],
            (u('réveillé'), u('drôle'))  # u'S’il') # eh ?
        )

    def test_enum_compile(self):
        e1 = Enum('x', 'y', 'z', name='somename')
        t1 = Table('sometable', MetaData(), Column('somecolumn', e1))
        self.assert_compile(schema.CreateTable(t1),
                            "CREATE TABLE sometable (somecolumn "
                            "ENUM('x','y','z'))")
        t1 = Table('sometable', MetaData(), Column('somecolumn',
                   Enum('x', 'y', 'z', native_enum=False)))
        self.assert_compile(schema.CreateTable(t1),
                            "CREATE TABLE sometable (somecolumn "
                            "VARCHAR(1), CHECK (somecolumn IN ('x', "
                            "'y', 'z')))")

    @testing.provide_metadata
    @testing.exclude('mysql', '<', (4,), "3.23 can't handle an ENUM of ''")
    def test_enum_parse(self):

        with testing.expect_deprecated('Manually quoting ENUM value literals'):
            enum_table = Table(
                'mysql_enum', self.metadata,
                Column('e1', mysql.ENUM("'a'")),
                Column('e2', mysql.ENUM("''")),
                Column('e3', mysql.ENUM('a')),
                Column('e4', mysql.ENUM('')),
                Column('e5', mysql.ENUM("'a'", "''")),
                Column('e6', mysql.ENUM("''", "'a'")),
                Column('e7', mysql.ENUM("''", "'''a'''", "'b''b'", "''''")))

        for col in enum_table.c:
            self.assert_(repr(col))

        enum_table.create()
        reflected = Table('mysql_enum', MetaData(testing.db),
                          autoload=True)
        for t in enum_table, reflected:
            eq_(t.c.e1.type.enums, ("a",))
            eq_(t.c.e2.type.enums, ("",))
            eq_(t.c.e3.type.enums, ("a",))
            eq_(t.c.e4.type.enums, ("",))
            eq_(t.c.e5.type.enums, ("a", ""))
            eq_(t.c.e6.type.enums, ("", "a"))
            eq_(t.c.e7.type.enums, ("", "'a'", "b'b", "'"))

    @testing.provide_metadata
    @testing.exclude('mysql', '<', (5,))
    def test_set_parse(self):
        with testing.expect_deprecated('Manually quoting SET value literals'):
            set_table = Table(
                'mysql_set', self.metadata,
                Column('e1', mysql.SET("'a'")),
                Column('e2', mysql.SET("''", retrieve_as_bitwise=True)),
                Column('e3', mysql.SET('a')),
                Column('e4', mysql.SET('', retrieve_as_bitwise=True)),
                Column('e5', mysql.SET("'a'", "''", retrieve_as_bitwise=True)),
                Column('e6', mysql.SET("''", "'a'", retrieve_as_bitwise=True)),
                Column('e7', mysql.SET(
                    "''", "'''a'''", "'b''b'", "''''",
                    retrieve_as_bitwise=True)))

        for col in set_table.c:
            self.assert_(repr(col))

        set_table.create()

        # don't want any warnings on reflection
        reflected = Table('mysql_set', MetaData(testing.db),
                          autoload=True)
        for t in set_table, reflected:
            eq_(t.c.e1.type.values, ("a",))
            eq_(t.c.e2.type.values, ("",))
            eq_(t.c.e3.type.values, ("a",))
            eq_(t.c.e4.type.values, ("",))
            eq_(t.c.e5.type.values, ("a", ""))
            eq_(t.c.e6.type.values, ("", "a"))
            eq_(t.c.e7.type.values, ("", "'a'", "b'b", "'"))


def colspec(c):
    return testing.db.dialect.ddl_compiler(
        testing.db.dialect, None).get_column_specification(c)


class JSONTest(AssertsCompiledSQL, fixtures.TestBase):
    __only_on__ = ('mysql >= 5.7.9',)
    __dialect__ = mysql.dialect()

    def setup(self):
        metadata = MetaData()
        self.test_table = Table('test_table', metadata,
                                Column('id', Integer, primary_key=True),
                                Column('test_column', JSON),
                                )
        self.jsoncol = self.test_table.c.test_column
        self.ids = self.test_table.c.id

    def _test_where(self, whereclause, expected):
        stmt = select([self.test_table]).where(whereclause)
        self.assert_compile(
            stmt,
            "SELECT test_table.id, test_table.test_column FROM test_table "
            "WHERE %s" % expected
        )

    def _test_cols(self, colclause, expected, from_=True):
        stmt = select([colclause])
        self.assert_compile(
            stmt,
            (
                "SELECT %s" +
                (" FROM test_table" if from_ else "")
            ) % expected
        )

    def test_bind_serialize_default(self):
        dialect = mysql.dialect()
        proc = self.test_table.c.test_column.type._cached_bind_processor(
            dialect)
        eq_(
            proc({"A": [1, 2, 3, True, False]}),
            '{"A": [1, 2, 3, true, false]}'
        )

    def test_bind_serialize_none(self):
        dialect = mysql.dialect()
        proc = self.test_table.c.test_column.type._cached_bind_processor(
            dialect)
        eq_(
            proc(None),
            'null'
        )

    def test_bind_serialize_none_as_null(self):
        dialect = mysql.dialect()
        proc = JSON(none_as_null=True)._cached_bind_processor(
            dialect)
        eq_(
            proc(None),
            None
        )
        eq_(
            proc(null()),
            None
        )

    def test_bind_serialize_null(self):
        dialect = mysql.dialect()
        proc = self.test_table.c.test_column.type._cached_bind_processor(
            dialect)
        eq_(
            proc(null()),
            None
        )

    def test_result_deserialize_default(self):
        dialect = mysql.dialect()
        proc = self.test_table.c.test_column.type._cached_result_processor(
            dialect, None)
        eq_(
            proc('{"A": [1, 2, 3, true, false]}'),
            {"A": [1, 2, 3, True, False]}
        )

    def test_result_deserialize_null(self):
        dialect = mysql.dialect()
        proc = self.test_table.c.test_column.type._cached_result_processor(
            dialect, None)
        eq_(
            proc('null'),
            None
        )

    def test_result_deserialize_None(self):
        dialect = mysql.dialect()
        proc = self.test_table.c.test_column.type._cached_result_processor(
            dialect, None)
        eq_(
            proc(None),
            None
        )

    # This test is a bit misleading -- in real life you will need to cast to
    # do anything
    def test_where_getitem(self):
        self._test_where(
            self.jsoncol['bar'][1] == None,
            "JSON_EXTRACT(test_table.test_column, %s) IS NULL"
        )

    def test_where_path(self):
        self._test_where(
            self.jsoncol[("foo", 1)] == None,
            "JSON_EXTRACT(test_table.test_column, %s) IS NULL"
        )

    def test_path_typing(self):
        col = column('x', JSON())
        is_(
            col['q'].type._type_affinity, JSON
        )
        is_(
            col[('q', )].type._type_affinity, JSON
        )
        is_(
            col['q']['p'].type._type_affinity, JSON
        )
        is_(
            col[('q', 'p')].type._type_affinity, JSON
        )

    def test_where_getitem_json_cast(self):
        self._test_where(
            self.jsoncol['bar'].cast(Integer) == 5,
            "CAST(JSON_EXTRACT(test_table.test_column, %s) AS SIGNED INTEGER) "
            "= %s"
        )

    def test_cols_get(self):
        self._test_cols(
            self.jsoncol['foo'],
            "JSON_EXTRACT(test_table.test_column, %s) AS `JSON_EXTRACT_1`",
            True
        )

class JSONRoundTripTest(fixtures.TablesTest):
    __only_on__ = ('mysql >= 5.7.9',)
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table('data_table', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(30), nullable=False),
              Column('data', JSON),
              Column('nulldata', JSON(none_as_null=True))
              )

    def _fixture_data(self, engine):
        data_table = self.tables.data_table
        engine.execute(
            data_table.insert(),
            {'name': 'r1', 'data': {"k1": "r1v1", "k2": "r1v2"}},
            {'name': 'r2', 'data': {"k1": "r2v1", "k2": "r2v2"}},
            {'name': 'r3', 'data': {"k1": "r3v1", "k2": "r3v2"}},
            {'name': 'r4', 'data': {"k1": "r4v1", "k2": "r4v2"}},
            {'name': 'r5', 'data': {"k1": "r5v1", "k2": "r5v2", "k3": 5}},
            {'name': 'r6', 'data': {"k1": {"r6v1": {'subr': [1, 2, 3]}}}},
            {'name': 'r7', 'data': [{"r7v1": 1}, {"r7v2": 2}, {"r7v3": 3}]},
        )

    def _assert_data(self, compare, engine, column='data'):
        col = self.tables.data_table.c[column]

        data = engine.execute(
            select([col]).
            order_by(self.tables.data_table.c.name)
        ).fetchall()
        eq_([d for d, in data], compare)

    def _assert_column_is_NULL(self, column='data'):
        col = self.tables.data_table.c[column]

        data = testing.db.execute(
            select([col]).
            where(col.is_(null()))
        ).fetchall()
        eq_([d for d, in data], [None])

    def _assert_column_is_JSON_NULL(self, column='data'):
        col = self.tables.data_table.c[column]

        data = testing.db.execute(
            select([col]).
            where(cast(col, String) == "null")
        ).fetchall()
        eq_([d for d, in data], [None])

    def test_insert(self):
        testing.db.execute(
            self.tables.data_table.insert(),
            {'name': 'r1', 'data': {"k1": "r1v1", "k2": "r1v2"}}
        )
        self._assert_data([{"k1": "r1v1", "k2": "r1v2"}], testing.db)

    def test_insert_nulls(self):
        testing.db.execute(
            self.tables.data_table.insert(),
            {'name': 'r1', 'data': null()}
        )
        self._assert_data([None], testing.db)

    def test_insert_none_as_null(self):
        testing.db.execute(
            self.tables.data_table.insert(),
            {'name': 'r1', 'nulldata': None}
        )
        self._assert_column_is_NULL(column='nulldata')

    def test_insert_nulljson_into_none_as_null(self):
        testing.db.execute(
            self.tables.data_table.insert(),
            {'name': 'r1', 'nulldata': JSON.NULL}
        )
        self._assert_column_is_JSON_NULL(column='nulldata')

    def test_reflect(self):
        insp = inspect(testing.db)
        cols = insp.get_columns('data_table')
        assert isinstance(cols[2]['type'], JSON)

    def test_custom_serialize_deserialize(self):
        import json

        def loads(value):
            value = json.loads(value)
            value['x'] += '_loads'
            return value

        def dumps(value):
            value = dict(value)
            value['x'] = 'dumps_y'
            return json.dumps(value)

        engine = engines.testing_engine(options=dict(
            json_serializer=dumps,
            json_deserializer=loads
        ))

        engine.execute(
            self.tables.data_table.insert(),
            {'name': 'r1', 'data': {"key": "value", "x": "q"}}
        )
        self._assert_data([{"key": "value", "x": "dumps_y_loads"}], engine)

    def test_attribute_query(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        result = testing.db.execute(
            select([data_table.c.name]).where(
                data_table.c.data.json.k1['r6v1'].subr == [1, 2, 3]
            )
        )
        eq_(result.scalar(), 'r6')

    def test_path_query_list(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        result = testing.db.execute(
            select([data_table.c.name]).where(
                data_table.c.data[('k1', 'r6v1', 'subr')] == [1, 2, 3]
            )
        )
        eq_(result.scalar(), 'r6')

    def test_path_query_dict(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        result = testing.db.execute(
            select([data_table.c.name]).where(
                data_table.c.data[('k1', 'r6v1')] == {'subr': [1, 2, 3]}
            )
        )
        eq_(result.scalar(), 'r6')

    def test_multi_index_query(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        result = testing.db.execute(
            select([data_table.c.name]).where(
                data_table.c.data['k1']['r6v1']['subr'] == [1, 2, 3]
            )
        )
        eq_(result.scalar(), 'r6')

    def test_wildcard_query(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        data = (
            (data_table.c.data['*']['%'], 'r7', [1, 2, 3]),
            (data_table.c.data['**.subr']['*'], 'r6', [1, 2, 3]),
            (data_table.c.data['**']['subr']['*'], 'r6', [1, 2, 3]),
        )
        for datum in data:
            result = testing.db.execute(
                select([datum[0]]).where(data_table.c.name == datum[1]
                )
            )
            eq_(result.scalar(), datum[2])

    def test_query_returned_as_int(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        result = testing.db.execute(
            select([data_table.c.data['k3'].cast(Integer)]).where(
                data_table.c.name == 'r5')
        ).first()
        assert isinstance(result[0], long)

    def test_criterion(self):
        self._fixture_data(testing.db)
        data_table = self.tables.data_table
        result = testing.db.execute(
            select([data_table.c.data]).where(
                data_table.c.data['k1'] == 'r3v1'
            )
        ).first()
        eq_(result, ({'k1': 'r3v1', 'k2': 'r3v2'},))

    def test_fixed_round_trip(self):
        doc = {
            "key": "value",
            "key2": {"k1": "v1", "k2": "v2"}
        }
        s = select([JSON.MySqlJsonDocument(doc)])
        eq_(
            testing.db.scalar(s),
            doc
        )

    def test_unicode_round_trip(self):
        doc = {
            "key": util.u('réveillé'),
            "data": {"k1": util.u('drôle')}
        }
        s = select([JSON.MySqlJsonDocument(doc)])
        eq_(
            testing.db.scalar(s),
            doc
        )

    def test_eval_none_flag_orm(self):
        Base = declarative_base()

        class Data(Base):
            __table__ = self.tables.data_table

        s = Session(testing.db)

        d1 = Data(name='d1', data=None, nulldata=None)
        s.add(d1)
        s.commit()

        s.bulk_insert_mappings(
            Data, [{"name": "d2", "data": None, "nulldata": None}]
        )
        eq_(
            s.query(
                cast(self.tables.data_table.c.data, String),
                cast(self.tables.data_table.c.nulldata, String)
            ).filter(self.tables.data_table.c.name == 'd1').first(),
            ("null", None)
        )
        eq_(
            s.query(
                cast(self.tables.data_table.c.data, String),
                cast(self.tables.data_table.c.nulldata, String)
            ).filter(self.tables.data_table.c.name == 'd2').first(),
            ("null", None)
        )

# ::TODO:: postgres jsonb tests have tests for contains/contained/etc...
#