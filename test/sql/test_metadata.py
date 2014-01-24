from sqlalchemy.testing import assert_raises
from sqlalchemy.testing import assert_raises_message
from sqlalchemy.testing import emits_warning

import pickle
from sqlalchemy import Integer, String, UniqueConstraint, \
    CheckConstraint, ForeignKey, MetaData, Sequence, \
    ForeignKeyConstraint, PrimaryKeyConstraint, ColumnDefault, Index, event,\
    events, Unicode, types as sqltypes, bindparam, \
    Table, Column
from sqlalchemy import schema, exc
import sqlalchemy as tsa
from sqlalchemy.testing import fixtures
from sqlalchemy import testing
from sqlalchemy.testing import ComparesTables, AssertsCompiledSQL
from sqlalchemy.testing import eq_, is_, mock
from contextlib import contextmanager

class MetaDataTest(fixtures.TestBase, ComparesTables):
    def test_metadata_connect(self):
        metadata = MetaData()
        t1 = Table('table1', metadata,
            Column('col1', Integer, primary_key=True),
            Column('col2', String(20)))
        metadata.bind = testing.db
        metadata.create_all()
        try:
            assert t1.count().scalar() == 0
        finally:
            metadata.drop_all()

    def test_metadata_contains(self):
        metadata = MetaData()
        t1 = Table('t1', metadata, Column('x', Integer))
        t2 = Table('t2', metadata, Column('x', Integer), schema='foo')
        t3 = Table('t2', MetaData(), Column('x', Integer))
        t4 = Table('t1', MetaData(), Column('x', Integer), schema='foo')

        assert "t1" in metadata
        assert "foo.t2" in metadata
        assert "t2" not in metadata
        assert "foo.t1" not in metadata
        assert t1 in metadata
        assert t2 in metadata
        assert t3 not in metadata
        assert t4 not in metadata

    def test_uninitialized_column_copy(self):
        for col in [
            Column('foo', String(), nullable=False),
            Column('baz', String(), unique=True),
            Column(Integer(), primary_key=True),
            Column('bar', Integer(), Sequence('foo_seq'), primary_key=True,
                                                            key='bar'),
            Column(Integer(), ForeignKey('bat.blah'), doc="this is a col"),
            Column('bar', Integer(), ForeignKey('bat.blah'), primary_key=True,
                                                            key='bar'),
            Column('bar', Integer(), info={'foo': 'bar'}),
        ]:
            c2 = col.copy()
            for attr in ('name', 'type', 'nullable',
                        'primary_key', 'key', 'unique', 'info',
                        'doc'):
                eq_(getattr(col, attr), getattr(c2, attr))
            eq_(len(col.foreign_keys), len(c2.foreign_keys))
            if col.default:
                eq_(c2.default.name, 'foo_seq')
            for a1, a2 in zip(col.foreign_keys, c2.foreign_keys):
                assert a1 is not a2
                eq_(a2._colspec, 'bat.blah')

    def test_col_subclass_copy(self):
        class MyColumn(schema.Column):
            def __init__(self, *args, **kw):
                self.widget = kw.pop('widget', None)
                super(MyColumn, self).__init__(*args, **kw)

            def copy(self, *arg, **kw):
                c = super(MyColumn, self).copy(*arg, **kw)
                c.widget = self.widget
                return c
        c1 = MyColumn('foo', Integer, widget='x')
        c2 = c1.copy()
        assert isinstance(c2, MyColumn)
        eq_(c2.widget, 'x')

    def test_uninitialized_column_copy_events(self):
        msgs = []
        def write(c, t):
            msgs.append("attach %s.%s" % (t.name, c.name))
        c1 = Column('foo', String())
        m = MetaData()
        for i in range(3):
            cx = c1.copy()
            # as of 0.7, these events no longer copy.  its expected
            # that listeners will be re-established from the
            # natural construction of things.
            cx._on_table_attach(write)
            Table('foo%d' % i, m, cx)
        eq_(msgs, ['attach foo0.foo', 'attach foo1.foo', 'attach foo2.foo'])

    def test_schema_collection_add(self):
        metadata = MetaData()

        Table('t1', metadata, Column('x', Integer), schema='foo')
        Table('t2', metadata, Column('x', Integer), schema='bar')
        Table('t3', metadata, Column('x', Integer))

        eq_(metadata._schemas, set(['foo', 'bar']))
        eq_(len(metadata.tables), 3)

    def test_schema_collection_remove(self):
        metadata = MetaData()

        t1 = Table('t1', metadata, Column('x', Integer), schema='foo')
        Table('t2', metadata, Column('x', Integer), schema='bar')
        t3 = Table('t3', metadata, Column('x', Integer), schema='bar')

        metadata.remove(t3)
        eq_(metadata._schemas, set(['foo', 'bar']))
        eq_(len(metadata.tables), 2)

        metadata.remove(t1)
        eq_(metadata._schemas, set(['bar']))
        eq_(len(metadata.tables), 1)

    def test_schema_collection_remove_all(self):
        metadata = MetaData()

        Table('t1', metadata, Column('x', Integer), schema='foo')
        Table('t2', metadata, Column('x', Integer), schema='bar')

        metadata.clear()
        eq_(metadata._schemas, set())
        eq_(len(metadata.tables), 0)

    def test_metadata_tables_immutable(self):
        metadata = MetaData()

        Table('t1', metadata, Column('x', Integer))
        assert 't1' in metadata.tables

        assert_raises(
            TypeError,
            lambda: metadata.tables.pop('t1')
        )

    @testing.provide_metadata
    def test_dupe_tables(self):
        metadata = self.metadata
        Table('table1', metadata,
                Column('col1', Integer, primary_key=True),
                Column('col2', String(20)))

        metadata.create_all()
        Table('table1', metadata, autoload=True)
        def go():
            Table('table1', metadata,
                    Column('col1', Integer, primary_key=True),
                    Column('col2', String(20)))
        assert_raises_message(
            tsa.exc.InvalidRequestError,
                "Table 'table1' is already defined for this "
                "MetaData instance.  Specify 'extend_existing=True' "
                "to redefine options and columns on an existing "
                "Table object.",
            go
        )

    def test_fk_copy(self):
        c1 = Column('foo', Integer)
        c2 = Column('bar', Integer)
        m = MetaData()
        t1 = Table('t', m, c1, c2)

        kw = dict(onupdate="X",
                        ondelete="Y", use_alter=True, name='f1',
                        deferrable="Z", initially="Q", link_to_name=True)

        fk1 = ForeignKey(c1, **kw)
        fk2 = ForeignKeyConstraint((c1,), (c2,), **kw)

        t1.append_constraint(fk2)
        fk1c = fk1.copy()
        fk2c = fk2.copy()

        for k in kw:
            eq_(getattr(fk1c, k), kw[k])
            eq_(getattr(fk2c, k), kw[k])

    def test_check_constraint_copy(self):
        r = lambda x: x
        c = CheckConstraint("foo bar",
                            name='name',
                            initially=True,
                            deferrable=True,
                            _create_rule=r)
        c2 = c.copy()
        eq_(c2.name, 'name')
        eq_(str(c2.sqltext), "foo bar")
        eq_(c2.initially, True)
        eq_(c2.deferrable, True)
        assert c2._create_rule is r

    def test_col_replace_w_constraint(self):
        m = MetaData()
        a = Table('a', m, Column('id', Integer, primary_key=True))

        aid = Column('a_id', ForeignKey('a.id'))
        b = Table('b', m, aid)
        b.append_column(aid)

        assert b.c.a_id.references(a.c.id)
        eq_(len(b.constraints), 2)

    def test_fk_construct(self):
        c1 = Column('foo', Integer)
        c2 = Column('bar', Integer)
        m = MetaData()
        t1 = Table('t', m, c1, c2)
        fk1 = ForeignKeyConstraint(('foo', ), ('bar', ), table=t1)
        assert fk1 in t1.constraints

    def test_fk_no_such_parent_col_error(self):
        meta = MetaData()
        a = Table('a', meta, Column('a', Integer))
        Table('b', meta, Column('b', Integer))

        def go():
            a.append_constraint(
                ForeignKeyConstraint(['x'], ['b.b'])
            )
        assert_raises_message(
            exc.ArgumentError,
            "Can't create ForeignKeyConstraint on "
            "table 'a': no column named 'x' is present.",
            go
        )

    def test_fk_given_non_col(self):
        not_a_col = bindparam('x')
        assert_raises_message(
            exc.ArgumentError,
            "String, Column, or Column-bound argument expected, got Bind",
            ForeignKey, not_a_col
        )

    def test_fk_given_non_col_clauseelem(self):
        class Foo(object):
            def __clause_element__(self):
                return bindparam('x')
        assert_raises_message(
            exc.ArgumentError,
            "String, Column, or Column-bound argument expected, got Bind",
            ForeignKey, Foo()
        )

    def test_fk_given_col_non_table(self):
        t = Table('t', MetaData(), Column('x', Integer))
        xa = t.alias().c.x
        assert_raises_message(
            exc.ArgumentError,
            "ForeignKey received Column not bound to a Table, got: .*Alias",
            ForeignKey, xa
        )

    def test_fk_given_col_non_table_clauseelem(self):
        t = Table('t', MetaData(), Column('x', Integer))
        class Foo(object):
            def __clause_element__(self):
                return t.alias().c.x

        assert_raises_message(
            exc.ArgumentError,
            "ForeignKey received Column not bound to a Table, got: .*Alias",
            ForeignKey, Foo()
        )

    def test_fk_no_such_target_col_error_upfront(self):
        meta = MetaData()
        a = Table('a', meta, Column('a', Integer))
        Table('b', meta, Column('b', Integer))

        a.append_constraint(ForeignKeyConstraint(['a'], ['b.x']))

        assert_raises_message(
            exc.NoReferencedColumnError,
            "Could not initialize target column for ForeignKey 'b.x' on "
            "table 'a': table 'b' has no column named 'x'",
            getattr, list(a.foreign_keys)[0], "column"
        )

    def test_fk_no_such_target_col_error_delayed(self):
        meta = MetaData()
        a = Table('a', meta, Column('a', Integer))
        a.append_constraint(
            ForeignKeyConstraint(['a'], ['b.x']))

        b = Table('b', meta, Column('b', Integer))

        assert_raises_message(
            exc.NoReferencedColumnError,
            "Could not initialize target column for ForeignKey 'b.x' on "
            "table 'a': table 'b' has no column named 'x'",
            getattr, list(a.foreign_keys)[0], "column"
        )


    @testing.exclude('mysql', '<', (4, 1, 1), 'early types are squirrely')
    def test_to_metadata(self):
        from sqlalchemy.testing.schema import Table
        meta = MetaData()

        table = Table('mytable', meta,
            Column('myid', Integer, Sequence('foo_id_seq'), primary_key=True),
            Column('name', String(40), nullable=True),
            Column('foo', String(40), nullable=False, server_default='x',
                                                        server_onupdate='q'),
            Column('bar', String(40), nullable=False, default='y',
                                                        onupdate='z'),
            Column('description', String(30),
                                    CheckConstraint("description='hi'")),
            UniqueConstraint('name'),
            test_needs_fk=True
        )

        table2 = Table('othertable', meta,
            Column('id', Integer, Sequence('foo_seq'), primary_key=True),
            Column('myid', Integer,
                        ForeignKey('mytable.myid'),
                    ),
            test_needs_fk=True
            )

        def test_to_metadata():
            meta2 = MetaData()
            table_c = table.tometadata(meta2)
            table2_c = table2.tometadata(meta2)
            return (table_c, table2_c)

        def test_pickle():
            meta.bind = testing.db
            meta2 = pickle.loads(pickle.dumps(meta))
            assert meta2.bind is None
            pickle.loads(pickle.dumps(meta2))
            return (meta2.tables['mytable'], meta2.tables['othertable'])

        def test_pickle_via_reflect():
            # this is the most common use case, pickling the results of a
            # database reflection
            meta2 = MetaData(bind=testing.db)
            t1 = Table('mytable', meta2, autoload=True)
            Table('othertable', meta2, autoload=True)
            meta3 = pickle.loads(pickle.dumps(meta2))
            assert meta3.bind is None
            assert meta3.tables['mytable'] is not t1

            return (meta3.tables['mytable'], meta3.tables['othertable'])

        meta.create_all(testing.db)
        try:
            for test, has_constraints, reflect in \
                    (test_to_metadata, True, False), \
                    (test_pickle, True, False), \
                    (test_pickle_via_reflect, False, True):
                table_c, table2_c = test()
                self.assert_tables_equal(table, table_c)
                self.assert_tables_equal(table2, table2_c)
                assert table is not table_c
                assert table.primary_key is not table_c.primary_key
                assert list(table2_c.c.myid.foreign_keys)[0].column \
                    is table_c.c.myid
                assert list(table2_c.c.myid.foreign_keys)[0].column \
                    is not table.c.myid
                assert 'x' in str(table_c.c.foo.server_default.arg)
                if not reflect:
                    assert isinstance(table_c.c.myid.default, Sequence)
                    assert str(table_c.c.foo.server_onupdate.arg) == 'q'
                    assert str(table_c.c.bar.default.arg) == 'y'
                    assert getattr(table_c.c.bar.onupdate.arg, 'arg',
                                   table_c.c.bar.onupdate.arg) == 'z'
                    assert isinstance(table2_c.c.id.default, Sequence)

                # constraints dont get reflected for any dialect right
                # now

                if has_constraints:
                    for c in table_c.c.description.constraints:
                        if isinstance(c, CheckConstraint):
                            break
                    else:
                        assert False
                    assert str(c.sqltext) == "description='hi'"
                    for c in table_c.constraints:
                        if isinstance(c, UniqueConstraint):
                            break
                    else:
                        assert False
                    assert c.columns.contains_column(table_c.c.name)
                    assert not c.columns.contains_column(table.c.name)


        finally:
            meta.drop_all(testing.db)

    def test_col_key_fk_parent_tometadata(self):
        # test #2643
        m1 = MetaData()
        a = Table('a', m1, Column('x', Integer))
        b = Table('b', m1, Column('x', Integer, ForeignKey('a.x'), key='y'))
        assert b.c.y.references(a.c.x)

        m2 = MetaData()
        b2 = b.tometadata(m2)
        a2 = a.tometadata(m2)
        assert b2.c.y.references(a2.c.x)


    def test_pickle_metadata_sequence_restated(self):
        m1 = MetaData()
        Table('a', m1,
             Column('id', Integer, primary_key=True),
             Column('x', Integer, Sequence("x_seq")))

        m2 = pickle.loads(pickle.dumps(m1))

        s2 = Sequence("x_seq")
        t2 = Table('a', m2,
             Column('id', Integer, primary_key=True),
             Column('x', Integer, s2),
             extend_existing=True)

        assert m2._sequences['x_seq'] is t2.c.x.default
        assert m2._sequences['x_seq'] is s2


    def test_sequence_restated_replaced(self):
        """Test restatement of Sequence replaces."""

        m1 = MetaData()
        s1 = Sequence("x_seq")
        t = Table('a', m1,
             Column('x', Integer, s1)
        )
        assert m1._sequences['x_seq'] is s1

        s2 = Sequence('x_seq')
        Table('a', m1,
             Column('x', Integer, s2),
             extend_existing=True
        )
        assert t.c.x.default is s2
        assert m1._sequences['x_seq'] is s2


    def test_pickle_metadata_sequence_implicit(self):
        m1 = MetaData()
        Table('a', m1,
             Column('id', Integer, primary_key=True),
             Column('x', Integer, Sequence("x_seq")))

        m2 = pickle.loads(pickle.dumps(m1))

        t2 = Table('a', m2, extend_existing=True)

        eq_(m2._sequences, {'x_seq': t2.c.x.default})

    def test_pickle_metadata_schema(self):
        m1 = MetaData()
        Table('a', m1,
             Column('id', Integer, primary_key=True),
             Column('x', Integer, Sequence("x_seq")),
             schema='y')

        m2 = pickle.loads(pickle.dumps(m1))

        Table('a', m2, schema='y',
             extend_existing=True)

        eq_(m2._schemas, m1._schemas)

    def test_tometadata_with_schema(self):
        meta = MetaData()

        table = Table('mytable', meta,
            Column('myid', Integer, primary_key=True),
            Column('name', String(40), nullable=True),
            Column('description', String(30),
                            CheckConstraint("description='hi'")),
            UniqueConstraint('name'),
        )

        table2 = Table('othertable', meta,
            Column('id', Integer, primary_key=True),
            Column('myid', Integer, ForeignKey('mytable.myid')),
            )

        meta2 = MetaData()
        table_c = table.tometadata(meta2, schema='someschema')
        table2_c = table2.tometadata(meta2, schema='someschema')

        eq_(str(table_c.join(table2_c).onclause), str(table_c.c.myid
            == table2_c.c.myid))
        eq_(str(table_c.join(table2_c).onclause),
            'someschema.mytable.myid = someschema.othertable.myid')

    def test_tometadata_with_default_schema(self):
        meta = MetaData()

        table = Table('mytable', meta,
            Column('myid', Integer, primary_key=True),
            Column('name', String(40), nullable=True),
            Column('description', String(30),
                        CheckConstraint("description='hi'")),
            UniqueConstraint('name'),
            schema='myschema',
        )

        table2 = Table('othertable', meta,
            Column('id', Integer, primary_key=True),
            Column('myid', Integer, ForeignKey('myschema.mytable.myid')),
            schema='myschema',
            )

        meta2 = MetaData()
        table_c = table.tometadata(meta2)
        table2_c = table2.tometadata(meta2)

        eq_(str(table_c.join(table2_c).onclause), str(table_c.c.myid
            == table2_c.c.myid))
        eq_(str(table_c.join(table2_c).onclause),
            'myschema.mytable.myid = myschema.othertable.myid')

    def test_tometadata_copy_info(self):
        m = MetaData()
        fk = ForeignKey('t2.id')
        c = Column('c', Integer, fk)
        ck = CheckConstraint('c > 5')
        t = Table('t', m, c, ck)

        m.info['minfo'] = True
        fk.info['fkinfo'] = True
        c.info['cinfo'] = True
        ck.info['ckinfo'] = True
        t.info['tinfo'] = True
        t.primary_key.info['pkinfo'] = True
        fkc = [const for const in t.constraints if
                    isinstance(const, ForeignKeyConstraint)][0]
        fkc.info['fkcinfo'] = True

        m2 = MetaData()
        t2 = t.tometadata(m2)

        m.info['minfo'] = False
        fk.info['fkinfo'] = False
        c.info['cinfo'] = False
        ck.info['ckinfo'] = False
        t.primary_key.info['pkinfo'] = False
        fkc.info['fkcinfo'] = False

        eq_(m2.info, {})
        eq_(t2.info, {"tinfo": True})
        eq_(t2.c.c.info, {"cinfo": True})
        eq_(list(t2.c.c.foreign_keys)[0].info, {"fkinfo": True})
        eq_(t2.primary_key.info, {"pkinfo": True})

        fkc2 = [const for const in t2.constraints
                    if isinstance(const, ForeignKeyConstraint)][0]
        eq_(fkc2.info, {"fkcinfo": True})

        ck2 = [const for const in
                    t2.constraints if isinstance(const, CheckConstraint)][0]
        eq_(ck2.info, {"ckinfo": True})


    def test_tometadata_kwargs(self):
        meta = MetaData()

        table = Table('mytable', meta,
            Column('myid', Integer, primary_key=True),
            mysql_engine='InnoDB',
        )

        meta2 = MetaData()
        table_c = table.tometadata(meta2)

        eq_(table.kwargs, {"mysql_engine": "InnoDB"})

        eq_(table.kwargs, table_c.kwargs)

    def test_tometadata_indexes(self):
        meta = MetaData()

        table = Table('mytable', meta,
            Column('id', Integer, primary_key=True),
            Column('data1', Integer, index=True),
            Column('data2', Integer),
        )
        Index('multi', table.c.data1, table.c.data2),

        meta2 = MetaData()
        table_c = table.tometadata(meta2)

        def _get_key(i):
            return [i.name, i.unique] + \
                    sorted(i.kwargs.items()) + \
                    list(i.columns.keys())

        eq_(
            sorted([_get_key(i) for i in table.indexes]),
            sorted([_get_key(i) for i in table_c.indexes])
        )

    @emits_warning("Table '.+' already exists within the given MetaData")
    def test_tometadata_already_there(self):

        meta1 = MetaData()
        table1 = Table('mytable', meta1,
            Column('myid', Integer, primary_key=True),
        )
        meta2 = MetaData()
        table2 = Table('mytable', meta2,
            Column('yourid', Integer, primary_key=True),
        )

        table_c = table1.tometadata(meta2)
        table_d = table2.tometadata(meta2)

        # d'oh!
        assert table_c is table_d

    def test_metadata_schema_arg(self):
        m1 = MetaData(schema='sch1')
        m2 = MetaData(schema='sch1', quote_schema=True)
        m3 = MetaData(schema='sch1', quote_schema=False)
        m4 = MetaData()

        for i, (name, metadata, schema, quote_schema,
                        exp_schema, exp_quote_schema) in enumerate([
                                ('t1', m1, None, None, 'sch1', None),
                                ('t2', m1, 'sch2', None, 'sch2', None),
                                ('t3', m1, 'sch2', True, 'sch2', True),
                                ('t4', m1, 'sch1', None, 'sch1', None),
                                ('t1', m2, None, None, 'sch1', True),
                                ('t2', m2, 'sch2', None, 'sch2', None),
                                ('t3', m2, 'sch2', True, 'sch2', True),
                                ('t4', m2, 'sch1', None, 'sch1', None),
                                ('t1', m3, None, None, 'sch1', False),
                                ('t2', m3, 'sch2', None, 'sch2', None),
                                ('t3', m3, 'sch2', True, 'sch2', True),
                                ('t4', m3, 'sch1', None, 'sch1', None),
                                ('t1', m4, None, None, None, None),
                                ('t2', m4, 'sch2', None, 'sch2', None),
                                ('t3', m4, 'sch2', True, 'sch2', True),
                                ('t4', m4, 'sch1', None, 'sch1', None),
                        ]):
            kw = {}
            if schema is not None:
                kw['schema'] = schema
            if quote_schema is not None:
                kw['quote_schema'] = quote_schema
            t = Table(name, metadata, **kw)
            eq_(t.schema, exp_schema, "test %d, table schema" % i)
            eq_(t.schema.quote if t.schema is not None else None,
                            exp_quote_schema,
                            "test %d, table quote_schema" % i)
            seq = Sequence(name, metadata=metadata, **kw)
            eq_(seq.schema, exp_schema, "test %d, seq schema" % i)
            eq_(seq.schema.quote if seq.schema is not None else None,
                            exp_quote_schema,
                            "test %d, seq quote_schema" % i)

    def test_manual_dependencies(self):
        meta = MetaData()
        a = Table('a', meta, Column('foo', Integer))
        b = Table('b', meta, Column('foo', Integer))
        c = Table('c', meta, Column('foo', Integer))
        d = Table('d', meta, Column('foo', Integer))
        e = Table('e', meta, Column('foo', Integer))

        e.add_is_dependent_on(c)
        a.add_is_dependent_on(b)
        b.add_is_dependent_on(d)
        e.add_is_dependent_on(b)
        c.add_is_dependent_on(a)
        eq_(
            meta.sorted_tables,
            [d, b, a, c, e]
        )

    def test_tometadata_default_schema_metadata(self):
        meta = MetaData(schema='myschema')

        table = Table('mytable', meta,
            Column('myid', Integer, primary_key=True),
            Column('name', String(40), nullable=True),
            Column('description', String(30), CheckConstraint("description='hi'")),
            UniqueConstraint('name'),
        )

        table2 = Table('othertable', meta,
            Column('id', Integer, primary_key=True),
            Column('myid', Integer, ForeignKey('myschema.mytable.myid')),
            )

        meta2 = MetaData(schema='someschema')
        table_c = table.tometadata(meta2, schema=None)
        table2_c = table2.tometadata(meta2, schema=None)

        eq_(str(table_c.join(table2_c).onclause),
                str(table_c.c.myid == table2_c.c.myid))
        eq_(str(table_c.join(table2_c).onclause),
                "someschema.mytable.myid = someschema.othertable.myid")

    def test_tometadata_strip_schema(self):
        meta = MetaData()

        table = Table('mytable', meta,
            Column('myid', Integer, primary_key=True),
            Column('name', String(40), nullable=True),
            Column('description', String(30),
                        CheckConstraint("description='hi'")),
            UniqueConstraint('name'),
        )

        table2 = Table('othertable', meta,
            Column('id', Integer, primary_key=True),
            Column('myid', Integer, ForeignKey('mytable.myid')),
            )

        meta2 = MetaData()
        table_c = table.tometadata(meta2, schema=None)
        table2_c = table2.tometadata(meta2, schema=None)

        eq_(str(table_c.join(table2_c).onclause), str(table_c.c.myid
            == table2_c.c.myid))
        eq_(str(table_c.join(table2_c).onclause),
            'mytable.myid = othertable.myid')

    def test_nonexistent(self):
        assert_raises(tsa.exc.NoSuchTableError, Table,
                          'fake_table',
                          MetaData(testing.db), autoload=True)

    def test_assorted_repr(self):
        t1 = Table("foo", MetaData(), Column("x", Integer))
        i1 = Index("bar", t1.c.x)
        ck = schema.CheckConstraint("x > y", name="someconstraint")

        for const, exp in (
            (Sequence("my_seq"),
                "Sequence('my_seq')"),
            (Sequence("my_seq", start=5),
                "Sequence('my_seq', start=5)"),
            (Column("foo", Integer),
                "Column('foo', Integer(), table=None)"),
            (Table("bar", MetaData(), Column("x", String)),
                "Table('bar', MetaData(bind=None), "
                "Column('x', String(), table=<bar>), schema=None)"),
            (schema.DefaultGenerator(for_update=True),
                "DefaultGenerator(for_update=True)"),
            (schema.Index("bar", "c"), "Index('bar')"),
            (i1, "Index('bar', Column('x', Integer(), table=<foo>))"),
            (schema.FetchedValue(), "FetchedValue()"),
            (ck,
                    "CheckConstraint("
                    "%s"
                    ", name='someconstraint')" % repr(ck.sqltext)),
        ):
            eq_(
                repr(const),
                exp
            )

class TableTest(fixtures.TestBase, AssertsCompiledSQL):
    @testing.skip_if('mssql', 'different col format')
    def test_prefixes(self):
        from sqlalchemy import Table
        table1 = Table("temporary_table_1", MetaData(),
                      Column("col1", Integer),
                      prefixes=["TEMPORARY"])

        self.assert_compile(
            schema.CreateTable(table1),
            "CREATE TEMPORARY TABLE temporary_table_1 (col1 INTEGER)"
        )

        table2 = Table("temporary_table_2", MetaData(),
                      Column("col1", Integer),
                      prefixes=["VIRTUAL"])
        self.assert_compile(
            schema.CreateTable(table2),
            "CREATE VIRTUAL TABLE temporary_table_2 (col1 INTEGER)"
        )

    def test_table_info(self):
        metadata = MetaData()
        t1 = Table('foo', metadata, info={'x': 'y'})
        t2 = Table('bar', metadata, info={})
        t3 = Table('bat', metadata)
        assert t1.info == {'x': 'y'}
        assert t2.info == {}
        assert t3.info == {}
        for t in (t1, t2, t3):
            t.info['bar'] = 'zip'
            assert t.info['bar'] == 'zip'

    def test_c_immutable(self):
        m = MetaData()
        t1 = Table('t', m, Column('x', Integer), Column('y', Integer))
        assert_raises(
            TypeError,
            t1.c.extend, [Column('z', Integer)]
        )

        def assign():
            t1.c['z'] = Column('z', Integer)
        assert_raises(
            TypeError,
            assign
        )

        def assign2():
            t1.c.z = Column('z', Integer)
        assert_raises(
            TypeError,
            assign2
        )

    def test_autoincrement_replace(self):
        m = MetaData()

        t = Table('t', m,
            Column('id', Integer, primary_key=True)
        )

        is_(t._autoincrement_column, t.c.id)

        t = Table('t', m,
            Column('id', Integer, primary_key=True),
            extend_existing=True
        )
        is_(t._autoincrement_column, t.c.id)

    def test_pk_args_standalone(self):
        m = MetaData()
        t = Table('t', m,
                    Column('x', Integer, primary_key=True),
                    PrimaryKeyConstraint(mssql_clustered=True)
                )
        eq_(
            list(t.primary_key), [t.c.x]
        )
        eq_(
            t.primary_key.dialect_kwargs, {"mssql_clustered": True}
        )

    def test_pk_cols_sets_flags(self):
        m = MetaData()
        t = Table('t', m,
                    Column('x', Integer),
                    Column('y', Integer),
                    Column('z', Integer),
                    PrimaryKeyConstraint('x', 'y')
                )
        eq_(t.c.x.primary_key, True)
        eq_(t.c.y.primary_key, True)
        eq_(t.c.z.primary_key, False)

    def test_pk_col_mismatch_one(self):
        m = MetaData()
        assert_raises_message(
            exc.SAWarning,
            "Table 't' specifies columns 'x' as primary_key=True, "
                "not matching locally specified columns 'q'",
            Table, 't', m,
                Column('x', Integer, primary_key=True),
                Column('q', Integer),
                PrimaryKeyConstraint('q')
        )

    def test_pk_col_mismatch_two(self):
        m = MetaData()
        assert_raises_message(
            exc.SAWarning,
            "Table 't' specifies columns 'a', 'b', 'c' as primary_key=True, "
                "not matching locally specified columns 'b', 'c'",
            Table, 't', m,
           Column('a', Integer, primary_key=True),
           Column('b', Integer, primary_key=True),
           Column('c', Integer, primary_key=True),
           PrimaryKeyConstraint('b', 'c')
        )

    @testing.emits_warning("Table 't'")
    def test_pk_col_mismatch_three(self):
        m = MetaData()
        t = Table('t', m,
                Column('x', Integer, primary_key=True),
                Column('q', Integer),
                PrimaryKeyConstraint('q')
        )
        eq_(list(t.primary_key), [t.c.q])

    @testing.emits_warning("Table 't'")
    def test_pk_col_mismatch_four(self):
        m = MetaData()
        t = Table('t', m,
           Column('a', Integer, primary_key=True),
           Column('b', Integer, primary_key=True),
           Column('c', Integer, primary_key=True),
           PrimaryKeyConstraint('b', 'c')
        )
        eq_(list(t.primary_key), [t.c.b, t.c.c])

class SchemaTypeTest(fixtures.TestBase):
    class MyType(sqltypes.SchemaType, sqltypes.TypeEngine):
        column = None
        table = None
        evt_targets = ()

        def _set_table(self, column, table):
            super(SchemaTypeTest.MyType, self)._set_table(column, table)
            self.column = column
            self.table = table

        def _on_table_create(self, target, bind, **kw):
            self.evt_targets += (target,)

    def test_independent_schema(self):
        m = MetaData()
        type_ = self.MyType(schema="q")
        t1 = Table('x', m, Column("y", type_), schema="z")
        eq_(t1.c.y.type.schema, "q")

    def test_inherit_schema(self):
        m = MetaData()
        type_ = self.MyType(schema="q", inherit_schema=True)
        t1 = Table('x', m, Column("y", type_), schema="z")
        eq_(t1.c.y.type.schema, "z")

    def test_independent_schema_enum(self):
        m = MetaData()
        type_ = sqltypes.Enum("a", schema="q")
        t1 = Table('x', m, Column("y", type_), schema="z")
        eq_(t1.c.y.type.schema, "q")

    def test_inherit_schema_enum(self):
        m = MetaData()
        type_ = sqltypes.Enum("a", "b", "c", schema="q", inherit_schema=True)
        t1 = Table('x', m, Column("y", type_), schema="z")
        eq_(t1.c.y.type.schema, "z")

    def test_tometadata_copy_type(self):
        m1 = MetaData()

        type_ = self.MyType()
        t1 = Table('x', m1, Column("y", type_))

        m2 = MetaData()
        t2 = t1.tometadata(m2)

        # metadata isn't set
        is_(t2.c.y.type.metadata, None)

        # our test type sets table, though
        is_(t2.c.y.type.table, t2)

    def test_tometadata_independent_schema(self):
        m1 = MetaData()

        type_ = self.MyType()
        t1 = Table('x', m1, Column("y", type_))

        m2 = MetaData()
        t2 = t1.tometadata(m2, schema="bar")

        eq_(t2.c.y.type.schema, None)

    def test_tometadata_inherit_schema(self):
        m1 = MetaData()

        type_ = self.MyType(inherit_schema=True)
        t1 = Table('x', m1, Column("y", type_))

        m2 = MetaData()
        t2 = t1.tometadata(m2, schema="bar")

        eq_(t1.c.y.type.schema, None)
        eq_(t2.c.y.type.schema, "bar")

    def test_tometadata_independent_events(self):
        m1 = MetaData()

        type_ = self.MyType()
        t1 = Table('x', m1, Column("y", type_))

        m2 = MetaData()
        t2 = t1.tometadata(m2)

        t1.dispatch.before_create(t1, testing.db)
        eq_(t1.c.y.type.evt_targets, (t1,))
        eq_(t2.c.y.type.evt_targets, ())

        t2.dispatch.before_create(t2, testing.db)
        t2.dispatch.before_create(t2, testing.db)
        eq_(t1.c.y.type.evt_targets, (t1,))
        eq_(t2.c.y.type.evt_targets, (t2, t2))



class SchemaTest(fixtures.TestBase, AssertsCompiledSQL):

    def test_default_schema_metadata_fk(self):
        m = MetaData(schema="foo")
        t1 = Table('t1', m, Column('x', Integer))
        t2 = Table('t2', m, Column('x', Integer, ForeignKey('t1.x')))
        assert t2.c.x.references(t1.c.x)

    def test_ad_hoc_schema_equiv_fk(self):
        m = MetaData()
        t1 = Table('t1', m, Column('x', Integer), schema="foo")
        t2 = Table('t2', m, Column('x', Integer, ForeignKey('t1.x')), schema="foo")
        assert_raises(
            exc.NoReferencedTableError,
            lambda: t2.c.x.references(t1.c.x)
        )

    def test_default_schema_metadata_fk_alt_remote(self):
        m = MetaData(schema="foo")
        t1 = Table('t1', m, Column('x', Integer))
        t2 = Table('t2', m, Column('x', Integer, ForeignKey('t1.x')),
                                schema="bar")
        assert t2.c.x.references(t1.c.x)

    def test_default_schema_metadata_fk_alt_local_raises(self):
        m = MetaData(schema="foo")
        t1 = Table('t1', m, Column('x', Integer), schema="bar")
        t2 = Table('t2', m, Column('x', Integer, ForeignKey('t1.x')))
        assert_raises(
            exc.NoReferencedTableError,
            lambda: t2.c.x.references(t1.c.x)
        )

    def test_default_schema_metadata_fk_alt_local(self):
        m = MetaData(schema="foo")
        t1 = Table('t1', m, Column('x', Integer), schema="bar")
        t2 = Table('t2', m, Column('x', Integer, ForeignKey('bar.t1.x')))
        assert t2.c.x.references(t1.c.x)

    def test_create_drop_schema(self):

        self.assert_compile(
            schema.CreateSchema("sa_schema"),
            "CREATE SCHEMA sa_schema"
        )
        self.assert_compile(
            schema.DropSchema("sa_schema"),
            "DROP SCHEMA sa_schema"
        )
        self.assert_compile(
            schema.DropSchema("sa_schema", cascade=True),
            "DROP SCHEMA sa_schema CASCADE"
        )

    def test_iteration(self):
        metadata = MetaData()
        table1 = Table('table1', metadata, Column('col1', Integer,
                       primary_key=True), schema='someschema')
        table2 = Table('table2', metadata, Column('col1', Integer,
                       primary_key=True), Column('col2', Integer,
                       ForeignKey('someschema.table1.col1')),
                       schema='someschema')

        t1 = str(schema.CreateTable(table1).compile(bind=testing.db))
        t2 = str(schema.CreateTable(table2).compile(bind=testing.db))
        if testing.db.dialect.preparer(testing.db.dialect).omit_schema:
            assert t1.index("CREATE TABLE table1") > -1
            assert t2.index("CREATE TABLE table2") > -1
        else:
            assert t1.index("CREATE TABLE someschema.table1") > -1
            assert t2.index("CREATE TABLE someschema.table2") > -1


class UseExistingTest(fixtures.TablesTest):
    @classmethod
    def define_tables(cls, metadata):
        Table('users', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('name', String(30)))

    def _useexisting_fixture(self):
        meta2 = MetaData(testing.db)
        Table('users', meta2, autoload=True)
        return meta2

    def _notexisting_fixture(self):
        return MetaData(testing.db)

    def test_exception_no_flags(self):
        meta2 = self._useexisting_fixture()
        def go():
            Table('users', meta2, Column('name',
                          Unicode), autoload=True)
        assert_raises_message(
            exc.InvalidRequestError,
                "Table 'users' is already defined for this "\
                "MetaData instance.",
            go
        )

    @testing.uses_deprecated
    def test_deprecated_useexisting(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      autoload=True, useexisting=True)
        assert isinstance(users.c.name.type, Unicode)
        assert not users.quote
        users = Table('users', meta2, quote=True, autoload=True,
                      useexisting=True)
        assert users.quote

    def test_keep_plus_existing_raises(self):
        meta2 = self._useexisting_fixture()
        assert_raises(
            exc.ArgumentError,
            Table, 'users', meta2, keep_existing=True,
                extend_existing=True
        )

    @testing.uses_deprecated
    def test_existing_plus_useexisting_raises(self):
        meta2 = self._useexisting_fixture()
        assert_raises(
            exc.ArgumentError,
            Table, 'users', meta2, useexisting=True,
                extend_existing=True
        )

    def test_keep_existing_no_dupe_constraints(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2,
            Column('id', Integer),
            Column('name', Unicode),
            UniqueConstraint('name'),
            keep_existing=True
        )
        assert 'name' in users.c
        assert 'id' in users.c
        eq_(len(users.constraints), 2)

        u2 = Table('users', meta2,
            Column('id', Integer),
            Column('name', Unicode),
            UniqueConstraint('name'),
            keep_existing=True
        )
        eq_(len(u2.constraints), 2)

    def test_extend_existing_dupes_constraints(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2,
            Column('id', Integer),
            Column('name', Unicode),
            UniqueConstraint('name'),
            extend_existing=True
        )
        assert 'name' in users.c
        assert 'id' in users.c
        eq_(len(users.constraints), 2)

        u2 = Table('users', meta2,
            Column('id', Integer),
            Column('name', Unicode),
            UniqueConstraint('name'),
            extend_existing=True
        )
        # constraint got duped
        eq_(len(u2.constraints), 3)

    def test_keep_existing_coltype(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      autoload=True, keep_existing=True)
        assert not isinstance(users.c.name.type, Unicode)

    def test_keep_existing_quote(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, quote=True, autoload=True,
                      keep_existing=True)
        assert not users.name.quote

    def test_keep_existing_add_column(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2,
                        Column('foo', Integer),
                        autoload=True,
                      keep_existing=True)
        assert "foo" not in users.c

    def test_keep_existing_coltype_no_orig(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      autoload=True, keep_existing=True)
        assert isinstance(users.c.name.type, Unicode)

    @testing.skip_if(
            lambda: testing.db.dialect.requires_name_normalize,
            "test depends on lowercase as case insensitive")
    def test_keep_existing_quote_no_orig(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2, quote=True,
                        autoload=True,
                      keep_existing=True)
        assert users.name.quote

    def test_keep_existing_add_column_no_orig(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2,
                        Column('foo', Integer),
                        autoload=True,
                      keep_existing=True)
        assert "foo" in users.c

    def test_keep_existing_coltype_no_reflection(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      keep_existing=True)
        assert not isinstance(users.c.name.type, Unicode)

    def test_keep_existing_quote_no_reflection(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, quote=True,
                      keep_existing=True)
        assert not users.name.quote

    def test_keep_existing_add_column_no_reflection(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2,
                        Column('foo', Integer),
                      keep_existing=True)
        assert "foo" not in users.c

    def test_extend_existing_coltype(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      autoload=True, extend_existing=True)
        assert isinstance(users.c.name.type, Unicode)

    def test_extend_existing_quote(self):
        meta2 = self._useexisting_fixture()
        assert_raises_message(
            tsa.exc.ArgumentError,
            "Can't redefine 'quote' or 'quote_schema' arguments",
            Table, 'users', meta2, quote=True, autoload=True,
                      extend_existing=True
        )

    def test_extend_existing_add_column(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2,
                        Column('foo', Integer),
                        autoload=True,
                      extend_existing=True)
        assert "foo" in users.c

    def test_extend_existing_coltype_no_orig(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      autoload=True, extend_existing=True)
        assert isinstance(users.c.name.type, Unicode)

    @testing.skip_if(
            lambda: testing.db.dialect.requires_name_normalize,
            "test depends on lowercase as case insensitive")
    def test_extend_existing_quote_no_orig(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2, quote=True,
                        autoload=True,
                      extend_existing=True)
        assert users.name.quote

    def test_extend_existing_add_column_no_orig(self):
        meta2 = self._notexisting_fixture()
        users = Table('users', meta2,
                        Column('foo', Integer),
                        autoload=True,
                      extend_existing=True)
        assert "foo" in users.c

    def test_extend_existing_coltype_no_reflection(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2, Column('name', Unicode),
                      extend_existing=True)
        assert isinstance(users.c.name.type, Unicode)

    def test_extend_existing_quote_no_reflection(self):
        meta2 = self._useexisting_fixture()
        assert_raises_message(
            tsa.exc.ArgumentError,
            "Can't redefine 'quote' or 'quote_schema' arguments",
            Table, 'users', meta2, quote=True,
                      extend_existing=True
        )

    def test_extend_existing_add_column_no_reflection(self):
        meta2 = self._useexisting_fixture()
        users = Table('users', meta2,
                        Column('foo', Integer),
                      extend_existing=True)
        assert "foo" in users.c

class ConstraintTest(fixtures.TestBase):
    def _single_fixture(self):
        m = MetaData()

        t1 = Table('t1', m,
            Column('a', Integer),
            Column('b', Integer)
        )

        t2 = Table('t2', m,
            Column('a', Integer, ForeignKey('t1.a'))
        )

        t3 = Table('t3', m,
            Column('a', Integer)
        )
        return t1, t2, t3

    def test_table_references(self):
        t1, t2, t3 = self._single_fixture()
        assert list(t2.c.a.foreign_keys)[0].references(t1)
        assert not list(t2.c.a.foreign_keys)[0].references(t3)

    def test_column_references(self):
        t1, t2, t3 = self._single_fixture()
        assert t2.c.a.references(t1.c.a)
        assert not t2.c.a.references(t3.c.a)
        assert not t2.c.a.references(t1.c.b)

    def test_column_references_derived(self):
        t1, t2, t3 = self._single_fixture()
        s1 = tsa.select([tsa.select([t1]).alias()])
        assert t2.c.a.references(s1.c.a)
        assert not t2.c.a.references(s1.c.b)

    def test_copy_doesnt_reference(self):
        t1, t2, t3 = self._single_fixture()
        a2 = t2.c.a.copy()
        assert not a2.references(t1.c.a)
        assert not a2.references(t1.c.b)

    def test_derived_column_references(self):
        t1, t2, t3 = self._single_fixture()
        s1 = tsa.select([tsa.select([t2]).alias()])
        assert s1.c.a.references(t1.c.a)
        assert not s1.c.a.references(t1.c.b)

    def test_related_column_not_present_atfirst_ok(self):
        m = MetaData()
        base_table = Table("base", m,
            Column("id", Integer, primary_key=True)
        )
        fk = ForeignKey('base.q')
        derived_table = Table("derived", m,
            Column("id", None, fk,
                primary_key=True),
        )

        base_table.append_column(Column('q', Integer))
        assert fk.column is base_table.c.q
        assert isinstance(derived_table.c.id.type, Integer)

    def test_invalid_composite_fk_check_strings(self):
        m = MetaData()

        assert_raises_message(
            exc.ArgumentError,
            r"ForeignKeyConstraint on t1\(x, y\) refers to "
                "multiple remote tables: t2 and t3",
            Table,
            't1', m, Column('x', Integer), Column('y', Integer),
            ForeignKeyConstraint(['x', 'y'], ['t2.x', 't3.y'])
        )

    def test_invalid_composite_fk_check_columns(self):
        m = MetaData()

        t2 = Table('t2', m, Column('x', Integer))
        t3 = Table('t3', m, Column('y', Integer))

        assert_raises_message(
            exc.ArgumentError,
            r"ForeignKeyConstraint on t1\(x, y\) refers to "
                "multiple remote tables: t2 and t3",
            Table,
            't1', m, Column('x', Integer), Column('y', Integer),
            ForeignKeyConstraint(['x', 'y'], [t2.c.x, t3.c.y])
        )

    def test_invalid_composite_fk_check_columns_notattached(self):
        m = MetaData()
        x = Column('x', Integer)
        y = Column('y', Integer)

        # no error is raised for this one right now.
        # which is a minor bug.
        Table('t1', m, Column('x', Integer), Column('y', Integer),
                ForeignKeyConstraint(['x', 'y'], [x, y])
            )

        t2 = Table('t2', m, x)
        t3 = Table('t3', m, y)

    def test_constraint_copied_to_proxy_ok(self):
        m = MetaData()
        t1 = Table('t1', m, Column('id', Integer, primary_key=True))
        t2 = Table('t2', m, Column('id', Integer, ForeignKey('t1.id'),
                        primary_key=True))

        s = tsa.select([t2])
        t2fk = list(t2.c.id.foreign_keys)[0]
        sfk = list(s.c.id.foreign_keys)[0]

        # the two FKs share the ForeignKeyConstraint
        is_(
            t2fk.constraint,
            sfk.constraint
        )

        # but the ForeignKeyConstraint isn't
        # aware of the select's FK
        eq_(
            t2fk.constraint.elements,
            [t2fk]
        )

    def test_type_propagate_composite_fk_string(self):
        metadata = MetaData()
        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True),
                  Column('key2', String(40), primary_key=True))

        b = Table('b', metadata,
                  Column('a_key1', None),
                  Column('a_key2', None),
                  Column('id', Integer, primary_key=True),
                  ForeignKeyConstraint(['a_key1', 'a_key2'],
                                       ['a.key1', 'a.key2'])
                  )

        assert isinstance(b.c.a_key1.type, Integer)
        assert isinstance(b.c.a_key2.type, String)

    def test_type_propagate_composite_fk_col(self):
        metadata = MetaData()
        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True),
                  Column('key2', String(40), primary_key=True))

        b = Table('b', metadata,
                  Column('a_key1', None),
                  Column('a_key2', None),
                  Column('id', Integer, primary_key=True),
                  ForeignKeyConstraint(['a_key1', 'a_key2'],
                                       [a.c.key1, a.c.key2])
                  )

        assert isinstance(b.c.a_key1.type, Integer)
        assert isinstance(b.c.a_key2.type, String)

    def test_type_propagate_standalone_fk_string(self):
        metadata = MetaData()
        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True))

        b = Table('b', metadata,
                  Column('a_key1', None, ForeignKey("a.key1")),
                  )

        assert isinstance(b.c.a_key1.type, Integer)

    def test_type_propagate_standalone_fk_col(self):
        metadata = MetaData()
        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True))

        b = Table('b', metadata,
                  Column('a_key1', None, ForeignKey(a.c.key1)),
                  )

        assert isinstance(b.c.a_key1.type, Integer)

    def test_type_propagate_chained_string_source_first(self):
        metadata = MetaData()
        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True))

        b = Table('b', metadata,
                  Column('a_key1', None, ForeignKey("a.key1")),
                  )

        c = Table('c', metadata,
                  Column('b_key1', None, ForeignKey("b.a_key1")),
                  )

        assert isinstance(b.c.a_key1.type, Integer)
        assert isinstance(c.c.b_key1.type, Integer)

    def test_type_propagate_chained_string_source_last(self):
        metadata = MetaData()

        b = Table('b', metadata,
                  Column('a_key1', None, ForeignKey("a.key1")),
                  )

        c = Table('c', metadata,
                  Column('b_key1', None, ForeignKey("b.a_key1")),
                  )

        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True))

        assert isinstance(b.c.a_key1.type, Integer)
        assert isinstance(c.c.b_key1.type, Integer)

    def test_type_propagate_chained_col_orig_first(self):
        metadata = MetaData()
        a = Table('a', metadata,
                  Column('key1', Integer, primary_key=True))

        b = Table('b', metadata,
                  Column('a_key1', None, ForeignKey(a.c.key1)),
                  )

        c = Table('c', metadata,
                  Column('b_key1', None, ForeignKey(b.c.a_key1)),
                  )

        assert isinstance(b.c.a_key1.type, Integer)
        assert isinstance(c.c.b_key1.type, Integer)

    def test_column_accessor_col(self):
        c1 = Column('x', Integer)
        fk = ForeignKey(c1)
        is_(fk.column, c1)

    def test_column_accessor_clause_element(self):
        c1 = Column('x', Integer)

        class CThing(object):
            def __init__(self, c):
                self.c = c
            def __clause_element__(self):
                return self.c

        fk = ForeignKey(CThing(c1))
        is_(fk.column, c1)

    def test_column_accessor_string_no_parent(self):
        fk = ForeignKey("sometable.somecol")
        assert_raises_message(
            exc.InvalidRequestError,
            "this ForeignKey object does not yet have a parent "
            "Column associated with it.",
            getattr, fk, "column"
        )

    def test_column_accessor_string_no_parent_table(self):
        fk = ForeignKey("sometable.somecol")
        c1 = Column('x', fk)
        assert_raises_message(
            exc.InvalidRequestError,
            "this ForeignKey's parent column is not yet "
            "associated with a Table.",
            getattr, fk, "column"
        )

    def test_column_accessor_string_no_target_table(self):
        fk = ForeignKey("sometable.somecol")
        c1 = Column('x', fk)
        t1 = Table('t', MetaData(), c1)
        assert_raises_message(
            exc.NoReferencedTableError,
            "Foreign key associated with column 't.x' could not find "
            "table 'sometable' with which to generate a "
            "foreign key to target column 'somecol'",
            getattr, fk, "column"
        )

    def test_column_accessor_string_no_target_column(self):
        fk = ForeignKey("sometable.somecol")
        c1 = Column('x', fk)
        m = MetaData()
        t1 = Table('t', m, c1)
        t2 = Table("sometable", m, Column('notsomecol', Integer))
        assert_raises_message(
            exc.NoReferencedColumnError,
            "Could not initialize target column for ForeignKey "
            "'sometable.somecol' on table 't': "
            "table 'sometable' has no column named 'somecol'",
            getattr, fk, "column"
        )

    def test_remove_table_fk_bookkeeping(self):
        metadata = MetaData()
        fk = ForeignKey('t1.x')
        t2 = Table('t2', metadata, Column('y', Integer, fk))
        t3 = Table('t3', metadata, Column('y', Integer, ForeignKey('t1.x')))

        assert t2.key in metadata.tables
        assert ("t1", "x") in metadata._fk_memos

        metadata.remove(t2)

        # key is removed
        assert t2.key not in metadata.tables

        # the memo for the FK is still there
        assert ("t1", "x") in metadata._fk_memos

        # fk is not in the collection
        assert fk not in metadata._fk_memos[("t1", "x")]

        # make the referenced table
        t1 = Table('t1', metadata, Column('x', Integer))

        # t2 tells us exactly what's wrong
        assert_raises_message(
            exc.InvalidRequestError,
            "Table t2 is no longer associated with its parent MetaData",
            getattr, fk, "column"
        )

        # t3 is unaffected
        assert t3.c.y.references(t1.c.x)

        # remove twice OK
        metadata.remove(t2)


class ColumnDefinitionTest(AssertsCompiledSQL, fixtures.TestBase):
    """Test Column() construction."""

    __dialect__ = 'default'

    def columns(self):
        return [Column(Integer),
                 Column('b', Integer),
                 Column(Integer),
                 Column('d', Integer),
                 Column(Integer, name='e'),
                 Column(type_=Integer),
                 Column(Integer()),
                 Column('h', Integer()),
                 Column(type_=Integer())]

    def test_basic(self):
        c = self.columns()

        for i, v in ((0, 'a'), (2, 'c'), (5, 'f'), (6, 'g'), (8, 'i')):
            c[i].name = v
            c[i].key = v
        del i, v

        tbl = Table('table', MetaData(), *c)

        for i, col in enumerate(tbl.c):
            assert col.name == c[i].name

    def test_name_none(self):

        c = Column(Integer)
        assert_raises_message(
            exc.ArgumentError,
            "Column must be constructed with a non-blank name or assign a "
            "non-blank .name ",
            Table, 't', MetaData(), c)

    def test_name_blank(self):

        c = Column('', Integer)
        assert_raises_message(
            exc.ArgumentError,
            "Column must be constructed with a non-blank name or assign a "
            "non-blank .name ",
            Table, 't', MetaData(), c)

    def test_dupe_column(self):
        c = Column('x', Integer)
        Table('t', MetaData(), c)

        assert_raises_message(
            exc.ArgumentError,
            "Column object already assigned to Table 't'",
            Table, 'q', MetaData(), c)

    def test_incomplete_key(self):
        c = Column(Integer)
        assert c.name is None
        assert c.key is None

        c.name = 'named'
        Table('t', MetaData(), c)

        assert c.name == 'named'
        assert c.name == c.key

    def test_unique_index_flags_default_to_none(self):
        c = Column(Integer)
        eq_(c.unique, None)
        eq_(c.index, None)

        c = Column('c', Integer, index=True)
        eq_(c.unique, None)
        eq_(c.index, True)

        t = Table('t', MetaData(), c)
        eq_(list(t.indexes)[0].unique, False)

        c = Column(Integer, unique=True)
        eq_(c.unique, True)
        eq_(c.index, None)

        c = Column('c', Integer, index=True, unique=True)
        eq_(c.unique, True)
        eq_(c.index, True)

        t = Table('t', MetaData(), c)
        eq_(list(t.indexes)[0].unique, True)

    def test_bogus(self):
        assert_raises(exc.ArgumentError, Column, 'foo', name='bar')
        assert_raises(exc.ArgumentError, Column, 'foo', Integer,
                          type_=Integer())

    def test_custom_subclass_proxy(self):
        """test proxy generation of a Column subclass, can be compiled."""

        from sqlalchemy.schema import Column
        from sqlalchemy.ext.compiler import compiles
        from sqlalchemy.sql import select

        class MyColumn(Column):
            def _constructor(self, name, type, **kw):
                kw['name'] = name
                return MyColumn(type, **kw)

            def __init__(self, type, **kw):
                Column.__init__(self, type, **kw)

            def my_goofy_thing(self):
                return "hi"

        @compiles(MyColumn)
        def goofy(element, compiler, **kw):
            s = compiler.visit_column(element, **kw)
            return s + "-"

        id = MyColumn(Integer, primary_key=True)
        id.name = 'id'
        name = MyColumn(String)
        name.name = 'name'
        t1 = Table('foo', MetaData(),
            id,
            name
        )

        # goofy thing
        eq_(t1.c.name.my_goofy_thing(), "hi")

        # create proxy
        s = select([t1.select().alias()])

        # proxy has goofy thing
        eq_(s.c.name.my_goofy_thing(), "hi")

        # compile works
        self.assert_compile(
            select([t1.select().alias()]),
            "SELECT anon_1.id-, anon_1.name- FROM "
            "(SELECT foo.id- AS id, foo.name- AS name "
            "FROM foo) AS anon_1",
        )

    def test_custom_subclass_proxy_typeerror(self):
        from sqlalchemy.schema import Column
        from sqlalchemy.sql import select

        class MyColumn(Column):
            def __init__(self, type, **kw):
                Column.__init__(self, type, **kw)

        id = MyColumn(Integer, primary_key=True)
        id.name = 'id'
        name = MyColumn(String)
        name.name = 'name'
        t1 = Table('foo', MetaData(),
            id,
            name
        )
        assert_raises_message(
            TypeError,
            "Could not create a copy of this <class "
            "'test.sql.test_metadata..*MyColumn'> "
            "object.  Ensure the class includes a _constructor()",
            getattr, select([t1.select().alias()]), 'c'
        )

    def test_custom_create(self):
        from sqlalchemy.ext.compiler import compiles, deregister

        @compiles(schema.CreateColumn)
        def compile(element, compiler, **kw):
            column = element.element

            if "special" not in column.info:
                return compiler.visit_create_column(element, **kw)

            text = "%s SPECIAL DIRECTIVE %s" % (
                    column.name,
                    compiler.type_compiler.process(column.type)
                )
            default = compiler.get_column_default_string(column)
            if default is not None:
                text += " DEFAULT " + default

            if not column.nullable:
                text += " NOT NULL"

            if column.constraints:
                text += " ".join(
                            compiler.process(const)
                            for const in column.constraints)
            return text

        t = Table('mytable', MetaData(),
                Column('x', Integer, info={"special": True}, primary_key=True),
                Column('y', String(50)),
                Column('z', String(20), info={"special": True})
            )

        self.assert_compile(
            schema.CreateTable(t),
            "CREATE TABLE mytable (x SPECIAL DIRECTIVE INTEGER "
                "NOT NULL, y VARCHAR(50), "
                "z SPECIAL DIRECTIVE VARCHAR(20), PRIMARY KEY (x))"
        )

        deregister(schema.CreateColumn)

class ColumnDefaultsTest(fixtures.TestBase):
    """test assignment of default fixures to columns"""

    def _fixture(self, *arg, **kw):
        return Column('x', Integer, *arg, **kw)

    def test_server_default_positional(self):
        target = schema.DefaultClause('y')
        c = self._fixture(target)
        assert c.server_default is target
        assert target.column is c

    def test_onupdate_default_not_server_default_one(self):
        target1 = schema.DefaultClause('y')
        target2 = schema.DefaultClause('z')

        c = self._fixture(server_default=target1, server_onupdate=target2)
        eq_(c.server_default.arg, 'y')
        eq_(c.server_onupdate.arg, 'z')

    def test_onupdate_default_not_server_default_two(self):
        target1 = schema.DefaultClause('y', for_update=True)
        target2 = schema.DefaultClause('z', for_update=True)

        c = self._fixture(server_default=target1, server_onupdate=target2)
        eq_(c.server_default.arg, 'y')
        eq_(c.server_onupdate.arg, 'z')

    def test_onupdate_default_not_server_default_three(self):
        target1 = schema.DefaultClause('y', for_update=False)
        target2 = schema.DefaultClause('z', for_update=True)

        c = self._fixture(target1, target2)
        eq_(c.server_default.arg, 'y')
        eq_(c.server_onupdate.arg, 'z')

    def test_onupdate_default_not_server_default_four(self):
        target1 = schema.DefaultClause('y', for_update=False)

        c = self._fixture(server_onupdate=target1)
        is_(c.server_default, None)
        eq_(c.server_onupdate.arg, 'y')

    def test_server_default_keyword_as_schemaitem(self):
        target = schema.DefaultClause('y')
        c = self._fixture(server_default=target)
        assert c.server_default is target
        assert target.column is c

    def test_server_default_keyword_as_clause(self):
        target = 'y'
        c = self._fixture(server_default=target)
        assert c.server_default.arg == target
        assert c.server_default.column is c

    def test_server_default_onupdate_positional(self):
        target = schema.DefaultClause('y', for_update=True)
        c = self._fixture(target)
        assert c.server_onupdate is target
        assert target.column is c

    def test_server_default_onupdate_keyword_as_schemaitem(self):
        target = schema.DefaultClause('y', for_update=True)
        c = self._fixture(server_onupdate=target)
        assert c.server_onupdate is target
        assert target.column is c

    def test_server_default_onupdate_keyword_as_clause(self):
        target = 'y'
        c = self._fixture(server_onupdate=target)
        assert c.server_onupdate.arg == target
        assert c.server_onupdate.column is c

    def test_column_default_positional(self):
        target = schema.ColumnDefault('y')
        c = self._fixture(target)
        assert c.default is target
        assert target.column is c

    def test_column_default_keyword_as_schemaitem(self):
        target = schema.ColumnDefault('y')
        c = self._fixture(default=target)
        assert c.default is target
        assert target.column is c

    def test_column_default_keyword_as_clause(self):
        target = 'y'
        c = self._fixture(default=target)
        assert c.default.arg == target
        assert c.default.column is c

    def test_column_default_onupdate_positional(self):
        target = schema.ColumnDefault('y', for_update=True)
        c = self._fixture(target)
        assert c.onupdate is target
        assert target.column is c

    def test_column_default_onupdate_keyword_as_schemaitem(self):
        target = schema.ColumnDefault('y', for_update=True)
        c = self._fixture(onupdate=target)
        assert c.onupdate is target
        assert target.column is c

    def test_column_default_onupdate_keyword_as_clause(self):
        target = 'y'
        c = self._fixture(onupdate=target)
        assert c.onupdate.arg == target
        assert c.onupdate.column is c

class ColumnOptionsTest(fixtures.TestBase):

    def test_default_generators(self):
        g1, g2 = Sequence('foo_id_seq'), ColumnDefault('f5')
        assert Column(String, default=g1).default is g1
        assert Column(String, onupdate=g1).onupdate is g1
        assert Column(String, default=g2).default is g2
        assert Column(String, onupdate=g2).onupdate is g2

    def _null_type_error(self, col):
        t = Table('t', MetaData(), col)
        assert_raises_message(
            exc.CompileError,
            r"\(in table 't', column 'foo'\): Can't generate DDL for NullType",
            schema.CreateTable(t).compile
        )

    def _no_name_error(self, col):
        assert_raises_message(
            exc.ArgumentError,
            "Column must be constructed with a non-blank name or "
            "assign a non-blank .name",
            Table, 't', MetaData(), col
        )

    def _no_error(self, col):
        m = MetaData()
        b = Table('bar', m, Column('id', Integer))
        t = Table('t', m, col)
        schema.CreateTable(t).compile()

    def test_argument_signatures(self):
        self._no_name_error(Column())
        self._null_type_error(Column("foo"))
        self._no_name_error(Column(default="foo"))

        self._no_name_error(Column(Sequence("a")))
        self._null_type_error(Column("foo", default="foo"))

        self._null_type_error(Column("foo", Sequence("a")))

        self._no_name_error(Column(ForeignKey('bar.id')))

        self._no_error(Column("foo", ForeignKey('bar.id')))

        self._no_name_error(Column(ForeignKey('bar.id'), default="foo"))

        self._no_name_error(Column(ForeignKey('bar.id'), Sequence("a")))
        self._no_error(Column("foo", ForeignKey('bar.id'), default="foo"))
        self._no_error(Column("foo", ForeignKey('bar.id'), Sequence("a")))


    def test_column_info(self):

        c1 = Column('foo', String, info={'x': 'y'})
        c2 = Column('bar', String, info={})
        c3 = Column('bat', String)
        assert c1.info == {'x': 'y'}
        assert c2.info == {}
        assert c3.info == {}

        for c in (c1, c2, c3):
            c.info['bar'] = 'zip'
            assert c.info['bar'] == 'zip'

class CatchAllEventsTest(fixtures.TestBase):

    def teardown(self):
        events.SchemaEventTarget.dispatch._clear()

    def test_all_events(self):
        canary = []
        def before_attach(obj, parent):
            canary.append("%s->%s" % (obj.__class__.__name__,
                                parent.__class__.__name__))

        def after_attach(obj, parent):
            canary.append("%s->%s" % (obj.__class__.__name__, parent))

        event.listen(schema.SchemaItem, "before_parent_attach", before_attach)
        event.listen(schema.SchemaItem, "after_parent_attach", after_attach)

        m = MetaData()
        Table('t1', m,
            Column('id', Integer, Sequence('foo_id'), primary_key=True),
            Column('bar', String, ForeignKey('t2.id'))
        )
        Table('t2', m,
            Column('id', Integer, primary_key=True),
        )

        eq_(
            canary,
            ['Sequence->Column', 'Sequence->id', 'ForeignKey->Column',
             'ForeignKey->bar', 'Table->MetaData',
             'PrimaryKeyConstraint->Table', 'PrimaryKeyConstraint->t1',
             'Column->Table', 'Column->t1', 'Column->Table',
             'Column->t1', 'ForeignKeyConstraint->Table',
             'ForeignKeyConstraint->t1', 'Table->MetaData(bind=None)',
             'Table->MetaData', 'PrimaryKeyConstraint->Table',
             'PrimaryKeyConstraint->t2', 'Column->Table', 'Column->t2',
             'Table->MetaData(bind=None)']
        )

    def test_events_per_constraint(self):
        canary = []

        def evt(target):
            def before_attach(obj, parent):
                canary.append("%s->%s" % (target.__name__,
                                        parent.__class__.__name__))

            def after_attach(obj, parent):
                assert hasattr(obj, 'name')  # so we can change it
                canary.append("%s->%s" % (target.__name__, parent))
            event.listen(target, "before_parent_attach", before_attach)
            event.listen(target, "after_parent_attach", after_attach)

        for target in [
            schema.ForeignKeyConstraint, schema.PrimaryKeyConstraint,
            schema.UniqueConstraint,
            schema.CheckConstraint,
            schema.Index
        ]:
            evt(target)

        m = MetaData()
        Table('t1', m,
            Column('id', Integer, Sequence('foo_id'), primary_key=True),
            Column('bar', String, ForeignKey('t2.id'), index=True),
            Column('bat', Integer, unique=True),
        )
        Table('t2', m,
            Column('id', Integer, primary_key=True),
            Column('bar', Integer),
            Column('bat', Integer),
            CheckConstraint("bar>5"),
            UniqueConstraint('bar', 'bat'),
            Index(None, 'bar', 'bat')
        )
        eq_(
            canary,
            [
                'PrimaryKeyConstraint->Table', 'PrimaryKeyConstraint->t1',
                'Index->Table', 'Index->t1',
                'ForeignKeyConstraint->Table', 'ForeignKeyConstraint->t1',
                'UniqueConstraint->Table', 'UniqueConstraint->t1',
                'PrimaryKeyConstraint->Table', 'PrimaryKeyConstraint->t2',
                'CheckConstraint->Table', 'CheckConstraint->t2',
                'UniqueConstraint->Table', 'UniqueConstraint->t2',
                'Index->Table', 'Index->t2'
            ]
        )

class DialectKWArgTest(fixtures.TestBase):
    @contextmanager
    def _fixture(self):
        from sqlalchemy.engine.default import DefaultDialect
        class ParticipatingDialect(DefaultDialect):
            construct_arguments = [
                (schema.Index, {
                    "x": 5,
                    "y": False,
                    "z_one": None
                }),
                (schema.ForeignKeyConstraint, {
                    "foobar": False
                })
            ]

        class ParticipatingDialect2(DefaultDialect):
            construct_arguments = [
                (schema.Index, {
                    "x": 9,
                    "y": True,
                    "pp": "default"
                }),
                (schema.Table, {
                    "*": None
                })
            ]

        class NonParticipatingDialect(DefaultDialect):
            construct_arguments = None

        def load(dialect_name):
            if dialect_name == "participating":
                return ParticipatingDialect
            elif dialect_name == "participating2":
                return ParticipatingDialect2
            elif dialect_name == "nonparticipating":
                return NonParticipatingDialect
            else:
                raise exc.NoSuchModuleError("no dialect %r" % dialect_name)
        with mock.patch("sqlalchemy.dialects.registry.load", load):
            yield

    def test_participating(self):
        with self._fixture():
            idx = Index('a', 'b', 'c', participating_y=True)
            eq_(
                idx.dialect_options,
                {"participating": {"x": 5, "y": True, "z_one": None}}
            )
            eq_(
                idx.dialect_kwargs,
                {
                    'participating_y': True,
                }
            )

    def test_nonparticipating(self):
        with self._fixture():
            idx = Index('a', 'b', 'c', nonparticipating_y=True, nonparticipating_q=5)
            eq_(
                idx.dialect_kwargs,
                {
                    'nonparticipating_y': True,
                    'nonparticipating_q': 5
                }
            )

    def test_unknown_dialect_warning(self):
        with self._fixture():
            assert_raises_message(
                exc.SAWarning,
                "Can't validate argument 'unknown_y'; can't locate "
                "any SQLAlchemy dialect named 'unknown'",
                Index, 'a', 'b', 'c', unknown_y=True
            )

    def test_participating_bad_kw(self):
        with self._fixture():
            assert_raises_message(
                exc.ArgumentError,
                "Argument 'participating_q_p_x' is not accepted by dialect "
                "'participating' on behalf of "
                "<class 'sqlalchemy.sql.schema.Index'>",
                Index, 'a', 'b', 'c', participating_q_p_x=8
            )

    def test_participating_unknown_schema_item(self):
        with self._fixture():
            # the dialect doesn't include UniqueConstraint in
            # its registry at all.
            assert_raises_message(
                exc.ArgumentError,
                "Argument 'participating_q_p_x' is not accepted by dialect "
                "'participating' on behalf of "
                "<class 'sqlalchemy.sql.schema.UniqueConstraint'>",
                UniqueConstraint, 'a', 'b', participating_q_p_x=8
            )

    @testing.emits_warning("Can't validate")
    def test_unknown_dialect_warning_still_populates(self):
        with self._fixture():
            idx = Index('a', 'b', 'c', unknown_y=True)
            eq_(idx.dialect_kwargs, {"unknown_y": True})  # still populates

    @testing.emits_warning("Can't validate")
    def test_unknown_dialect_warning_still_populates_multiple(self):
        with self._fixture():
            idx = Index('a', 'b', 'c', unknown_y=True, unknown_z=5,
                                otherunknown_foo='bar', participating_y=8)
            eq_(
                idx.dialect_options,
                {
                    "unknown": {'y': True, 'z': 5, '*': None},
                    "otherunknown": {'foo': 'bar', '*': None},
                    "participating": {'x': 5, 'y': 8, 'z_one': None}
                }
            )
            eq_(idx.dialect_kwargs,
                {'unknown_z': 5, 'participating_y': 8,
                'unknown_y': True,
                'otherunknown_foo': 'bar'}
            )  # still populates

    def test_combined(self):
        with self._fixture():
            idx = Index('a', 'b', 'c', participating_x=7,
                                    nonparticipating_y=True)

            eq_(
                idx.dialect_options,
                {
                    'participating': {'y': False, 'x': 7, 'z_one': None},
                    'nonparticipating': {'y': True, '*': None}
                }
            )
            eq_(
                idx.dialect_kwargs,
                {
                    'participating_x': 7,
                    'nonparticipating_y': True,
                }
            )

    def test_multiple_participating(self):
        with self._fixture():
            idx = Index('a', 'b', 'c',
                        participating_x=7,
                        participating2_x=15,
                        participating2_y="lazy"
                )
            eq_(
                idx.dialect_options,
                {
                    "participating": {'x': 7, 'y': False, 'z_one': None},
                    "participating2": {'x': 15, 'y': 'lazy', 'pp': 'default'},
                }
            )
            eq_(
                idx.dialect_kwargs,
                {
                    'participating_x': 7,
                    'participating2_x': 15,
                    'participating2_y': 'lazy'
                }
            )

    def test_foreign_key_propagate(self):
        with self._fixture():
            m = MetaData()
            fk = ForeignKey('t2.id', participating_foobar=True)
            t = Table('t', m, Column('id', Integer, fk))
            fkc = [c for c in t.constraints if isinstance(c, ForeignKeyConstraint)][0]
            eq_(
                fkc.dialect_kwargs,
                {'participating_foobar': True}
            )

    def test_foreign_key_propagate_exceptions_delayed(self):
        with self._fixture():
            m = MetaData()
            fk = ForeignKey('t2.id', participating_fake=True)
            c1 = Column('id', Integer, fk)
            assert_raises_message(
                exc.ArgumentError,
                "Argument 'participating_fake' is not accepted by "
                "dialect 'participating' on behalf of "
                "<class 'sqlalchemy.sql.schema.ForeignKeyConstraint'>",
                Table, 't', m, c1
            )

    def test_wildcard(self):
        with self._fixture():
            m = MetaData()
            t = Table('x', m, Column('x', Integer),
                    participating2_xyz='foo',
                    participating2_engine='InnoDB',
                )
            eq_(
                t.dialect_kwargs,
                {
                    'participating2_xyz': 'foo',
                    'participating2_engine': 'InnoDB'
                }
            )

    def test_uninit_wildcard(self):
        with self._fixture():
            m = MetaData()
            t = Table('x', m, Column('x', Integer))
            eq_(
                t.dialect_options['participating2'], {'*': None}
            )
            eq_(
                t.dialect_kwargs, {}
            )

    def test_not_contains_wildcard(self):
        with self._fixture():
            m = MetaData()
            t = Table('x', m, Column('x', Integer))
            assert 'foobar' not in t.dialect_options['participating2']

    def test_contains_wildcard(self):
        with self._fixture():
            m = MetaData()
            t = Table('x', m, Column('x', Integer), participating2_foobar=5)
            assert 'foobar' in t.dialect_options['participating2']


    def test_update(self):
        with self._fixture():
            idx = Index('a', 'b', 'c', participating_x=20)
            eq_(idx.dialect_kwargs, {
                        "participating_x": 20,
                    })
            idx._validate_dialect_kwargs({
                        "participating_x": 25,
                        "participating_z_one": "default"})
            eq_(idx.dialect_options, {
                    "participating": {"x": 25, "y": False, "z_one": "default"}
                    })
            eq_(idx.dialect_kwargs, {
                        "participating_x": 25,
                        'participating_z_one': "default"
                    })

            idx._validate_dialect_kwargs({
                        "participating_x": 25,
                        "participating_z_one": "default"})

            eq_(idx.dialect_options, {
                    "participating": {"x": 25, "y": False, "z_one": "default"}
                    })
            eq_(idx.dialect_kwargs, {
                        "participating_x": 25,
                        'participating_z_one': "default"
                    })

            idx._validate_dialect_kwargs({
                        "participating_y": True,
                        'participating2_y': "p2y"})
            eq_(idx.dialect_options, {
                    "participating": {"x": 25, "y": True, "z_one": "default"},
                    "participating2": {"y": "p2y", "pp": "default", "x": 9}
                    })
            eq_(idx.dialect_kwargs, {
                        "participating_x": 25,
                        "participating_y": True,
                        'participating2_y': "p2y",
                        "participating_z_one": "default"})
