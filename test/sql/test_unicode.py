# coding: utf-8
"""verrrrry basic unicode column name testing"""

from sqlalchemy import *
from sqlalchemy.testing import fixtures, engines, eq_
from sqlalchemy import testing
from sqlalchemy.testing.engines import utf8_engine
from sqlalchemy.sql import column
from sqlalchemy.testing.schema import Table, Column
from sqlalchemy.util import u, ue

class UnicodeSchemaTest(fixtures.TestBase):
    __requires__ = ('unicode_ddl',)

    @classmethod
    def setup_class(cls):
        global unicode_bind, metadata, t1, t2, t3

        unicode_bind = utf8_engine()

        metadata = MetaData(unicode_bind)
        t1 = Table(u('unitable1'), metadata,
            Column(u('méil'), Integer, primary_key=True),
            Column(ue('\u6e2c\u8a66'), Integer),
            test_needs_fk=True,
            )
        t2 = Table(u('Unitéble2'), metadata,
            Column(u('méil'), Integer, primary_key=True, key="a"),
            Column(ue('\u6e2c\u8a66'), Integer, ForeignKey(u('unitable1.méil')),
                   key="b"
                   ),
                   test_needs_fk=True,
            )

        # Few DBs support Unicode foreign keys
        if testing.against('sqlite'):
            t3 = Table(ue('\u6e2c\u8a66'), metadata,
                       Column(ue('\u6e2c\u8a66_id'), Integer, primary_key=True,
                              autoincrement=False),
                       Column(ue('unitable1_\u6e2c\u8a66'), Integer,
                              ForeignKey(ue('unitable1.\u6e2c\u8a66'))
                              ),
                       Column(u('Unitéble2_b'), Integer,
                              ForeignKey(u('Unitéble2.b'))
                              ),
                       Column(ue('\u6e2c\u8a66_self'), Integer,
                              ForeignKey(ue('\u6e2c\u8a66.\u6e2c\u8a66_id'))
                              ),
                       test_needs_fk=True,
                       )
        else:
            t3 = Table(ue('\u6e2c\u8a66'), metadata,
                       Column(ue('\u6e2c\u8a66_id'), Integer, primary_key=True,
                              autoincrement=False),
                       Column(ue('unitable1_\u6e2c\u8a66'), Integer),
                       Column(u('Unitéble2_b'), Integer),
                       Column(ue('\u6e2c\u8a66_self'), Integer),
                       test_needs_fk=True,
                       )
        metadata.create_all()

    @engines.close_first
    def teardown(self):
        if metadata.tables:
            t3.delete().execute()
            t2.delete().execute()
            t1.delete().execute()

    @classmethod
    def teardown_class(cls):
        global unicode_bind
        metadata.drop_all()
        del unicode_bind

    def test_insert(self):
        t1.insert().execute({u('méil'):1, ue('\u6e2c\u8a66'):5})
        t2.insert().execute({u('a'):1, u('b'):1})
        t3.insert().execute({ue('\u6e2c\u8a66_id'): 1,
                             ue('unitable1_\u6e2c\u8a66'): 5,
                             u('Unitéble2_b'): 1,
                             ue('\u6e2c\u8a66_self'): 1})

        assert t1.select().execute().fetchall() == [(1, 5)]
        assert t2.select().execute().fetchall() == [(1, 1)]
        assert t3.select().execute().fetchall() == [(1, 5, 1, 1)]

    def test_reflect(self):
        t1.insert().execute({u('méil'):2, ue('\u6e2c\u8a66'):7})
        t2.insert().execute({u('a'):2, u('b'):2})
        t3.insert().execute({ue('\u6e2c\u8a66_id'): 2,
                             ue('unitable1_\u6e2c\u8a66'): 7,
                             u('Unitéble2_b'): 2,
                             ue('\u6e2c\u8a66_self'): 2})

        meta = MetaData(unicode_bind)
        tt1 = Table(t1.name, meta, autoload=True)
        tt2 = Table(t2.name, meta, autoload=True)
        tt3 = Table(t3.name, meta, autoload=True)

        tt1.insert().execute({u('méil'):1, ue('\u6e2c\u8a66'):5})
        tt2.insert().execute({u('méil'):1, ue('\u6e2c\u8a66'):1})
        tt3.insert().execute({ue('\u6e2c\u8a66_id'): 1,
                              ue('unitable1_\u6e2c\u8a66'): 5,
                              u('Unitéble2_b'): 1,
                              ue('\u6e2c\u8a66_self'): 1})

        self.assert_(tt1.select(order_by=desc(u('méil'))).execute().fetchall() ==
                     [(2, 7), (1, 5)])
        self.assert_(tt2.select(order_by=desc(u('méil'))).execute().fetchall() ==
                     [(2, 2), (1, 1)])
        self.assert_(tt3.select(order_by=desc(ue('\u6e2c\u8a66_id'))).
                     execute().fetchall() ==
                     [(2, 7, 2, 2), (1, 5, 1, 1)])
        meta.drop_all()
        metadata.create_all()

    def test_repr(self):

        m = MetaData()
        t = Table(ue('\u6e2c\u8a66'), m, Column(ue('\u6e2c\u8a66_id'), Integer))

        # I hardly understand what's going on with the backslashes in
        # this one on py2k vs. py3k
        eq_(
            repr(t),
            (
                "Table('\\u6e2c\\u8a66', MetaData(bind=None), "
                "Column('\\u6e2c\\u8a66_id', Integer(), table=<\u6e2c\u8a66>), "
                "schema=None)"))

class EscapesDefaultsTest(fixtures.TestBase):
    def test_default_exec(self):
        metadata = MetaData(testing.db)
        t1 = Table('t1', metadata,
            Column('special_col', Integer, Sequence('special_col'), primary_key=True),
            Column('data', String(50)) # to appease SQLite without DEFAULT VALUES
            )
        metadata.create_all()

        try:
            engine = metadata.bind

            # reset the identifier preparer, so that we can force it to cache
            # a unicode identifier
            engine.dialect.identifier_preparer = engine.dialect.preparer(engine.dialect)
            select([column('special_col')]).select_from(t1).execute().close()
            assert isinstance(engine.dialect.identifier_preparer.format_sequence(Sequence('special_col')), str)

            # now execute, run the sequence.  it should run in u"Special_col.nextid" or similar as
            # a unicode object; cx_oracle asserts that this is None or a String (postgresql lets it pass thru).
            # ensure that executioncontext._exec_default() is encoding.
            t1.insert().execute(data='foo')
        finally:
            metadata.drop_all()


