# coding: utf-8

from sqlalchemy.testing import eq_, assert_raises
from sqlalchemy import *
from sqlalchemy import sql, exc, schema
from sqlalchemy.util import u
from sqlalchemy import util
from sqlalchemy.dialects.mysql import base as mysql
from sqlalchemy.testing import fixtures, AssertsCompiledSQL, AssertsExecutionResults
from sqlalchemy import testing
from sqlalchemy.testing.engines import utf8_engine
import datetime
import decimal

class TypesTest(fixtures.TestBase, AssertsExecutionResults, AssertsCompiledSQL):
    "Test MySQL column types"

    __dialect__ = mysql.dialect()

    def test_numeric(self):
        "Exercise type specification and options for numeric types."

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

    @testing.only_if('mysql')
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

    @testing.only_if('mysql')
    @testing.exclude('mysql', '<', (5, 0, 5), 'a 5.0+ feature')
    @testing.fails_if(
            lambda: testing.against("mysql+oursql") and util.py3k,
            'some round trips fail, oursql bug ?')
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

    @testing.only_if('mysql')
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

    def test_timestamp(self):
        """Exercise funky TIMESTAMP default syntax."""

        columns = [
            ([TIMESTAMP],
             'TIMESTAMP NULL'),
            ([mysql.MSTimeStamp],
             'TIMESTAMP NULL'),
            ([mysql.MSTimeStamp,
              DefaultClause(sql.text('CURRENT_TIMESTAMP'))],
             "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ([mysql.MSTimeStamp,
              DefaultClause(sql.text("'1999-09-09 09:09:09'"))],
             "TIMESTAMP DEFAULT '1999-09-09 09:09:09'"),
            ([mysql.MSTimeStamp,
              DefaultClause(sql.text("'1999-09-09 09:09:09' "
                                      "ON UPDATE CURRENT_TIMESTAMP"))],
             "TIMESTAMP DEFAULT '1999-09-09 09:09:09' "
             "ON UPDATE CURRENT_TIMESTAMP"),
            ([mysql.MSTimeStamp,
              DefaultClause(sql.text("CURRENT_TIMESTAMP "
                                      "ON UPDATE CURRENT_TIMESTAMP"))],
             "TIMESTAMP DEFAULT CURRENT_TIMESTAMP "
             "ON UPDATE CURRENT_TIMESTAMP"),
            ]
        for spec, expected in columns:
            c = Column('t', *spec)
            Table('t', MetaData(), c)
            self.assert_compile(
                schema.CreateColumn(c),
                "t %s" % expected

            )

    @testing.only_if('mysql')
    @testing.provide_metadata
    def test_timestamp_nullable(self):
        ts_table = Table('mysql_timestamp', self.metadata,
                            Column('t1', TIMESTAMP),
                            Column('t2', TIMESTAMP, nullable=False),
                    )
        self.metadata.create_all()

        now = testing.db.execute("select now()").scalar()

        # TIMESTAMP without NULL inserts current time when passed
        # NULL.  when not passed, generates 0000-00-00 quite
        # annoyingly.
        ts_table.insert().execute({'t1': now, 't2': None})
        ts_table.insert().execute({'t1': None, 't2': None})

        # normalize dates that are over the second boundary
        def normalize(dt):
            if dt is None:
                return None
            elif (dt - now).seconds < 5:
                return now
            else:
                return dt
        eq_(
            [tuple([normalize(dt) for dt in row])
            for row in ts_table.select().execute()],
            [(now, now), (None, now)]
        )

    def test_time(self):
        """"Exercise TIME."""

        self.assert_compile(
                mysql.TIME(),
                "TIME"
        )

        self.assert_compile(
                mysql.TIME(fsp=5),
                "TIME(5)"
        )

        eq_(
            mysql.TIME().result_processor(None, None)(
                    datetime.timedelta(seconds=35, minutes=517,
                            microseconds=450
                    )),
            datetime.time(8, 37, 35, 450)
        )

    @testing.only_if('mysql')
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


class EnumSetTest(fixtures.TestBase, AssertsExecutionResults, AssertsCompiledSQL):

    __only_on__ = 'mysql'
    __dialect__ = mysql.dialect()


    @testing.provide_metadata
    def test_enum(self):
        """Exercise the ENUM type."""

        with testing.expect_deprecated('Manually quoting ENUM value literals'):
            e1, e2 = mysql.ENUM("'a'", "'b'"), mysql.ENUM("'a'", "'b'")

        enum_table = Table('mysql_enum', self.metadata,
            Column('e1', e1),
            Column('e2', e2, nullable=False),
            Column('e2generic', Enum("a", "b"), nullable=False),
            Column('e3', mysql.ENUM("'a'", "'b'", strict=True)),
            Column('e4', mysql.ENUM("'a'", "'b'", strict=True),
                   nullable=False),
            Column('e5', mysql.ENUM("a", "b")),
            Column('e5generic', Enum("a", "b")),
            Column('e6', mysql.ENUM("'a'", "b")),
            )

        eq_(colspec(enum_table.c.e1),
                       "e1 ENUM('a','b')")
        eq_(colspec(enum_table.c.e2),
                       "e2 ENUM('a','b') NOT NULL")
        eq_(colspec(enum_table.c.e2generic),
                      "e2generic ENUM('a','b') NOT NULL")
        eq_(colspec(enum_table.c.e3),
                       "e3 ENUM('a','b')")
        eq_(colspec(enum_table.c.e4),
                       "e4 ENUM('a','b') NOT NULL")
        eq_(colspec(enum_table.c.e5),
                       "e5 ENUM('a','b')")
        eq_(colspec(enum_table.c.e5generic),
                      "e5generic ENUM('a','b')")
        eq_(colspec(enum_table.c.e6),
                       "e6 ENUM('''a''','b')")
        enum_table.create()

        assert_raises(exc.DBAPIError, enum_table.insert().execute,
                        e1=None, e2=None, e3=None, e4=None)

        assert_raises(exc.StatementError, enum_table.insert().execute,
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

    @testing.provide_metadata
    def test_set(self):

        with testing.expect_deprecated('Manually quoting SET value literals'):
            e1, e2 = mysql.SET("'a'", "'b'"), mysql.SET("'a'", "'b'")

        set_table = Table('mysql_set', self.metadata,
            Column('e1', e1),
            Column('e2', e2, nullable=False),
            Column('e3', mysql.SET("a", "b")),
            Column('e4', mysql.SET("'a'", "b")),
            Column('e5', mysql.SET("'a'", "'b'", quoting="quoted"))
            )

        eq_(colspec(set_table.c.e1),
                       "e1 SET('a','b')")
        eq_(colspec(set_table.c.e2),
                       "e2 SET('a','b') NOT NULL")
        eq_(colspec(set_table.c.e3),
                       "e3 SET('a','b')")
        eq_(colspec(set_table.c.e4),
                       "e4 SET('''a''','b')")
        eq_(colspec(set_table.c.e5),
                       "e5 SET('a','b')")
        set_table.create()

        assert_raises(exc.DBAPIError, set_table.insert().execute,
                        e1=None, e2=None, e3=None, e4=None)

        if testing.against("+oursql"):
            assert_raises(exc.StatementError, set_table.insert().execute,
                                        e1='c', e2='c', e3='c', e4='c')

        set_table.insert().execute(e1='a', e2='a', e3='a', e4="'a'", e5="a,b")
        set_table.insert().execute(e1='b', e2='b', e3='b', e4='b', e5="a,b")

        res = set_table.select().execute().fetchall()

        if testing.against("+oursql"):
            expected = [
                # 1st row with all c's, data truncated
                (set(['']), set(['']), set(['']), set(['']), None),
            ]
        else:
            expected = []

        expected.extend([
            (set(['a']), set(['a']), set(['a']), set(["'a'"]), set(['a', 'b'])),
            (set(['b']), set(['b']), set(['b']), set(['b']), set(['a', 'b']))
        ])

        eq_(res, expected)

    @testing.provide_metadata
    def test_set_roundtrip_plus_reflection(self):
        set_table = Table('mysql_set', self.metadata,
                        Column('s1',
                          mysql.SET("dq", "sq")),
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
                self.assert_(list(row) == expected)
                table.delete().execute()

            roundtrip([None, None, None], [None] * 3)
            roundtrip(['', '', ''], [set([''])] * 3)
            roundtrip([set(['dq']), set(['a']), set(['5'])])
            roundtrip(['dq', 'a', '5'], [set(['dq']), set(['a']),
                      set(['5'])])
            roundtrip([1, 1, 1], [set(['dq']), set(['a']), set(['5'
                      ])])
            roundtrip([set(['dq', 'sq']), None, set(['9', '5', '7'
                      ])])
        set_table.insert().execute({'s3': set(['5'])},
                {'s3': set(['5', '7'])}, {'s3': set(['5', '7', '9'])},
                {'s3': set(['7', '9'])})

        # NOTE: the string sent to MySQL here is sensitive to ordering.
        # for some reason the set ordering is always "5, 7" when we test on
        # MySQLdb but in Py3K this is not guaranteed.   So basically our
        # SET type doesn't do ordering correctly (not sure how it can,
        # as we don't know how the SET was configured in the first place.)
        rows = select([set_table.c.s3],
                    set_table.c.s3.in_([set(['5']), ['5', '7']])
                        ).execute().fetchall()
        found = set([frozenset(row[0]) for row in rows])
        eq_(found, set([frozenset(['5']), frozenset(['5', '7'])]))

    def test_unicode_enum(self):
        unicode_engine = utf8_engine()
        metadata = MetaData(unicode_engine)
        t1 = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', Enum(u('réveillé'), u('drôle'), u('S’il'))),
            Column('value2', mysql.ENUM(u('réveillé'), u('drôle'), u('S’il')))
        )
        metadata.create_all()
        try:
            t1.insert().execute(value=u('drôle'), value2=u('drôle'))
            t1.insert().execute(value=u('réveillé'), value2=u('réveillé'))
            t1.insert().execute(value=u('S’il'), value2=u('S’il'))
            eq_(t1.select().order_by(t1.c.id).execute().fetchall(),
                [(1, u('drôle'), u('drôle')), (2, u('réveillé'), u('réveillé')),
                            (3, u('S’il'), u('S’il'))]
            )

            # test reflection of the enum labels

            m2 = MetaData(testing.db)
            t2 = Table('table', m2, autoload=True)

            # TODO: what's wrong with the last element ?  is there
            # latin-1 stuff forcing its way in ?

            assert t2.c.value.type.enums[0:2] == \
                    (u('réveillé'), u('drôle'))  # u'S’il') # eh ?

            assert t2.c.value2.type.enums[0:2] == \
                    (u('réveillé'), u('drôle'))  # u'S’il') # eh ?
        finally:
            metadata.drop_all()

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
            enum_table = Table('mysql_enum', self.metadata,
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
            set_table = Table('mysql_set', self.metadata,
                Column('e1', mysql.SET("'a'")),
                Column('e2', mysql.SET("''")),
                Column('e3', mysql.SET('a')),
                Column('e4', mysql.SET('')),
                Column('e5', mysql.SET("'a'", "''")),
                Column('e6', mysql.SET("''", "'a'")),
                Column('e7', mysql.SET("''", "'''a'''", "'b''b'", "''''")))

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

