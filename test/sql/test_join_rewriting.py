from sqlalchemy import Table, Column, Integer, MetaData, ForeignKey, select
from sqlalchemy.testing import fixtures, AssertsCompiledSQL, eq_
from sqlalchemy import util
from sqlalchemy.engine import default
from sqlalchemy import testing



m = MetaData()

a = Table('a', m,
        Column('id', Integer, primary_key=True)
    )

b = Table('b', m,
        Column('id', Integer, primary_key=True),
        Column('a_id', Integer, ForeignKey('a.id'))
    )

c = Table('c', m,
        Column('id', Integer, primary_key=True),
        Column('b_id', Integer, ForeignKey('b.id'))
    )

d = Table('d', m,
        Column('id', Integer, primary_key=True),
        Column('c_id', Integer, ForeignKey('c.id'))
    )

e = Table('e', m,
        Column('id', Integer, primary_key=True)
    )

b_key = Table('b_key', m,
        Column('id', Integer, primary_key=True, key='bid'),
    )

a_to_b_key = Table('a_to_b_key', m,
        Column('aid', Integer, ForeignKey('a.id')),
        Column('bid', Integer, ForeignKey('b_key.bid')),
    )

class _JoinRewriteTestBase(AssertsCompiledSQL):
    def _test(self, s, assert_):
        self.assert_compile(
            s,
            assert_
        )

        compiled = s.compile(dialect=self.__dialect__)

        # column name should be in result map, as we never render
        # .key in SQL
        for key, col in zip([c.name for c in s.c], s.inner_columns):
            key = key % compiled.anon_map
            assert col in compiled.result_map[key][1]

    _a_bkeyselect_bkey = ""

    def test_a_bkeyselect_bkey(self):
        assoc = a_to_b_key.select().alias()
        j1 = assoc.join(b_key)
        j2 = a.join(j1)

        s = select([a, b_key], use_labels=True).select_from(j2)
        self._test(s, self._a_bkeyselect_bkey)

    def test_a_bc(self):
        j1 = b.join(c)
        j2 = a.join(j1)

        # TODO: if we remove 'b' or 'c', shouldn't we get just
        # the subset of cols from anon_1 ?

        # TODO: do this test also with individual cols, things change
        # lots based on how you go with this

        s = select([a, b, c], use_labels=True).\
            select_from(j2).\
            where(b.c.id == 2).\
            where(c.c.id == 3).order_by(a.c.id, b.c.id, c.c.id)

        self._test(s, self._a_bc)

    def test_a_bkeyassoc(self):
        j1 = b_key.join(a_to_b_key)
        j2 = a.join(j1)

        s = select([a, b_key.c.bid], use_labels=True).\
                select_from(j2)

        self._test(s, self._a_bkeyassoc)

    def test_a_bkeyassoc_aliased(self):
        bkey_alias = b_key.alias()
        a_to_b_key_alias = a_to_b_key.alias()

        j1 = bkey_alias.join(a_to_b_key_alias)
        j2 = a.join(j1)

        s = select([a, bkey_alias.c.bid], use_labels=True).\
                select_from(j2)

        self._test(s, self._a_bkeyassoc_aliased)

    def test_a__b_dc(self):
        j1 = c.join(d)
        j2 = b.join(j1)
        j3 = a.join(j2)

        s = select([a, b, c, d], use_labels=True).\
            select_from(j3).\
            where(b.c.id == 2).\
            where(c.c.id == 3).\
            where(d.c.id == 4).\
                order_by(a.c.id, b.c.id, c.c.id, d.c.id)

        self._test(
            s,
            self._a__b_dc
        )

    def test_a_bc_comma_a1_selbc(self):
        # test here we're emulating is
        # test.orm.inheritance.test_polymorphic_rel:PolymorphicJoinsTest.test_multi_join
        j1 = b.join(c)
        j2 = b.join(c).select(use_labels=True).alias()
        j3 = a.join(j1)
        a_a = a.alias()
        j4 = a_a.join(j2)

        s = select([a, a_a, b, c, j2], use_labels=True).\
                select_from(j3).select_from(j4).order_by(j2.c.b_id)

        self._test(
            s,
            self._a_bc_comma_a1_selbc
        )


class JoinRewriteTest(_JoinRewriteTestBase, fixtures.TestBase):
    """test rendering of each join with right-nested rewritten as
    aliased SELECT statements.."""

    @util.classproperty
    def __dialect__(cls):
        dialect = default.DefaultDialect()
        dialect.supports_right_nested_joins = False
        return dialect

    _a__b_dc = (
            "SELECT a.id AS a_id, anon_1.b_id AS b_id, "
            "anon_1.b_a_id AS b_a_id, anon_1.c_id AS c_id, "
            "anon_1.c_b_id AS c_b_id, anon_1.d_id AS d_id, "
            "anon_1.d_c_id AS d_c_id "
            "FROM a JOIN (SELECT b.id AS b_id, b.a_id AS b_a_id, "
            "anon_2.c_id AS c_id, anon_2.c_b_id AS c_b_id, "
            "anon_2.d_id AS d_id, anon_2.d_c_id AS d_c_id "
            "FROM b JOIN (SELECT c.id AS c_id, c.b_id AS c_b_id, "
            "d.id AS d_id, d.c_id AS d_c_id "
            "FROM c JOIN d ON c.id = d.c_id) AS anon_2 "
            "ON b.id = anon_2.c_b_id) AS anon_1 ON a.id = anon_1.b_a_id "
            "WHERE anon_1.b_id = :id_1 AND anon_1.c_id = :id_2 AND "
            "anon_1.d_id = :id_3 "
            "ORDER BY a.id, anon_1.b_id, anon_1.c_id, anon_1.d_id"
            )

    _a_bc = (
            "SELECT a.id AS a_id, anon_1.b_id AS b_id, "
            "anon_1.b_a_id AS b_a_id, anon_1.c_id AS c_id, "
            "anon_1.c_b_id AS c_b_id FROM a JOIN "
            "(SELECT b.id AS b_id, b.a_id AS b_a_id, "
                "c.id AS c_id, c.b_id AS c_b_id "
                "FROM b JOIN c ON b.id = c.b_id) AS anon_1 "
            "ON a.id = anon_1.b_a_id "
            "WHERE anon_1.b_id = :id_1 AND anon_1.c_id = :id_2 "
            "ORDER BY a.id, anon_1.b_id, anon_1.c_id"
            )

    _a_bc_comma_a1_selbc = (
            "SELECT a.id AS a_id, a_1.id AS a_1_id, anon_1.b_id AS b_id, "
            "anon_1.b_a_id AS b_a_id, anon_1.c_id AS c_id, "
            "anon_1.c_b_id AS c_b_id, anon_2.b_id AS anon_2_b_id, "
            "anon_2.b_a_id AS anon_2_b_a_id, anon_2.c_id AS anon_2_c_id, "
            "anon_2.c_b_id AS anon_2_c_b_id FROM a "
            "JOIN (SELECT b.id AS b_id, b.a_id AS b_a_id, c.id AS c_id, "
            "c.b_id AS c_b_id FROM b JOIN c ON b.id = c.b_id) AS anon_1 "
            "ON a.id = anon_1.b_a_id, "
            "a AS a_1 JOIN "
                "(SELECT b.id AS b_id, b.a_id AS b_a_id, "
                "c.id AS c_id, c.b_id AS c_b_id "
                "FROM b JOIN c ON b.id = c.b_id) AS anon_2 "
            "ON a_1.id = anon_2.b_a_id ORDER BY anon_2.b_id"
        )

    _a_bkeyassoc = (
        "SELECT a.id AS a_id, anon_1.b_key_id AS b_key_id "
        "FROM a JOIN "
        "(SELECT b_key.id AS b_key_id, a_to_b_key.aid AS a_to_b_key_aid, "
        "a_to_b_key.bid AS a_to_b_key_bid FROM b_key "
        "JOIN a_to_b_key ON b_key.id = a_to_b_key.bid) AS anon_1 "
        "ON a.id = anon_1.a_to_b_key_aid"
        )

    _a_bkeyassoc_aliased = (
        "SELECT a.id AS a_id, anon_1.b_key_1_id AS b_key_1_id "
        "FROM a JOIN (SELECT b_key_1.id AS b_key_1_id, "
        "a_to_b_key_1.aid AS a_to_b_key_1_aid, "
        "a_to_b_key_1.bid AS a_to_b_key_1_bid FROM b_key AS b_key_1 "
        "JOIN a_to_b_key AS a_to_b_key_1 ON b_key_1.id = a_to_b_key_1.bid) AS "
        "anon_1 ON a.id = anon_1.a_to_b_key_1_aid"
        )

    _a_bkeyselect_bkey = (
        "SELECT a.id AS a_id, anon_2.anon_1_aid AS anon_1_aid, "
        "anon_2.anon_1_bid AS anon_1_bid, anon_2.b_key_id AS b_key_id "
        "FROM a JOIN (SELECT anon_1.aid AS anon_1_aid, anon_1.bid AS anon_1_bid, "
            "b_key.id AS b_key_id "
            "FROM (SELECT a_to_b_key.aid AS aid, a_to_b_key.bid AS bid "
                "FROM a_to_b_key) AS anon_1 "
        "JOIN b_key ON b_key.id = anon_1.bid) AS anon_2 ON a.id = anon_2.anon_1_aid"
    )



class JoinPlainTest(_JoinRewriteTestBase, fixtures.TestBase):
    """test rendering of each join with normal nesting."""
    @util.classproperty
    def __dialect__(cls):
        dialect = default.DefaultDialect()
        return dialect

    _a_bkeyselect_bkey = (
        "SELECT a.id AS a_id, b_key.id AS b_key_id FROM a JOIN "
        "((SELECT a_to_b_key.aid AS aid, a_to_b_key.bid AS bid "
            "FROM a_to_b_key) AS anon_1 JOIN b_key ON b_key.id = anon_1.bid) "
        "ON a.id = anon_1.aid"
    )
    _a__b_dc = (
            "SELECT a.id AS a_id, b.id AS b_id, "
            "b.a_id AS b_a_id, c.id AS c_id, "
            "c.b_id AS c_b_id, d.id AS d_id, "
            "d.c_id AS d_c_id "
            "FROM a JOIN (b JOIN (c JOIN d ON c.id = d.c_id) "
            "ON b.id = c.b_id) ON a.id = b.a_id "
            "WHERE b.id = :id_1 AND c.id = :id_2 AND "
            "d.id = :id_3 "
            "ORDER BY a.id, b.id, c.id, d.id"
            )


    _a_bc = (
            "SELECT a.id AS a_id, b.id AS b_id, "
            "b.a_id AS b_a_id, c.id AS c_id, "
            "c.b_id AS c_b_id FROM a JOIN "
            "(b JOIN c ON b.id = c.b_id) "
            "ON a.id = b.a_id "
            "WHERE b.id = :id_1 AND c.id = :id_2 "
            "ORDER BY a.id, b.id, c.id"
            )

    _a_bc_comma_a1_selbc = (
            "SELECT a.id AS a_id, a_1.id AS a_1_id, b.id AS b_id, "
            "b.a_id AS b_a_id, c.id AS c_id, "
            "c.b_id AS c_b_id, anon_1.b_id AS anon_1_b_id, "
            "anon_1.b_a_id AS anon_1_b_a_id, anon_1.c_id AS anon_1_c_id, "
            "anon_1.c_b_id AS anon_1_c_b_id FROM a "
            "JOIN (b JOIN c ON b.id = c.b_id) "
            "ON a.id = b.a_id, "
            "a AS a_1 JOIN "
                "(SELECT b.id AS b_id, b.a_id AS b_a_id, "
                "c.id AS c_id, c.b_id AS c_b_id "
                "FROM b JOIN c ON b.id = c.b_id) AS anon_1 "
            "ON a_1.id = anon_1.b_a_id ORDER BY anon_1.b_id"
        )

    _a_bkeyassoc = (
        "SELECT a.id AS a_id, b_key.id AS b_key_id "
        "FROM a JOIN "
        "(b_key JOIN a_to_b_key ON b_key.id = a_to_b_key.bid) "
        "ON a.id = a_to_b_key.aid"
        )

    _a_bkeyassoc_aliased = (
        "SELECT a.id AS a_id, b_key_1.id AS b_key_1_id FROM a "
        "JOIN (b_key AS b_key_1 JOIN a_to_b_key AS a_to_b_key_1 "
        "ON b_key_1.id = a_to_b_key_1.bid) ON a.id = a_to_b_key_1.aid"
    )

class JoinNoUseLabelsTest(_JoinRewriteTestBase, fixtures.TestBase):
    @util.classproperty
    def __dialect__(cls):
        dialect = default.DefaultDialect()
        dialect.supports_right_nested_joins = False
        return dialect

    def _test(self, s, assert_):
        s.use_labels = False
        self.assert_compile(
            s,
            assert_
        )

    _a_bkeyselect_bkey = (
        "SELECT a.id, b_key.id FROM a JOIN ((SELECT a_to_b_key.aid AS aid, "
            "a_to_b_key.bid AS bid FROM a_to_b_key) AS anon_1 "
            "JOIN b_key ON b_key.id = anon_1.bid) ON a.id = anon_1.aid"
    )

    _a__b_dc = (
            "SELECT a.id, b.id, "
            "b.a_id, c.id, "
            "c.b_id, d.id, "
            "d.c_id "
            "FROM a JOIN (b JOIN (c JOIN d ON c.id = d.c_id) "
            "ON b.id = c.b_id) ON a.id = b.a_id "
            "WHERE b.id = :id_1 AND c.id = :id_2 AND "
            "d.id = :id_3 "
            "ORDER BY a.id, b.id, c.id, d.id"
            )

    _a_bc = (
            "SELECT a.id, b.id, "
            "b.a_id, c.id, "
            "c.b_id FROM a JOIN "
            "(b JOIN c ON b.id = c.b_id) "
            "ON a.id = b.a_id "
            "WHERE b.id = :id_1 AND c.id = :id_2 "
            "ORDER BY a.id, b.id, c.id"
            )

    _a_bc_comma_a1_selbc = (
            "SELECT a.id, a_1.id, b.id, "
            "b.a_id, c.id, "
            "c.b_id, anon_1.b_id, "
            "anon_1.b_a_id, anon_1.c_id, "
            "anon_1.c_b_id FROM a "
            "JOIN (b JOIN c ON b.id = c.b_id) "
            "ON a.id = b.a_id, "
            "a AS a_1 JOIN "
                "(SELECT b.id AS b_id, b.a_id AS b_a_id, "
                "c.id AS c_id, c.b_id AS c_b_id "
                "FROM b JOIN c ON b.id = c.b_id) AS anon_1 "
            "ON a_1.id = anon_1.b_a_id ORDER BY anon_1.b_id"
        )

    _a_bkeyassoc = (
        "SELECT a.id, b_key.id FROM a JOIN (b_key JOIN a_to_b_key "
        "ON b_key.id = a_to_b_key.bid) ON a.id = a_to_b_key.aid"
        )

    _a_bkeyassoc_aliased = (
        "SELECT a.id, b_key_1.id FROM a JOIN (b_key AS b_key_1 "
        "JOIN a_to_b_key AS a_to_b_key_1 ON b_key_1.id = a_to_b_key_1.bid) "
        "ON a.id = a_to_b_key_1.aid"
    )

class JoinExecTest(_JoinRewriteTestBase, fixtures.TestBase):
    """invoke the SQL on the current backend to ensure compatibility"""

    _a_bc = _a_bc_comma_a1_selbc = _a__b_dc = _a_bkeyassoc = _a_bkeyassoc_aliased = None

    @classmethod
    def setup_class(cls):
        m.create_all(testing.db)

    @classmethod
    def teardown_class(cls):
        m.drop_all(testing.db)

    def _test(self, selectable, assert_):
        result = testing.db.execute(selectable)
        for col in selectable.inner_columns:
            assert col in result._metadata._keymap


class DialectFlagTest(fixtures.TestBase, AssertsCompiledSQL):
    def test_dialect_flag(self):
        d1 = default.DefaultDialect(supports_right_nested_joins=True)
        d2 = default.DefaultDialect(supports_right_nested_joins=False)

        j1 = b.join(c)
        j2 = a.join(j1)

        s = select([a, b, c], use_labels=True).\
            select_from(j2)

        self.assert_compile(
            s,
            "SELECT a.id AS a_id, b.id AS b_id, b.a_id AS b_a_id, c.id AS c_id, "
            "c.b_id AS c_b_id FROM a JOIN (b JOIN c ON b.id = c.b_id) "
            "ON a.id = b.a_id",
            dialect=d1
        )
        self.assert_compile(
            s,
            "SELECT a.id AS a_id, anon_1.b_id AS b_id, "
            "anon_1.b_a_id AS b_a_id, "
            "anon_1.c_id AS c_id, anon_1.c_b_id AS c_b_id "
            "FROM a JOIN (SELECT b.id AS b_id, b.a_id AS b_a_id, c.id AS c_id, "
            "c.b_id AS c_b_id FROM b JOIN c ON b.id = c.b_id) AS anon_1 "
            "ON a.id = anon_1.b_a_id",
            dialect=d2
        )
