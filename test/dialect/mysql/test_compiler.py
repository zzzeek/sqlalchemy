# coding: utf-8

from sqlalchemy.testing import eq_, assert_raises_message
from sqlalchemy import *
from sqlalchemy import sql, exc, schema, types as sqltypes
from sqlalchemy.dialects.mysql import base as mysql
from sqlalchemy.testing import fixtures, AssertsCompiledSQL
from sqlalchemy import testing
from sqlalchemy.sql import table, column

class CompileTest(fixtures.TestBase, AssertsCompiledSQL):

    __dialect__ = mysql.dialect()

    def test_reserved_words(self):
        table = Table("mysql_table", MetaData(),
            Column("col1", Integer),
            Column("master_ssl_verify_server_cert", Integer))
        x = select([table.c.col1, table.c.master_ssl_verify_server_cert])

        self.assert_compile(x,
            "SELECT mysql_table.col1, "
            "mysql_table.`master_ssl_verify_server_cert` FROM mysql_table")

    def test_create_index_simple(self):
        m = MetaData()
        tbl = Table('testtbl', m, Column('data', String(255)))
        idx = Index('test_idx1', tbl.c.data)

        self.assert_compile(schema.CreateIndex(idx),
            'CREATE INDEX test_idx1 ON testtbl (data)')

    def test_create_index_with_length(self):
        m = MetaData()
        tbl = Table('testtbl', m, Column('data', String(255)))
        idx1 = Index('test_idx1', tbl.c.data, mysql_length=10)
        idx2 = Index('test_idx2', tbl.c.data, mysql_length=5)

        self.assert_compile(schema.CreateIndex(idx1),
            'CREATE INDEX test_idx1 ON testtbl (data(10))')
        self.assert_compile(schema.CreateIndex(idx2),
            'CREATE INDEX test_idx2 ON testtbl (data(5))')

    def test_create_composite_index_with_length(self):
        m = MetaData()
        tbl = Table('testtbl', m,
                    Column('a', String(255)),
                    Column('b', String(255)))

        idx1 = Index('test_idx1', tbl.c.a, tbl.c.b,
                     mysql_length={'a': 10, 'b': 20})
        idx2 = Index('test_idx2', tbl.c.a, tbl.c.b,
                     mysql_length={'a': 15})
        idx3 = Index('test_idx3', tbl.c.a, tbl.c.b,
                     mysql_length=30)

        self.assert_compile(
            schema.CreateIndex(idx1),
            'CREATE INDEX test_idx1 ON testtbl (a(10), b(20))'
        )
        self.assert_compile(
            schema.CreateIndex(idx2),
            'CREATE INDEX test_idx2 ON testtbl (a(15), b)'
        )
        self.assert_compile(
            schema.CreateIndex(idx3),
            'CREATE INDEX test_idx3 ON testtbl (a(30), b(30))'
        )

    def test_create_index_with_using(self):
        m = MetaData()
        tbl = Table('testtbl', m, Column('data', String(255)))
        idx1 = Index('test_idx1', tbl.c.data, mysql_using='btree')
        idx2 = Index('test_idx2', tbl.c.data, mysql_using='hash')

        self.assert_compile(schema.CreateIndex(idx1),
            'CREATE INDEX test_idx1 ON testtbl (data) USING btree')
        self.assert_compile(schema.CreateIndex(idx2),
            'CREATE INDEX test_idx2 ON testtbl (data) USING hash')

    def test_create_pk_plain(self):
        m = MetaData()
        tbl = Table('testtbl', m, Column('data', String(255)),
            PrimaryKeyConstraint('data'))

        self.assert_compile(schema.CreateTable(tbl),
            "CREATE TABLE testtbl (data VARCHAR(255), PRIMARY KEY (data))")

    def test_create_pk_with_using(self):
        m = MetaData()
        tbl = Table('testtbl', m, Column('data', String(255)),
            PrimaryKeyConstraint('data', mysql_using='btree'))

        self.assert_compile(schema.CreateTable(tbl),
            "CREATE TABLE testtbl (data VARCHAR(255), "
            "PRIMARY KEY (data) USING btree)")

    def test_create_index_expr(self):
        m = MetaData()
        t1 = Table('foo', m,
                Column('x', Integer)
            )
        self.assert_compile(
            schema.CreateIndex(Index("bar", t1.c.x > 5)),
            "CREATE INDEX bar ON foo (x > 5)"
        )

    def test_deferrable_initially_kw_not_ignored(self):
        m = MetaData()
        t1 = Table('t1', m, Column('id', Integer, primary_key=True))
        t2 = Table('t2', m, Column('id', Integer,
                        ForeignKey('t1.id', deferrable=True, initially="XYZ"),
                            primary_key=True))

        self.assert_compile(
            schema.CreateTable(t2),
            "CREATE TABLE t2 (id INTEGER NOT NULL, "
            "PRIMARY KEY (id), FOREIGN KEY(id) REFERENCES t1 (id) DEFERRABLE INITIALLY XYZ)"
        )

    def test_match_kw_raises(self):
        m = MetaData()
        t1 = Table('t1', m, Column('id', Integer, primary_key=True))
        t2 = Table('t2', m, Column('id', Integer,
                        ForeignKey('t1.id', match="XYZ"),
                            primary_key=True))

        assert_raises_message(
            exc.CompileError,
            "MySQL ignores the 'MATCH' keyword while at the same time causes "
            "ON UPDATE/ON DELETE clauses to be ignored.",
            schema.CreateTable(t2).compile, dialect=mysql.dialect()
        )

    def test_for_update(self):
        table1 = table('mytable',
                    column('myid'), column('name'), column('description'))

        self.assert_compile(
            table1.select(table1.c.myid == 7).with_for_update(),
            "SELECT mytable.myid, mytable.name, mytable.description "
            "FROM mytable WHERE mytable.myid = %s FOR UPDATE")

        self.assert_compile(
            table1.select(table1.c.myid == 7).with_for_update(read=True),
            "SELECT mytable.myid, mytable.name, mytable.description "
            "FROM mytable WHERE mytable.myid = %s LOCK IN SHARE MODE")

class SQLTest(fixtures.TestBase, AssertsCompiledSQL):
    """Tests MySQL-dialect specific compilation."""

    __dialect__ = mysql.dialect()

    def test_precolumns(self):
        dialect = self.__dialect__

        def gen(distinct=None, prefixes=None):
            kw = {}
            if distinct is not None:
                kw['distinct'] = distinct
            if prefixes is not None:
                kw['prefixes'] = prefixes
            return str(select(['q'], **kw).compile(dialect=dialect))

        eq_(gen(None), 'SELECT q')
        eq_(gen(True), 'SELECT DISTINCT q')

        eq_(gen(prefixes=['ALL']), 'SELECT ALL q')
        eq_(gen(prefixes=['DISTINCTROW']),
                'SELECT DISTINCTROW q')

        # Interaction with MySQL prefix extensions
        eq_(
            gen(None, ['straight_join']),
            'SELECT straight_join q')
        eq_(
            gen(False, ['HIGH_PRIORITY', 'SQL_SMALL_RESULT', 'ALL']),
            'SELECT HIGH_PRIORITY SQL_SMALL_RESULT ALL q')
        eq_(
            gen(True, ['high_priority', sql.text('sql_cache')]),
            'SELECT high_priority sql_cache DISTINCT q')

    @testing.uses_deprecated
    def test_deprecated_distinct(self):
        dialect = self.__dialect__

        self.assert_compile(
            select(['q'], distinct='ALL'),
            'SELECT ALL q',
        )

        self.assert_compile(
            select(['q'], distinct='distinctROW'),
            'SELECT DISTINCTROW q',
        )

        self.assert_compile(
            select(['q'], distinct='ALL',
                    prefixes=['HIGH_PRIORITY', 'SQL_SMALL_RESULT']),
            'SELECT HIGH_PRIORITY SQL_SMALL_RESULT ALL q'
        )

    def test_backslash_escaping(self):
        self.assert_compile(
            sql.column('foo').like('bar', escape='\\'),
            "foo LIKE %s ESCAPE '\\\\'"
        )

        dialect = mysql.dialect()
        dialect._backslash_escapes=False
        self.assert_compile(
            sql.column('foo').like('bar', escape='\\'),
            "foo LIKE %s ESCAPE '\\'",
            dialect=dialect
        )

    def test_limit(self):
        t = sql.table('t', sql.column('col1'), sql.column('col2'))

        self.assert_compile(
            select([t]).limit(10).offset(20),
            "SELECT t.col1, t.col2 FROM t  LIMIT %s, %s",
            {'param_1':20, 'param_2':10}
            )
        self.assert_compile(
            select([t]).limit(10),
            "SELECT t.col1, t.col2 FROM t  LIMIT %s",
            {'param_1':10})

        self.assert_compile(
            select([t]).offset(10),
            "SELECT t.col1, t.col2 FROM t  LIMIT %s, 18446744073709551615",
            {'param_1':10}
            )

    def test_varchar_raise(self):
        for type_ in (
            String,
            VARCHAR,
            String(),
            VARCHAR(),
            NVARCHAR(),
            Unicode,
            Unicode(),
        ):
            type_ = sqltypes.to_instance(type_)
            assert_raises_message(
                exc.CompileError,
                "VARCHAR requires a length on dialect mysql",
                type_.compile,
                dialect=mysql.dialect()
            )

            t1 = Table('sometable', MetaData(),
                Column('somecolumn', type_)
            )
            assert_raises_message(
                exc.CompileError,
                r"\(in table 'sometable', column 'somecolumn'\)\: "
                r"(?:N)?VARCHAR requires a length on dialect mysql",
                schema.CreateTable(t1).compile,
                dialect=mysql.dialect()
            )

    def test_update_limit(self):
        t = sql.table('t', sql.column('col1'), sql.column('col2'))

        self.assert_compile(
            t.update(values={'col1':123}),
            "UPDATE t SET col1=%s"
            )
        self.assert_compile(
            t.update(values={'col1':123}, mysql_limit=5),
            "UPDATE t SET col1=%s LIMIT 5"
            )
        self.assert_compile(
            t.update(values={'col1':123}, mysql_limit=None),
            "UPDATE t SET col1=%s"
            )
        self.assert_compile(
            t.update(t.c.col2==456, values={'col1':123}, mysql_limit=1),
            "UPDATE t SET col1=%s WHERE t.col2 = %s LIMIT 1"
            )

    def test_utc_timestamp(self):
        self.assert_compile(func.utc_timestamp(), "UTC_TIMESTAMP")

    def test_sysdate(self):
        self.assert_compile(func.sysdate(), "SYSDATE()")

    def test_cast(self):
        t = sql.table('t', sql.column('col'))
        m = mysql

        specs = [
            (Integer, "CAST(t.col AS SIGNED INTEGER)"),
            (INT, "CAST(t.col AS SIGNED INTEGER)"),
            (m.MSInteger, "CAST(t.col AS SIGNED INTEGER)"),
            (m.MSInteger(unsigned=True), "CAST(t.col AS UNSIGNED INTEGER)"),
            (SmallInteger, "CAST(t.col AS SIGNED INTEGER)"),
            (m.MSSmallInteger, "CAST(t.col AS SIGNED INTEGER)"),
            (m.MSTinyInteger, "CAST(t.col AS SIGNED INTEGER)"),
            # 'SIGNED INTEGER' is a bigint, so this is ok.
            (m.MSBigInteger, "CAST(t.col AS SIGNED INTEGER)"),
            (m.MSBigInteger(unsigned=False), "CAST(t.col AS SIGNED INTEGER)"),
            (m.MSBigInteger(unsigned=True),
                            "CAST(t.col AS UNSIGNED INTEGER)"),
            (m.MSBit, "t.col"),

            # this is kind of sucky.  thank you default arguments!
            (NUMERIC, "CAST(t.col AS DECIMAL)"),
            (DECIMAL, "CAST(t.col AS DECIMAL)"),
            (Numeric, "CAST(t.col AS DECIMAL)"),
            (m.MSNumeric, "CAST(t.col AS DECIMAL)"),
            (m.MSDecimal, "CAST(t.col AS DECIMAL)"),

            (FLOAT, "t.col"),
            (Float, "t.col"),
            (m.MSFloat, "t.col"),
            (m.MSDouble, "t.col"),
            (m.MSReal, "t.col"),

            (TIMESTAMP, "CAST(t.col AS DATETIME)"),
            (DATETIME, "CAST(t.col AS DATETIME)"),
            (DATE, "CAST(t.col AS DATE)"),
            (TIME, "CAST(t.col AS TIME)"),
            (DateTime, "CAST(t.col AS DATETIME)"),
            (Date, "CAST(t.col AS DATE)"),
            (Time, "CAST(t.col AS TIME)"),
            (DateTime, "CAST(t.col AS DATETIME)"),
            (Date, "CAST(t.col AS DATE)"),
            (m.MSTime, "CAST(t.col AS TIME)"),
            (m.MSTimeStamp, "CAST(t.col AS DATETIME)"),
            (m.MSYear, "t.col"),
            (m.MSYear(2), "t.col"),
            (Interval, "t.col"),

            (String, "CAST(t.col AS CHAR)"),
            (Unicode, "CAST(t.col AS CHAR)"),
            (UnicodeText, "CAST(t.col AS CHAR)"),
            (VARCHAR, "CAST(t.col AS CHAR)"),
            (NCHAR, "CAST(t.col AS CHAR)"),
            (CHAR, "CAST(t.col AS CHAR)"),
            (m.CHAR(charset='utf8'), "CAST(t.col AS CHAR CHARACTER SET utf8)"),
            (CLOB, "CAST(t.col AS CHAR)"),
            (TEXT, "CAST(t.col AS CHAR)"),
            (m.TEXT(charset='utf8'), "CAST(t.col AS CHAR CHARACTER SET utf8)"),
            (String(32), "CAST(t.col AS CHAR(32))"),
            (Unicode(32), "CAST(t.col AS CHAR(32))"),
            (CHAR(32), "CAST(t.col AS CHAR(32))"),
            (m.MSString, "CAST(t.col AS CHAR)"),
            (m.MSText, "CAST(t.col AS CHAR)"),
            (m.MSTinyText, "CAST(t.col AS CHAR)"),
            (m.MSMediumText, "CAST(t.col AS CHAR)"),
            (m.MSLongText, "CAST(t.col AS CHAR)"),
            (m.MSNChar, "CAST(t.col AS CHAR)"),
            (m.MSNVarChar, "CAST(t.col AS CHAR)"),

            (LargeBinary, "CAST(t.col AS BINARY)"),
            (BLOB, "CAST(t.col AS BINARY)"),
            (m.MSBlob, "CAST(t.col AS BINARY)"),
            (m.MSBlob(32), "CAST(t.col AS BINARY)"),
            (m.MSTinyBlob, "CAST(t.col AS BINARY)"),
            (m.MSMediumBlob, "CAST(t.col AS BINARY)"),
            (m.MSLongBlob, "CAST(t.col AS BINARY)"),
            (m.MSBinary, "CAST(t.col AS BINARY)"),
            (m.MSBinary(32), "CAST(t.col AS BINARY)"),
            (m.MSVarBinary, "CAST(t.col AS BINARY)"),
            (m.MSVarBinary(32), "CAST(t.col AS BINARY)"),

            # maybe this could be changed to something more DWIM, needs
            # testing
            (Boolean, "t.col"),
            (BOOLEAN, "t.col"),

            (m.MSEnum, "t.col"),
            (m.MSEnum("1", "2"), "t.col"),
            (m.MSSet, "t.col"),
            (m.MSSet("1", "2"), "t.col"),
            ]

        for type_, expected in specs:
            self.assert_compile(cast(t.c.col, type_), expected)

    def test_no_cast_pre_4(self):
        self.assert_compile(
                    cast(Column('foo', Integer), String),
                    "CAST(foo AS CHAR)",
            )
        dialect = mysql.dialect()
        dialect.server_version_info = (3, 2, 3)
        self.assert_compile(
                    cast(Column('foo', Integer), String),
                    "foo",
                    dialect=dialect
            )

    def test_cast_grouped_expression_non_castable(self):
        self.assert_compile(
            cast(sql.column('x') + sql.column('y'), Float),
            "(x + y)"
        )

    def test_cast_grouped_expression_pre_4(self):
        dialect = mysql.dialect()
        dialect.server_version_info = (3, 2, 3)
        self.assert_compile(
            cast(sql.column('x') + sql.column('y'), Integer),
            "(x + y)",
            dialect=dialect
        )

    def test_extract(self):
        t = sql.table('t', sql.column('col1'))

        for field in 'year', 'month', 'day':
            self.assert_compile(
                select([extract(field, t.c.col1)]),
                "SELECT EXTRACT(%s FROM t.col1) AS anon_1 FROM t" % field)

        # millsecondS to millisecond
        self.assert_compile(
            select([extract('milliseconds', t.c.col1)]),
            "SELECT EXTRACT(millisecond FROM t.col1) AS anon_1 FROM t")

    def test_too_long_index(self):
        exp = 'ix_zyrenian_zyme_zyzzogeton_zyzzogeton_zyrenian_zyme_zyz_5cd2'
        tname = 'zyrenian_zyme_zyzzogeton_zyzzogeton'
        cname = 'zyrenian_zyme_zyzzogeton_zo'

        t1 = Table(tname, MetaData(),
                    Column(cname, Integer, index=True),
                )
        ix1 = list(t1.indexes)[0]

        self.assert_compile(
            schema.CreateIndex(ix1),
            "CREATE INDEX %s "
            "ON %s (%s)" % (exp, tname, cname)
        )

    def test_innodb_autoincrement(self):
        t1 = Table('sometable', MetaData(), Column('assigned_id',
                   Integer(), primary_key=True, autoincrement=False),
                   Column('id', Integer(), primary_key=True,
                   autoincrement=True), mysql_engine='InnoDB')
        self.assert_compile(schema.CreateTable(t1),
                            'CREATE TABLE sometable (assigned_id '
                            'INTEGER NOT NULL, id INTEGER NOT NULL '
                            'AUTO_INCREMENT, PRIMARY KEY (assigned_id, '
                            'id), KEY idx_autoinc_id (id))ENGINE=Inn'
                            'oDB')

        t1 = Table('sometable', MetaData(), Column('assigned_id',
                   Integer(), primary_key=True, autoincrement=True),
                   Column('id', Integer(), primary_key=True,
                   autoincrement=False), mysql_engine='InnoDB')
        self.assert_compile(schema.CreateTable(t1),
                            'CREATE TABLE sometable (assigned_id '
                            'INTEGER NOT NULL AUTO_INCREMENT, id '
                            'INTEGER NOT NULL, PRIMARY KEY '
                            '(assigned_id, id))ENGINE=InnoDB')

    def test_innodb_autoincrement_reserved_word_column_name(self):
        t1 = Table(
            'sometable', MetaData(),
            Column('id', Integer(), primary_key=True, autoincrement=False),
            Column('order', Integer(), primary_key=True, autoincrement=True),
            mysql_engine='InnoDB')
        self.assert_compile(
            schema.CreateTable(t1),
            'CREATE TABLE sometable ('
            'id INTEGER NOT NULL, '
            '`order` INTEGER NOT NULL AUTO_INCREMENT, '
            'PRIMARY KEY (id, `order`), '
            'KEY idx_autoinc_order (`order`)'
            ')ENGINE=InnoDB')

