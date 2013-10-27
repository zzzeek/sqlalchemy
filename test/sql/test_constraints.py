from sqlalchemy.testing import assert_raises, assert_raises_message
from sqlalchemy import Table, Integer, String, Column, PrimaryKeyConstraint,\
    ForeignKeyConstraint, ForeignKey, UniqueConstraint, Index, MetaData, \
    CheckConstraint, func
from sqlalchemy import exc, schema
from sqlalchemy.testing import fixtures, AssertsExecutionResults, \
                    AssertsCompiledSQL
from sqlalchemy import testing
from sqlalchemy.engine import default
from sqlalchemy.testing import engines
from sqlalchemy.testing import eq_
from sqlalchemy.testing.assertsql import AllOf, RegexSQL, ExactSQL, CompiledSQL
from sqlalchemy.sql import table, column

class ConstraintGenTest(fixtures.TestBase, AssertsExecutionResults):
    __dialect__ = 'default'

    @testing.provide_metadata
    def test_pk_fk_constraint_create(self):
        metadata = self.metadata

        Table('employees', metadata,
            Column('id', Integer),
            Column('soc', String(40)),
            Column('name', String(30)),
            PrimaryKeyConstraint('id', 'soc')
            )
        Table('elements', metadata,
            Column('id', Integer),
            Column('stuff', String(30)),
            Column('emp_id', Integer),
            Column('emp_soc', String(40)),
            PrimaryKeyConstraint('id', name='elements_primkey'),
            ForeignKeyConstraint(['emp_id', 'emp_soc'],
                                ['employees.id', 'employees.soc'])
            )
        self.assert_sql_execution(
            testing.db,
            lambda: metadata.create_all(checkfirst=False),
            CompiledSQL('CREATE TABLE employees ('
                    'id INTEGER, '
                    'soc VARCHAR(40), '
                    'name VARCHAR(30), '
                    'PRIMARY KEY (id, soc)'
                    ')'
            ),
            CompiledSQL('CREATE TABLE elements ('
                    'id INTEGER, '
                    'stuff VARCHAR(30), '
                    'emp_id INTEGER, '
                    'emp_soc VARCHAR(40), '
                    'CONSTRAINT elements_primkey PRIMARY KEY (id), '
                    'FOREIGN KEY(emp_id, emp_soc) '
                            'REFERENCES employees (id, soc)'
                ')'
            )
        )


    @testing.provide_metadata
    def test_cyclic_fk_table_constraint_create(self):
        metadata = self.metadata

        Table("a", metadata,
            Column('id', Integer, primary_key=True),
            Column('bid', Integer),
            ForeignKeyConstraint(["bid"], ["b.id"])
            )
        Table("b", metadata,
            Column('id', Integer, primary_key=True),
            Column("aid", Integer),
            ForeignKeyConstraint(["aid"], ["a.id"], use_alter=True, name="bfk")
            )
        self._assert_cyclic_constraint(metadata)

    @testing.provide_metadata
    def test_cyclic_fk_column_constraint_create(self):
        metadata = self.metadata

        Table("a", metadata,
            Column('id', Integer, primary_key=True),
            Column('bid', Integer, ForeignKey("b.id")),
            )
        Table("b", metadata,
            Column('id', Integer, primary_key=True),
            Column("aid", Integer,
                ForeignKey("a.id", use_alter=True, name="bfk")
                ),
            )
        self._assert_cyclic_constraint(metadata)

    def _assert_cyclic_constraint(self, metadata):
        assertions = [
            CompiledSQL('CREATE TABLE b ('
                    'id INTEGER NOT NULL, '
                    'aid INTEGER, '
                    'PRIMARY KEY (id)'
                    ')'
                    ),
            CompiledSQL('CREATE TABLE a ('
                    'id INTEGER NOT NULL, '
                    'bid INTEGER, '
                    'PRIMARY KEY (id), '
                    'FOREIGN KEY(bid) REFERENCES b (id)'
                    ')'
                ),
        ]
        if testing.db.dialect.supports_alter:
            assertions.append(
                CompiledSQL('ALTER TABLE b ADD CONSTRAINT bfk '
                        'FOREIGN KEY(aid) REFERENCES a (id)')
            )
        self.assert_sql_execution(
            testing.db,
            lambda: metadata.create_all(checkfirst=False),
            *assertions
        )

        assertions = []
        if testing.db.dialect.supports_alter:
            assertions.append(CompiledSQL('ALTER TABLE b DROP CONSTRAINT bfk'))
        assertions.extend([
            CompiledSQL("DROP TABLE a"),
            CompiledSQL("DROP TABLE b"),
            ])
        self.assert_sql_execution(
            testing.db,
            lambda: metadata.drop_all(checkfirst=False),
            *assertions
        )

    @testing.provide_metadata
    def test_check_constraint_create(self):
        metadata = self.metadata

        Table('foo', metadata,
            Column('id', Integer, primary_key=True),
            Column('x', Integer),
            Column('y', Integer),
            CheckConstraint('x>y'))
        Table('bar', metadata,
            Column('id', Integer, primary_key=True),
            Column('x', Integer, CheckConstraint('x>7')),
            Column('z', Integer)
            )

        self.assert_sql_execution(
            testing.db,
            lambda: metadata.create_all(checkfirst=False),
            AllOf(
                CompiledSQL('CREATE TABLE foo ('
                        'id INTEGER NOT NULL, '
                        'x INTEGER, '
                        'y INTEGER, '
                        'PRIMARY KEY (id), '
                        'CHECK (x>y)'
                        ')'
                        ),
                CompiledSQL('CREATE TABLE bar ('
                        'id INTEGER NOT NULL, '
                        'x INTEGER CHECK (x>7), '
                        'z INTEGER, '
                        'PRIMARY KEY (id)'
                        ')'
                )
            )
        )

    @testing.provide_metadata
    def test_unique_constraint_create(self):
        metadata = self.metadata

        Table('foo', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', String(30), unique=True))
        Table('bar', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', String(30)),
            Column('value2', String(30)),
            UniqueConstraint('value', 'value2', name='uix1')
            )

        self.assert_sql_execution(
            testing.db,
            lambda: metadata.create_all(checkfirst=False),
            AllOf(
                CompiledSQL('CREATE TABLE foo ('
                        'id INTEGER NOT NULL, '
                        'value VARCHAR(30), '
                        'PRIMARY KEY (id), '
                        'UNIQUE (value)'
                    ')'),
                CompiledSQL('CREATE TABLE bar ('
                        'id INTEGER NOT NULL, '
                        'value VARCHAR(30), '
                        'value2 VARCHAR(30), '
                        'PRIMARY KEY (id), '
                        'CONSTRAINT uix1 UNIQUE (value, value2)'
                        ')')
            )
        )

    @testing.provide_metadata
    def test_index_create(self):
        metadata = self.metadata

        employees = Table('employees', metadata,
                          Column('id', Integer, primary_key=True),
                          Column('first_name', String(30)),
                          Column('last_name', String(30)),
                          Column('email_address', String(30)))

        i = Index('employee_name_index',
                  employees.c.last_name, employees.c.first_name)
        assert i in employees.indexes

        i2 = Index('employee_email_index',
                   employees.c.email_address, unique=True)
        assert i2 in employees.indexes

        self.assert_sql_execution(
            testing.db,
            lambda: metadata.create_all(checkfirst=False),
            RegexSQL("^CREATE TABLE"),
            AllOf(
                CompiledSQL('CREATE INDEX employee_name_index ON '
                        'employees (last_name, first_name)', []),
                CompiledSQL('CREATE UNIQUE INDEX employee_email_index ON '
                        'employees (email_address)', [])
            )
        )

    @testing.provide_metadata
    def test_index_create_camelcase(self):
        """test that mixed-case index identifiers are legal"""

        metadata = self.metadata

        employees = Table('companyEmployees', metadata,
                          Column('id', Integer, primary_key=True),
                          Column('firstName', String(30)),
                          Column('lastName', String(30)),
                          Column('emailAddress', String(30)))



        Index('employeeNameIndex',
                  employees.c.lastName, employees.c.firstName)

        Index('employeeEmailIndex',
                  employees.c.emailAddress, unique=True)

        self.assert_sql_execution(
            testing.db,
            lambda: metadata.create_all(checkfirst=False),
            RegexSQL("^CREATE TABLE"),
            AllOf(
                CompiledSQL('CREATE INDEX "employeeNameIndex" ON '
                        '"companyEmployees" ("lastName", "firstName")', []),
                CompiledSQL('CREATE UNIQUE INDEX "employeeEmailIndex" ON '
                        '"companyEmployees" ("emailAddress")', [])
            )
        )

    @testing.provide_metadata
    def test_index_create_inline(self):
        # test an index create using index=True, unique=True

        metadata = self.metadata

        events = Table('events', metadata,
                       Column('id', Integer, primary_key=True),
                       Column('name', String(30), index=True, unique=True),
                       Column('location', String(30), index=True),
                       Column('sport', String(30)),
                       Column('announcer', String(30)),
                       Column('winner', String(30)))

        Index('sport_announcer', events.c.sport, events.c.announcer,
                                    unique=True)
        Index('idx_winners', events.c.winner)

        eq_(
            set(ix.name for ix in events.indexes),
            set(['ix_events_name', 'ix_events_location',
                        'sport_announcer', 'idx_winners'])
        )

        self.assert_sql_execution(
            testing.db,
            lambda: events.create(testing.db),
            RegexSQL("^CREATE TABLE events"),
            AllOf(
                ExactSQL('CREATE UNIQUE INDEX ix_events_name ON events '
                                        '(name)'),
                ExactSQL('CREATE INDEX ix_events_location ON events '
                                        '(location)'),
                ExactSQL('CREATE UNIQUE INDEX sport_announcer ON events '
                                        '(sport, announcer)'),
                ExactSQL('CREATE INDEX idx_winners ON events (winner)')
            )
        )

    @testing.provide_metadata
    def test_index_functional_create(self):
        metadata = self.metadata

        t = Table('sometable', metadata,
                Column('id', Integer, primary_key=True),
                Column('data', String(50))
            )
        Index('myindex', t.c.data.desc())
        self.assert_sql_execution(
            testing.db,
            lambda: t.create(testing.db),
            CompiledSQL('CREATE TABLE sometable (id INTEGER NOT NULL, '
                            'data VARCHAR(50), PRIMARY KEY (id))'),
            ExactSQL('CREATE INDEX myindex ON sometable (data DESC)')
        )

class ConstraintCompilationTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = 'default'

    def test_create_plain(self):
        t = Table('t', MetaData(), Column('x', Integer))
        i = Index("xyz", t.c.x)
        self.assert_compile(
            schema.CreateIndex(i),
            "CREATE INDEX xyz ON t (x)"
        )

    def test_drop_plain_unattached(self):
        self.assert_compile(
            schema.DropIndex(Index(name="xyz")),
            "DROP INDEX xyz"
        )

    def test_drop_plain(self):
        self.assert_compile(
            schema.DropIndex(Index(name="xyz")),
            "DROP INDEX xyz"
        )

    def test_create_schema(self):
        t = Table('t', MetaData(), Column('x', Integer), schema="foo")
        i = Index("xyz", t.c.x)
        self.assert_compile(
            schema.CreateIndex(i),
            "CREATE INDEX xyz ON foo.t (x)"
        )

    def test_drop_schema(self):
        t = Table('t', MetaData(), Column('x', Integer), schema="foo")
        i = Index("xyz", t.c.x)
        self.assert_compile(
            schema.DropIndex(i),
            "DROP INDEX foo.xyz"
        )


    def test_too_long_idx_name(self):
        dialect = testing.db.dialect.__class__()

        for max_ident, max_index in [(22, None), (256, 22)]:
            dialect.max_identifier_length = max_ident
            dialect.max_index_name_length = max_index

            for tname, cname, exp in [
                ('sometable', 'this_name_is_too_long', 'ix_sometable_t_09aa'),
                ('sometable', 'this_name_alsois_long', 'ix_sometable_t_3cf1'),
            ]:

                t1 = Table(tname, MetaData(),
                            Column(cname, Integer, index=True),
                        )
                ix1 = list(t1.indexes)[0]

                self.assert_compile(
                    schema.CreateIndex(ix1),
                    "CREATE INDEX %s "
                    "ON %s (%s)" % (exp, tname, cname),
                    dialect=dialect
                )

        dialect.max_identifier_length = 22
        dialect.max_index_name_length = None

        t1 = Table('t', MetaData(), Column('c', Integer))
        assert_raises(
            exc.IdentifierError,
            schema.CreateIndex(Index(
                        "this_other_name_is_too_long_for_what_were_doing",
                        t1.c.c)).compile,
            dialect=dialect
        )

    def test_functional_index(self):
        metadata = MetaData()
        x = Table('x', metadata,
                Column('q', String(50))
            )
        idx = Index('y', func.lower(x.c.q))

        self.assert_compile(
            schema.CreateIndex(idx),
            "CREATE INDEX y ON x (lower(q))"
        )

        self.assert_compile(
            schema.CreateIndex(idx),
            "CREATE INDEX y ON x (lower(q))",
            dialect=testing.db.dialect
        )

    def test_index_declaration_inline(self):
        metadata = MetaData()

        t1 = Table('t1', metadata,
            Column('x', Integer),
            Column('y', Integer),
            Index('foo', 'x', 'y')
        )
        self.assert_compile(
            schema.CreateIndex(list(t1.indexes)[0]),
            "CREATE INDEX foo ON t1 (x, y)"
        )

    def _test_deferrable(self, constraint_factory):
        dialect = default.DefaultDialect()

        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer),
                  constraint_factory(deferrable=True))

        sql = str(schema.CreateTable(t).compile(dialect=dialect))
        assert 'DEFERRABLE' in sql, sql
        assert 'NOT DEFERRABLE' not in sql, sql

        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer),
                  constraint_factory(deferrable=False))

        sql = str(schema.CreateTable(t).compile(dialect=dialect))
        assert 'NOT DEFERRABLE' in sql


        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer),
                  constraint_factory(deferrable=True, initially='IMMEDIATE'))
        sql = str(schema.CreateTable(t).compile(dialect=dialect))
        assert 'NOT DEFERRABLE' not in sql
        assert 'INITIALLY IMMEDIATE' in sql

        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer),
                  constraint_factory(deferrable=True, initially='DEFERRED'))
        sql = str(schema.CreateTable(t).compile(dialect=dialect))

        assert 'NOT DEFERRABLE' not in sql
        assert 'INITIALLY DEFERRED' in sql

    def test_column_level_ck_name(self):
        t = Table('tbl', MetaData(),
            Column('a', Integer, CheckConstraint("a > 5",
                                name="ck_a_greater_five"))
        )
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE tbl (a INTEGER CONSTRAINT "
            "ck_a_greater_five CHECK (a > 5))"
        )
    def test_deferrable_pk(self):
        factory = lambda **kw: PrimaryKeyConstraint('a', **kw)
        self._test_deferrable(factory)

    def test_deferrable_table_fk(self):
        factory = lambda **kw: ForeignKeyConstraint(['b'], ['tbl.a'], **kw)
        self._test_deferrable(factory)

    def test_deferrable_column_fk(self):
        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer,
                         ForeignKey('tbl.a', deferrable=True,
                                    initially='DEFERRED')))

        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE tbl (a INTEGER, b INTEGER, "
            "FOREIGN KEY(b) REFERENCES tbl "
            "(a) DEFERRABLE INITIALLY DEFERRED)",
        )

    def test_fk_match_clause(self):
        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer,
                         ForeignKey('tbl.a', match="SIMPLE")))

        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE tbl (a INTEGER, b INTEGER, "
            "FOREIGN KEY(b) REFERENCES tbl "
            "(a) MATCH SIMPLE)",
        )

        self.assert_compile(
            schema.AddConstraint(list(t.foreign_keys)[0].constraint),
            "ALTER TABLE tbl ADD FOREIGN KEY(b) "
            "REFERENCES tbl (a) MATCH SIMPLE"
        )

    def test_deferrable_unique(self):
        factory = lambda **kw: UniqueConstraint('b', **kw)
        self._test_deferrable(factory)

    def test_deferrable_table_check(self):
        factory = lambda **kw: CheckConstraint('a < b', **kw)
        self._test_deferrable(factory)

    def test_multiple(self):
        m = MetaData()
        Table("foo", m,
            Column('id', Integer, primary_key=True),
            Column('bar', Integer, primary_key=True)
        )
        tb = Table("some_table", m,
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        Column('foo_bar', Integer, ForeignKey('foo.bar')),
        )
        self.assert_compile(
            schema.CreateTable(tb),
            "CREATE TABLE some_table ("
                "id INTEGER NOT NULL, "
                "foo_id INTEGER, "
                "foo_bar INTEGER, "
                "PRIMARY KEY (id), "
                "FOREIGN KEY(foo_id) REFERENCES foo (id), "
                "FOREIGN KEY(foo_bar) REFERENCES foo (bar))"
        )

    def test_deferrable_column_check(self):
        t = Table('tbl', MetaData(),
                  Column('a', Integer),
                  Column('b', Integer,
                         CheckConstraint('a < b',
                                         deferrable=True,
                                         initially='DEFERRED')))

        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE tbl (a INTEGER, b INTEGER CHECK (a < b) "
                "DEFERRABLE INITIALLY DEFERRED)"
        )

    def test_use_alter(self):
        m = MetaData()
        Table('t', m,
                  Column('a', Integer),
        )

        Table('t2', m,
                Column('a', Integer, ForeignKey('t.a', use_alter=True,
                                                        name='fk_ta')),
                Column('b', Integer, ForeignKey('t.a', name='fk_tb'))
        )

        e = engines.mock_engine(dialect_name='postgresql')
        m.create_all(e)
        m.drop_all(e)

        e.assert_sql([
            'CREATE TABLE t (a INTEGER)',
            'CREATE TABLE t2 (a INTEGER, b INTEGER, CONSTRAINT fk_tb '
                            'FOREIGN KEY(b) REFERENCES t (a))',
            'ALTER TABLE t2 '
                    'ADD CONSTRAINT fk_ta FOREIGN KEY(a) REFERENCES t (a)',
            'ALTER TABLE t2 DROP CONSTRAINT fk_ta',
            'DROP TABLE t2',
            'DROP TABLE t'
        ])

    def _constraint_create_fixture(self):
        m = MetaData()

        t = Table('tbl', m,
                  Column('a', Integer),
                  Column('b', Integer)
        )

        t2 = Table('t2', m,
                Column('a', Integer),
                Column('b', Integer)
        )

        return t, t2

    def test_render_ck_constraint_inline(self):
        t, t2 = self._constraint_create_fixture()

        CheckConstraint('a < b', name="my_test_constraint",
                                        deferrable=True, initially='DEFERRED',
                                        table=t)

        # before we create an AddConstraint,
        # the CONSTRAINT comes out inline
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE tbl ("
            "a INTEGER, "
            "b INTEGER, "
            "CONSTRAINT my_test_constraint CHECK (a < b) "
                        "DEFERRABLE INITIALLY DEFERRED"
            ")"
        )

    def test_render_ck_constraint_external(self):
        t, t2 = self._constraint_create_fixture()

        constraint = CheckConstraint('a < b', name="my_test_constraint",
                                        deferrable=True, initially='DEFERRED',
                                        table=t)

        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE tbl ADD CONSTRAINT my_test_constraint "
                    "CHECK (a < b) DEFERRABLE INITIALLY DEFERRED"
        )

    def test_external_ck_constraint_cancels_internal(self):
        t, t2 = self._constraint_create_fixture()

        constraint = CheckConstraint('a < b', name="my_test_constraint",
                                        deferrable=True, initially='DEFERRED',
                                        table=t)

        schema.AddConstraint(constraint)

        # once we make an AddConstraint,
        # inline compilation of the CONSTRAINT
        # is disabled
        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE tbl ("
            "a INTEGER, "
            "b INTEGER"
            ")"
        )

    def test_render_drop_constraint(self):
        t, t2 = self._constraint_create_fixture()

        constraint = CheckConstraint('a < b', name="my_test_constraint",
                                        deferrable=True, initially='DEFERRED',
                                        table=t)

        self.assert_compile(
            schema.DropConstraint(constraint),
            "ALTER TABLE tbl DROP CONSTRAINT my_test_constraint"
        )

    def test_render_drop_constraint_cascade(self):
        t, t2 = self._constraint_create_fixture()

        constraint = CheckConstraint('a < b', name="my_test_constraint",
                                        deferrable=True, initially='DEFERRED',
                                        table=t)

        self.assert_compile(
            schema.DropConstraint(constraint, cascade=True),
            "ALTER TABLE tbl DROP CONSTRAINT my_test_constraint CASCADE"
        )

    def test_render_add_fk_constraint_stringcol(self):
        t, t2 = self._constraint_create_fixture()

        constraint = ForeignKeyConstraint(["b"], ["t2.a"])
        t.append_constraint(constraint)
        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE tbl ADD FOREIGN KEY(b) REFERENCES t2 (a)"
        )

    def test_render_add_fk_constraint_realcol(self):
        t, t2 = self._constraint_create_fixture()

        constraint = ForeignKeyConstraint([t.c.a], [t2.c.b])
        t.append_constraint(constraint)
        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE tbl ADD FOREIGN KEY(a) REFERENCES t2 (b)"
        )

    def test_render_add_uq_constraint_stringcol(self):
        t, t2 = self._constraint_create_fixture()

        constraint = UniqueConstraint("a", "b", name="uq_cst")
        t2.append_constraint(constraint)
        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE t2 ADD CONSTRAINT uq_cst UNIQUE (a, b)"
        )

    def test_render_add_uq_constraint_realcol(self):
        t, t2 = self._constraint_create_fixture()

        constraint = UniqueConstraint(t2.c.a, t2.c.b, name="uq_cs2")
        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE t2 ADD CONSTRAINT uq_cs2 UNIQUE (a, b)"
        )

    def test_render_add_pk_constraint(self):
        t, t2 = self._constraint_create_fixture()

        assert t.c.a.primary_key is False
        constraint = PrimaryKeyConstraint(t.c.a)
        assert t.c.a.primary_key is True
        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE tbl ADD PRIMARY KEY (a)"
        )

    def test_render_check_constraint_sql_literal(self):
        t, t2 = self._constraint_create_fixture()

        constraint = CheckConstraint(t.c.a > 5)

        self.assert_compile(
            schema.AddConstraint(constraint),
            "ALTER TABLE tbl ADD CHECK (a > 5)"
        )

    def test_render_index_sql_literal(self):
        t, t2 = self._constraint_create_fixture()

        constraint = Index('name', t.c.a + 5)

        self.assert_compile(
            schema.CreateIndex(constraint),
            "CREATE INDEX name ON tbl (a + 5)"
        )


class ConstraintAPITest(fixtures.TestBase):
    def test_double_fk_usage_raises(self):
        f = ForeignKey('b.id')

        Column('x', Integer, f)
        assert_raises(exc.InvalidRequestError, Column, "y", Integer, f)

    def test_auto_append_constraint(self):
        m = MetaData()

        t = Table('tbl', m,
                  Column('a', Integer),
                  Column('b', Integer)
        )

        t2 = Table('t2', m,
                Column('a', Integer),
                Column('b', Integer)
        )

        for c in (
            UniqueConstraint(t.c.a),
            CheckConstraint(t.c.a > 5),
            ForeignKeyConstraint([t.c.a], [t2.c.a]),
            PrimaryKeyConstraint(t.c.a)
        ):
            assert c in t.constraints
            t.append_constraint(c)
            assert c in t.constraints

        c = Index('foo', t.c.a)
        assert c in t.indexes

    def test_auto_append_lowercase_table(self):
        t = table('t', column('a'))
        t2 = table('t2', column('a'))
        for c in (
            UniqueConstraint(t.c.a),
            CheckConstraint(t.c.a > 5),
            ForeignKeyConstraint([t.c.a], [t2.c.a]),
            PrimaryKeyConstraint(t.c.a),
            Index('foo', t.c.a)
        ):
            assert True

    def test_tometadata_ok(self):
        m = MetaData()

        t = Table('tbl', m,
                  Column('a', Integer),
                  Column('b', Integer)
        )

        t2 = Table('t2', m,
                Column('a', Integer),
                Column('b', Integer)
        )

        UniqueConstraint(t.c.a)
        CheckConstraint(t.c.a > 5)
        ForeignKeyConstraint([t.c.a], [t2.c.a])
        PrimaryKeyConstraint(t.c.a)

        m2 = MetaData()

        t3 = t.tometadata(m2)

        eq_(len(t3.constraints), 4)

        for c in t3.constraints:
            assert c.table is t3

    def test_check_constraint_copy(self):
        m = MetaData()
        t = Table('tbl', m,
                  Column('a', Integer),
                  Column('b', Integer)
        )
        ck = CheckConstraint(t.c.a > 5)
        ck2 = ck.copy()
        assert ck in t.constraints
        assert ck2 not in t.constraints


    def test_ambig_check_constraint_auto_append(self):
        m = MetaData()

        t = Table('tbl', m,
                  Column('a', Integer),
                  Column('b', Integer)
        )

        t2 = Table('t2', m,
                Column('a', Integer),
                Column('b', Integer)
        )
        c = CheckConstraint(t.c.a > t2.c.b)
        assert c not in t.constraints
        assert c not in t2.constraints

    def test_index_asserts_cols_standalone(self):
        metadata = MetaData()

        t1 = Table('t1', metadata,
            Column('x', Integer)
        )
        t2 = Table('t2', metadata,
            Column('y', Integer)
        )
        assert_raises_message(
            exc.ArgumentError,
            "Column 't2.y' is not part of table 't1'.",
            Index,
            "bar", t1.c.x, t2.c.y
        )

    def test_index_asserts_cols_inline(self):
        metadata = MetaData()

        t1 = Table('t1', metadata,
            Column('x', Integer)
        )
        assert_raises_message(
            exc.ArgumentError,
            "Index 'bar' is against table 't1', and "
            "cannot be associated with table 't2'.",
            Table, 't2', metadata,
                Column('y', Integer),
                Index('bar', t1.c.x)
        )

    def test_raise_index_nonexistent_name(self):
        m = MetaData()
        # the KeyError isn't ideal here, a nicer message
        # perhaps
        assert_raises(
            KeyError,
            Table, 't', m, Column('x', Integer), Index("foo", "q")
        )

    def test_raise_not_a_column(self):
        assert_raises(
            exc.ArgumentError,
            Index, "foo", 5
        )

    def test_raise_expr_no_column(self):
        idx = Index('foo', func.lower(5))

        assert_raises_message(
            exc.CompileError,
            "Index 'foo' is not associated with any table.",
            schema.CreateIndex(idx).compile, dialect=testing.db.dialect
        )
        assert_raises_message(
            exc.CompileError,
            "Index 'foo' is not associated with any table.",
            schema.CreateIndex(idx).compile
        )


    def test_no_warning_w_no_columns(self):
        # I think the test here is, there is no warning.
        # people want to create empty indexes for the purpose of
        # a drop.
        idx = Index(name="foo")

        assert_raises_message(
            exc.CompileError,
            "Index 'foo' is not associated with any table.",
            schema.CreateIndex(idx).compile, dialect=testing.db.dialect
        )
        assert_raises_message(
            exc.CompileError,
            "Index 'foo' is not associated with any table.",
            schema.CreateIndex(idx).compile
        )

    def test_raise_clauseelement_not_a_column(self):
        m = MetaData()
        t2 = Table('t2', m, Column('x', Integer))
        class SomeClass(object):
            def __clause_element__(self):
                return t2
        assert_raises(
            exc.ArgumentError,
            Index, "foo", SomeClass()
        )
