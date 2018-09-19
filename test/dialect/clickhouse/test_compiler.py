from sqlalchemy.dialects.postgresql.base import PGCompiler, PGDialect
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.sql import column, compiler, func, table
from sqlalchemy.sql.elements import ClauseList
from sqlalchemy.testing import AssertsCompiledSQL, \
    engines, expect_warnings, fixtures
from sqlalchemy import exc, Integer, select, String

tbl = table(
  'nba',
  column('id', Integer),
  column('name', String)
)


class ClickHouseCompiler(PGCompiler):
    def group_by_clause(self, select, **kw):
        # Usage check and move summaries to end of _group_by_clause
        summ_names = ('rollup', 'with_rollup', 'with_totals')
        summ_sql = (
          lambda x: self.process(x), lambda x: 'WITH ROLLUP',
          lambda x: 'WITH TOTALS')
        name_sqls = dict(zip(summ_names, summ_sql))

        summaries = [c for c in select._group_by_clause if c.name in summ_names]
        select._group_by_clause = ClauseList(
          *list(set(select._group_by_clause) - set(summaries))
        )
        text = " GROUP BY"
        group_by = super(ClickHouseCompiler, self).group_by_clause(select, **kw)
        if group_by:
            text = group_by
        for name in summ_names:
            for s in summaries:
                if s.name == name:
                    text += ' ' + name_sqls[s.name](s)
        return text


class ClickHouseDialect(PGDialect):
    name = 'clickhouse'
    statement_compiler = ClickHouseCompiler


class CompileGroupByTest(fixtures.TestBase, AssertsCompiledSQL):
    __dialect__ = ClickHouseDialect()

    def test_group_by_without_summary(self):
        stmt = select([tbl.c.id]).group_by(tbl.c.id)
        self.assert_compile(
            stmt,
            "SELECT nba.id FROM nba GROUP BY nba.id"
        )

    def test_group_by_with_rollup(self):
        stmt = select([tbl.c.id]).group_by(tbl.c.id, func.with_rollup())
        self.assert_compile(
            stmt,
            "SELECT nba.id FROM nba GROUP BY nba.id WITH ROLLUP"
        )

    def test_group_by_with_rollup_with_totals(self):
        stmt = select([tbl.c.id]).group_by(tbl.c.id, func.with_rollup(), func.with_totals())
        self.assert_compile(
            stmt,
            "SELECT nba.id FROM nba GROUP BY nba.id WITH ROLLUP WITH TOTALS"
        )

    def test_group_by_rollup(self):
        stmt = select([tbl.c.id]).group_by(func.rollup(tbl.c.id, tbl.c.name))
        self.assert_compile(
            stmt,
            "SELECT nba.id FROM nba GROUP BY ROLLUP(nba.id, nba.name)"
        )
