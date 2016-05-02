"""Test the TextClause and related constructs."""

from sqlalchemy.testing import fixtures, AssertsCompiledSQL, eq_, \
    assert_raises_message, expect_warnings, assert_warnings
from sqlalchemy import text, select, Integer, String, Float, \
    bindparam, and_, func, literal_column, exc, MetaData, Table, Column,\
    asc, func, desc, union
from sqlalchemy.types import NullType
from sqlalchemy.sql import table, column, util as sql_util
from sqlalchemy import util

table1 = table('mytable',
               column('myid', Integer),
               column('name', String),
               column('description', String),
               )

table2 = table(
    'myothertable',
    column('otherid', Integer),
    column('othername', String),
)


class CompileTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = 'default'

    def test_basic(self):
        self.assert_compile(
            text("select * from foo where lala = bar"),
            "select * from foo where lala = bar"
        )


class SelectCompositionTest(fixtures.TestBase, AssertsCompiledSQL):

    """test the usage of text() implicit within the select() construct
    when strings are passed."""

    __dialect__ = 'default'

    def test_select_composition_one(self):
        self.assert_compile(select(
            [
                literal_column("foobar(a)"),
                literal_column("pk_foo_bar(syslaal)")
            ],
            text("a = 12"),
            from_obj=[
                text("foobar left outer join lala on foobar.foo = lala.foo")
            ]
        ),
            "SELECT foobar(a), pk_foo_bar(syslaal) FROM foobar "
            "left outer join lala on foobar.foo = lala.foo WHERE a = 12"
        )

    def test_select_composition_two(self):
        s = select()
        s.append_column(column("column1"))
        s.append_column(column("column2"))
        s.append_whereclause(text("column1=12"))
        s.append_whereclause(text("column2=19"))
        s = s.order_by("column1")
        s.append_from(text("table1"))
        self.assert_compile(s, "SELECT column1, column2 FROM table1 WHERE "
                            "column1=12 AND column2=19 ORDER BY column1")

    def test_select_composition_three(self):
        self.assert_compile(
            select([column("column1"), column("column2")],
                   from_obj=table1).alias('somealias').select(),
            "SELECT somealias.column1, somealias.column2 FROM "
            "(SELECT column1, column2 FROM mytable) AS somealias"
        )

    def test_select_composition_four(self):
        # test that use_labels doesn't interfere with literal columns
        self.assert_compile(
            select([
                text("column1"), column("column2"),
                column("column3").label("bar"), table1.c.myid],
                from_obj=table1,
                use_labels=True),
            "SELECT column1, column2, column3 AS bar, "
            "mytable.myid AS mytable_myid "
            "FROM mytable"
        )

    def test_select_composition_five(self):
        # test that use_labels doesn't interfere
        # with literal columns that have textual labels
        self.assert_compile(
            select([
                text("column1 AS foobar"), text("column2 AS hoho"),
                table1.c.myid],
                from_obj=table1, use_labels=True),
            "SELECT column1 AS foobar, column2 AS hoho, "
            "mytable.myid AS mytable_myid FROM mytable"
        )

    def test_select_composition_six(self):
        # test that "auto-labeling of subquery columns"
        # doesn't interfere with literal columns,
        # exported columns don't get quoted
        self.assert_compile(
            select([
                literal_column("column1 AS foobar"),
                literal_column("column2 AS hoho"), table1.c.myid],
                from_obj=[table1]).select(),
            "SELECT column1 AS foobar, column2 AS hoho, myid FROM "
            "(SELECT column1 AS foobar, column2 AS hoho, "
            "mytable.myid AS myid FROM mytable)"
        )

    def test_select_composition_seven(self):
        self.assert_compile(
            select([
                literal_column('col1'),
                literal_column('col2')
            ], from_obj=table('tablename')).alias('myalias'),
            "SELECT col1, col2 FROM tablename"
        )

    def test_select_composition_eight(self):
        self.assert_compile(select(
            [table1.alias('t'), text("foo.f")],
            text("foo.f = t.id"),
            from_obj=[text("(select f from bar where lala=heyhey) foo")]
        ),
            "SELECT t.myid, t.name, t.description, foo.f FROM mytable AS t, "
            "(select f from bar where lala=heyhey) foo WHERE foo.f = t.id")

    def test_select_bundle_columns(self):
        self.assert_compile(select(
            [table1, table2.c.otherid,
                text("sysdate()"), text("foo, bar, lala")],
            and_(
                text("foo.id = foofoo(lala)"),
                text("datetime(foo) = Today"),
                table1.c.myid == table2.c.otherid,
            )
        ),
            "SELECT mytable.myid, mytable.name, mytable.description, "
            "myothertable.otherid, sysdate(), foo, bar, lala "
            "FROM mytable, myothertable WHERE foo.id = foofoo(lala) AND "
            "datetime(foo) = Today AND mytable.myid = myothertable.otherid")


class BindParamTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = 'default'

    def test_legacy(self):
        t = text("select * from foo where lala=:bar and hoho=:whee",
                 bindparams=[bindparam('bar', 4), bindparam('whee', 7)])

        self.assert_compile(
            t,
            "select * from foo where lala=:bar and hoho=:whee",
            checkparams={'bar': 4, 'whee': 7},
        )

    def test_positional(self):
        t = text("select * from foo where lala=:bar and hoho=:whee")
        t = t.bindparams(bindparam('bar', 4), bindparam('whee', 7))

        self.assert_compile(
            t,
            "select * from foo where lala=:bar and hoho=:whee",
            checkparams={'bar': 4, 'whee': 7},
        )

    def test_kw(self):
        t = text("select * from foo where lala=:bar and hoho=:whee")
        t = t.bindparams(bar=4, whee=7)

        self.assert_compile(
            t,
            "select * from foo where lala=:bar and hoho=:whee",
            checkparams={'bar': 4, 'whee': 7},
        )

    def test_positional_plus_kw(self):
        t = text("select * from foo where lala=:bar and hoho=:whee")
        t = t.bindparams(bindparam('bar', 4), whee=7)

        self.assert_compile(
            t,
            "select * from foo where lala=:bar and hoho=:whee",
            checkparams={'bar': 4, 'whee': 7},
        )

    def test_literal_binds(self):
        t = text("select * from foo where lala=:bar and hoho=:whee")
        t = t.bindparams(bindparam('bar', 4), whee='whee')

        self.assert_compile(
            t,
            "select * from foo where lala=4 and hoho='whee'",
            checkparams={},
            literal_binds=True
        )

    def _assert_type_map(self, t, compare):
        map_ = dict(
            (b.key, b.type) for b in t._bindparams.values()
        )
        for k in compare:
            assert compare[k]._type_affinity is map_[k]._type_affinity

    def test_typing_construction(self):
        t = text("select * from table :foo :bar :bat")

        self._assert_type_map(t, {"foo": NullType(),
                                  "bar": NullType(),
                                  "bat": NullType()})

        t = t.bindparams(bindparam('foo', type_=String))

        self._assert_type_map(t, {"foo": String(),
                                  "bar": NullType(),
                                  "bat": NullType()})

        t = t.bindparams(bindparam('bar', type_=Integer))

        self._assert_type_map(t, {"foo": String(),
                                  "bar": Integer(),
                                  "bat": NullType()})

        t = t.bindparams(bat=45.564)

        self._assert_type_map(t, {"foo": String(),
                                  "bar": Integer(),
                                  "bat": Float()})

    def test_binds_compiled_named(self):
        self.assert_compile(
            text("select * from foo where lala=:bar and hoho=:whee").
            bindparams(bar=4, whee=7),
            "select * from foo where lala=%(bar)s and hoho=%(whee)s",
            checkparams={'bar': 4, 'whee': 7},
            dialect="postgresql"
        )

    def test_binds_compiled_positional(self):
        self.assert_compile(
            text("select * from foo where lala=:bar and hoho=:whee").
            bindparams(bar=4, whee=7),
            "select * from foo where lala=? and hoho=?",
            checkparams={'bar': 4, 'whee': 7},
            dialect="sqlite"
        )

    def test_missing_bind_kw(self):
        assert_raises_message(
            exc.ArgumentError,
            "This text\(\) construct doesn't define a bound parameter named 'bar'",
            text(":foo").bindparams,
            foo=5,
            bar=7)

    def test_missing_bind_posn(self):
        assert_raises_message(
            exc.ArgumentError,
            "This text\(\) construct doesn't define a bound parameter named 'bar'",
            text(":foo").bindparams,
            bindparam(
                'foo',
                value=5),
            bindparam(
                'bar',
                value=7))

    def test_escaping_colons(self):
        # test escaping out text() params with a backslash
        self.assert_compile(
            text("select * from foo where clock='05:06:07' "
                 "and mork='\:mindy'"),
            "select * from foo where clock='05:06:07' and mork=':mindy'",
            checkparams={},
            params={},
            dialect="postgresql"
        )

    def test_escaping_double_colons(self):
        self.assert_compile(
            text(
                "SELECT * FROM pg_attribute WHERE "
                "attrelid = :tab\:\:regclass"),
            "SELECT * FROM pg_attribute WHERE "
            "attrelid = %(tab)s::regclass",
            params={'tab': None},
            dialect="postgresql"
        )

    def test_text_in_select_nonfrom(self):

        generate_series = text("generate_series(:x, :y, :z) as s(a)").\
            bindparams(x=None, y=None, z=None)

        s = select([
            (func.current_date() + literal_column("s.a")).label("dates")
        ]).select_from(generate_series)

        self.assert_compile(
            s,
            "SELECT CURRENT_DATE + s.a AS dates FROM "
            "generate_series(:x, :y, :z) as s(a)",
            checkparams={'y': None, 'x': None, 'z': None}
        )

        self.assert_compile(
            s.params(x=5, y=6, z=7),
            "SELECT CURRENT_DATE + s.a AS dates FROM "
            "generate_series(:x, :y, :z) as s(a)",
            checkparams={'y': 6, 'x': 5, 'z': 7}
        )


class AsFromTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = 'default'

    def test_basic_toplevel_resultmap_positional(self):
        t = text("select id, name from user").columns(
            column('id', Integer),
            column('name')
        )

        compiled = t.compile()
        eq_(compiled._create_result_map(),
            {'id': ('id',
                    (t.c.id._proxies[0],
                     'id',
                     'id'),
                    t.c.id.type),
                'name': ('name',
                         (t.c.name._proxies[0],
                          'name',
                          'name'),
                         t.c.name.type)})

    def test_basic_toplevel_resultmap(self):
        t = text("select id, name from user").columns(id=Integer, name=String)

        compiled = t.compile()
        eq_(compiled._create_result_map(),
            {'id': ('id',
                    (t.c.id._proxies[0],
                     'id',
                     'id'),
                    t.c.id.type),
                'name': ('name',
                         (t.c.name._proxies[0],
                          'name',
                          'name'),
                         t.c.name.type)})

    def test_basic_subquery_resultmap(self):
        t = text("select id, name from user").columns(id=Integer, name=String)

        stmt = select([table1.c.myid]).select_from(
            table1.join(t, table1.c.myid == t.c.id))
        compiled = stmt.compile()
        eq_(
            compiled._create_result_map(),
            {
                "myid": ("myid",
                         (table1.c.myid, "myid", "myid"), table1.c.myid.type),
            }
        )

    def test_column_collection_ordered(self):
        t = text("select a, b, c from foo").columns(column('a'),
                                                    column('b'), column('c'))
        eq_(t.c.keys(), ['a', 'b', 'c'])

    def test_column_collection_pos_plus_bykey(self):
        # overlapping positional names + type names
        t = text("select a, b, c from foo").columns(
            column('a'),
            column('b'),
            b=Integer,
            c=String)
        eq_(t.c.keys(), ['a', 'b', 'c'])
        eq_(t.c.b.type._type_affinity, Integer)
        eq_(t.c.c.type._type_affinity, String)

    def _xy_table_fixture(self):
        m = MetaData()
        t = Table('t', m, Column('x', Integer), Column('y', Integer))
        return t

    def _mapping(self, stmt):
        compiled = stmt.compile()
        return dict(
            (elem, key)
            for key, elements in compiled._create_result_map().items()
            for elem in elements[1]
        )

    def test_select_label_alt_name(self):
        t = self._xy_table_fixture()
        l1, l2 = t.c.x.label('a'), t.c.y.label('b')
        s = text("select x AS a, y AS b FROM t").columns(l1, l2)
        mapping = self._mapping(s)
        assert l1 in mapping

        assert t.c.x not in mapping

    def test_select_alias_label_alt_name(self):
        t = self._xy_table_fixture()
        l1, l2 = t.c.x.label('a'), t.c.y.label('b')
        s = text("select x AS a, y AS b FROM t").columns(l1, l2).alias()
        mapping = self._mapping(s)
        assert l1 in mapping

        assert t.c.x not in mapping

    def test_select_column(self):
        t = self._xy_table_fixture()
        x, y = t.c.x, t.c.y
        s = text("select x, y FROM t").columns(x, y)
        mapping = self._mapping(s)
        assert t.c.x in mapping

    def test_select_alias_column(self):
        t = self._xy_table_fixture()
        x, y = t.c.x, t.c.y
        s = text("select x, y FROM t").columns(x, y).alias()
        mapping = self._mapping(s)
        assert t.c.x in mapping

    def test_select_table_alias_column(self):
        t = self._xy_table_fixture()
        x, y = t.c.x, t.c.y

        ta = t.alias()
        s = text("select ta.x, ta.y FROM t AS ta").columns(ta.c.x, ta.c.y)
        mapping = self._mapping(s)
        assert x not in mapping

    def test_select_label_alt_name_table_alias_column(self):
        t = self._xy_table_fixture()
        x, y = t.c.x, t.c.y

        ta = t.alias()
        l1, l2 = ta.c.x.label('a'), ta.c.y.label('b')

        s = text("SELECT ta.x AS a, ta.y AS b FROM t AS ta").columns(l1, l2)
        mapping = self._mapping(s)
        assert x not in mapping
        assert l1 in mapping
        assert ta.c.x not in mapping

    def test_cte(self):
        t = text("select id, name from user").columns(
            id=Integer,
            name=String).cte('t')

        s = select([table1]).where(table1.c.myid == t.c.id)
        self.assert_compile(
            s,
            "WITH t AS (select id, name from user) "
            "SELECT mytable.myid, mytable.name, mytable.description "
            "FROM mytable, t WHERE mytable.myid = t.id"
        )

    def test_alias(self):
        t = text("select id, name from user").columns(
            id=Integer,
            name=String).alias('t')

        s = select([table1]).where(table1.c.myid == t.c.id)
        self.assert_compile(
            s,
            "SELECT mytable.myid, mytable.name, mytable.description "
            "FROM mytable, (select id, name from user) AS t "
            "WHERE mytable.myid = t.id"
        )

    def test_scalar_subquery(self):
        t = text("select id from user").columns(id=Integer)
        subq = t.as_scalar()

        assert subq.type._type_affinity is Integer()._type_affinity

        s = select([table1.c.myid, subq]).where(table1.c.myid == subq)
        self.assert_compile(
            s,
            "SELECT mytable.myid, (select id from user) AS anon_1 "
            "FROM mytable WHERE mytable.myid = (select id from user)"
        )

    def test_build_bindparams(self):
        t = text("select id from user :foo :bar :bat")
        t = t.bindparams(bindparam("foo", type_=Integer))
        t = t.columns(id=Integer)
        t = t.bindparams(bar=String)
        t = t.bindparams(bindparam('bat', value='bat'))

        eq_(
            set(t.element._bindparams),
            set(["bat", "foo", "bar"])
        )


class TextWarningsTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = 'default'

    def _test(self, fn, arg, offending_clause, expected):
        with expect_warnings("Textual "):
            stmt = fn(arg)
            self.assert_compile(stmt, expected)

        assert_raises_message(
            exc.SAWarning,
            r"Textual (?:SQL|column|SQL FROM) expression %(stmt)r should be "
            r"explicitly declared (?:with|as) text\(%(stmt)r\)" % {
                "stmt": util.ellipses_string(offending_clause),
            },
            fn, arg
        )

    def test_where(self):
        self._test(
            select([table1.c.myid]).where, "myid == 5", "myid == 5",
            "SELECT mytable.myid FROM mytable WHERE myid == 5"
        )

    def test_column(self):
        self._test(
            select, ["myid"], "myid",
            "SELECT myid"
        )

    def test_having(self):
        self._test(
            select([table1.c.myid]).having, "myid == 5", "myid == 5",
            "SELECT mytable.myid FROM mytable HAVING myid == 5"
        )

    def test_from(self):
        self._test(
            select([table1.c.myid]).select_from, "mytable", "mytable",
            "SELECT mytable.myid FROM mytable, mytable"   # two FROMs
        )


class OrderByLabelResolutionTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = 'default'

    def _test_warning(self, stmt, offending_clause, expected):
        with expect_warnings(
                "Can't resolve label reference %r;" % offending_clause):
            self.assert_compile(
                stmt,
                expected
            )
        assert_raises_message(
            exc.SAWarning,
            "Can't resolve label reference %r; converting to text" %
            offending_clause,
            stmt.compile
        )

    def test_order_by_label(self):
        stmt = select([table1.c.myid.label('foo')]).order_by('foo')
        self.assert_compile(
            stmt,
            "SELECT mytable.myid AS foo FROM mytable ORDER BY foo"
        )

    def test_order_by_colname(self):
        stmt = select([table1.c.myid]).order_by('name')
        self.assert_compile(
            stmt,
            "SELECT mytable.myid FROM mytable ORDER BY mytable.name"
        )

    def test_order_by_alias_colname(self):
        t1 = table1.alias()
        stmt = select([t1.c.myid]).apply_labels().order_by('name')
        self.assert_compile(
            stmt,
            "SELECT mytable_1.myid AS mytable_1_myid "
            "FROM mytable AS mytable_1 ORDER BY mytable_1.name"
        )

    def test_order_by_named_label_from_anon_label(self):
        s1 = select([table1.c.myid.label(None).label("foo"), table1.c.name])
        stmt = s1.order_by("foo")
        self.assert_compile(
            stmt,
            "SELECT mytable.myid AS foo, mytable.name "
            "FROM mytable ORDER BY foo"
        )

    def test_order_by_outermost_label(self):
        # test [ticket:3335], assure that order_by("foo")
        # catches the label named "foo" in the columns clause only,
        # and not the label named "foo" in the FROM clause
        s1 = select([table1.c.myid.label("foo"), table1.c.name]).alias()
        stmt = select([s1.c.name, func.bar().label("foo")]).order_by("foo")

        self.assert_compile(
            stmt,
            "SELECT anon_1.name, bar() AS foo FROM "
            "(SELECT mytable.myid AS foo, mytable.name AS name "
            "FROM mytable) AS anon_1 ORDER BY foo"
        )

    def test_unresolvable_warning_order_by(self):
        stmt = select([table1.c.myid]).order_by('foobar')
        self._test_warning(
            stmt, "foobar",
            "SELECT mytable.myid FROM mytable ORDER BY foobar"
        )

    def test_group_by_label(self):
        stmt = select([table1.c.myid.label('foo')]).group_by('foo')
        self.assert_compile(
            stmt,
            "SELECT mytable.myid AS foo FROM mytable GROUP BY foo"
        )

    def test_group_by_colname(self):
        stmt = select([table1.c.myid]).group_by('name')
        self.assert_compile(
            stmt,
            "SELECT mytable.myid FROM mytable GROUP BY mytable.name"
        )

    def test_unresolvable_warning_group_by(self):
        stmt = select([table1.c.myid]).group_by('foobar')
        self._test_warning(
            stmt, "foobar",
            "SELECT mytable.myid FROM mytable GROUP BY foobar"
        )

    def test_asc(self):
        stmt = select([table1.c.myid]).order_by(asc('name'), 'description')
        self.assert_compile(
            stmt,
            "SELECT mytable.myid FROM mytable "
            "ORDER BY mytable.name ASC, mytable.description"
        )

    def test_group_by_subquery(self):
        stmt = select([table1]).alias()
        stmt = select([stmt]).apply_labels().group_by("myid")
        self.assert_compile(
            stmt,
            "SELECT anon_1.myid AS anon_1_myid, anon_1.name AS anon_1_name, "
            "anon_1.description AS anon_1_description FROM "
            "(SELECT mytable.myid AS myid, mytable.name AS name, "
            "mytable.description AS description FROM mytable) AS anon_1 "
            "GROUP BY anon_1.myid"
        )

    def test_order_by_func_label_desc(self):
        stmt = select([func.foo('bar').label('fb'), table1]).\
            order_by(desc('fb'))

        self.assert_compile(
            stmt,
            "SELECT foo(:foo_1) AS fb, mytable.myid, mytable.name, "
            "mytable.description FROM mytable ORDER BY fb DESC"
        )

    def test_pg_distinct(self):
        stmt = select([table1]).distinct('name')
        self.assert_compile(
            stmt,
            "SELECT DISTINCT ON (mytable.name) mytable.myid, "
            "mytable.name, mytable.description FROM mytable",
            dialect="postgresql"
        )

    def test_over(self):
        stmt = select([column("foo"), column("bar")])
        stmt = select(
            [func.row_number().
             over(order_by='foo', partition_by='bar')]
        ).select_from(stmt)

        self.assert_compile(
            stmt,
            "SELECT row_number() OVER (PARTITION BY bar ORDER BY foo "
            "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) "
            "AS anon_1 FROM (SELECT foo, bar)"
        )

    def test_union_column(self):
        s1 = select([table1])
        s2 = select([table1])
        stmt = union(s1, s2).order_by("name")
        self.assert_compile(
            stmt,
            "SELECT mytable.myid, mytable.name, mytable.description FROM "
            "mytable UNION SELECT mytable.myid, mytable.name, "
            "mytable.description FROM mytable ORDER BY name"
        )

    def test_union_label(self):
        s1 = select([func.foo("hoho").label('x')])
        s2 = select([func.foo("Bar").label('y')])
        stmt = union(s1, s2).order_by("x")
        self.assert_compile(
            stmt,
            "SELECT foo(:foo_1) AS x UNION SELECT foo(:foo_2) AS y ORDER BY x"
        )

    def test_standalone_units_stringable(self):
        self.assert_compile(
            desc("somelabel"),
            "somelabel DESC"
        )

    def test_columnadapter_anonymized(self):
        """test issue #3148

        Testing the anonymization applied from the ColumnAdapter.columns
        collection, typically as used in eager loading.

        """
        exprs = [
            table1.c.myid,
            table1.c.name.label('t1name'),
            func.foo("hoho").label('x')]

        ta = table1.alias()
        adapter = sql_util.ColumnAdapter(ta, anonymize_labels=True)

        s1 = select([adapter.columns[expr] for expr in exprs]).\
            apply_labels().order_by("myid", "t1name", "x")

        def go():
            # the labels here are anonymized, so label naming
            # can't catch these.
            self.assert_compile(
                s1,
                "SELECT mytable_1.myid AS mytable_1_myid, "
                "mytable_1.name AS name_1, foo(:foo_2) AS foo_1 "
                "FROM mytable AS mytable_1 ORDER BY mytable_1.myid, t1name, x"
            )

        assert_warnings(
            go,
            ["Can't resolve label reference 't1name'",
             "Can't resolve label reference 'x'"], regex=True)

    def test_columnadapter_non_anonymized(self):
        """test issue #3148

        Testing the anonymization applied from the ColumnAdapter.columns
        collection, typically as used in eager loading.

        """
        exprs = [
            table1.c.myid,
            table1.c.name.label('t1name'),
            func.foo("hoho").label('x')]

        ta = table1.alias()
        adapter = sql_util.ColumnAdapter(ta)

        s1 = select([adapter.columns[expr] for expr in exprs]).\
            apply_labels().order_by("myid", "t1name", "x")

        # labels are maintained
        self.assert_compile(
            s1,
            "SELECT mytable_1.myid AS mytable_1_myid, "
            "mytable_1.name AS t1name, foo(:foo_1) AS x "
            "FROM mytable AS mytable_1 ORDER BY mytable_1.myid, t1name, x"
        )
