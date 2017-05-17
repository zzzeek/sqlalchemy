from collections import OrderedDict

import pytest

from sqlalchemy import Table, Column, Integer, String, MetaData
from sqlalchemy.dialects import mysql
from sqlalchemy.sql.expression import literal_column


table = Table(
    'foos', MetaData(),
    Column('id', Integer, primary_key=True),
    Column('bar', String(10)),
    Column('baz', String(10)),
)


def check_statement(statement, expected_sql):
    assert expected_sql == str(statement.compile(dialect=mysql.dialect()))


def test_from_values():
    stmt = mysql.insert(table, [{'id': 1, 'bar': 'ab'}, {'id': 2, 'bar': 'b'}])
    update = OrderedDict([('bar', stmt.values.bar), ('baz', stmt.values.baz)])
    from_values = (
        'INSERT INTO foos (id, bar) VALUES (%s, %s), (%s, %s) '
        'ON DUPLICATE KEY UPDATE bar = VALUES(bar), baz = VALUES(baz)'
    )
    stmt = stmt.on_duplicate_key_update(update=update)
    check_statement(stmt, from_values)


def test_from_literal():
    stmt = mysql.insert(table, [{'id': 1, 'bar': 'ab'}, {'id': 2, 'bar': 'b'}])
    stmt = stmt.on_duplicate_key_update(update=dict(bar=literal_column('bb')))
    from_values = (
        'INSERT INTO foos (id, bar) VALUES (%s, %s), (%s, %s) '
        'ON DUPLICATE KEY UPDATE bar = "bb"'
    )
