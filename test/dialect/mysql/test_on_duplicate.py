from sqlalchemy.testing.assertions import eq_, assert_raises
from sqlalchemy.testing import fixtures
from sqlalchemy import testing
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import Table, MetaData, Column, Integer, String


class OnDuplicateTest(fixtures.TablesTest):
    __only_on__ = 'mysql',
    __backend__ = True
    run_define_tables = 'each'

    @classmethod
    def define_tables(cls, metadata):
        Table(
            'foos', metadata,
            Column('id', Integer, primary_key=True),
            Column('bar', String(10)),
            Column('baz', String(10)),
        )

    def test_bad_args(self):
        assert_raises(
            ValueError,
            insert(self.tables.foos, values={}).on_duplicate_key_update
        )

    def test_on_duplicate_key_update(self):
        foos = self.tables.foos
        with testing.db.connect() as conn:
            conn.execute(insert(foos, dict(id=1, bar='b', baz='bz')))
            stmt = insert(foos, [dict(id=1, bar='ab'), dict(id=2, bar='b')])
            stmt = stmt.on_duplicate_key_update(bar=stmt.vals.bar)
            result = conn.execute(stmt)
            eq_(result.inserted_primary_key, [2])
            eq_(
                conn.execute(foos.select().where(foos.c.id == 1)).fetchall(),
                [(1, 'ab', 'bz')]
            )

