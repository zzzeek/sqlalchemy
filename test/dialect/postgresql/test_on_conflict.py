# coding: utf-8

from sqlalchemy.testing.assertions import (
    eq_, assert_raises, assert_raises_message, AssertsExecutionResults,
    AssertsCompiledSQL)
from sqlalchemy.testing import engines, fixtures
from sqlalchemy import testing
import datetime
from sqlalchemy import (
    Table, Column, select, MetaData, text, Integer, String, Sequence, Numeric,
    DateTime, BigInteger, func, extract, SmallInteger)
from sqlalchemy import exc, schema
from sqlalchemy.dialects.postgresql import base as postgresql
from sqlalchemy.dialects.postgresql.on_conflict import DoUpdate, DoNothing
import logging
import logging.handlers
from sqlalchemy.testing.mock import Mock
from sqlalchemy.engine import engine_from_config
from sqlalchemy.engine import url
from sqlalchemy.testing import is_
from sqlalchemy.testing import expect_deprecated


class OnConflictTest(fixtures.TestBase, AssertsExecutionResults, AssertsCompiledSQL):

    __only_on__ = 'postgresql'
    __backend__ = True

    @testing.only_if(
        "postgresql >= 9.5", "requires ON CONFLICT clause support")
    def test_on_conflict_do_nothing(self):
        meta = MetaData(testing.db)
        users = Table(
            'users', meta, Column(
                'id', Integer, primary_key=True), Column(
                'name', String(50)), schema='test_schema')
        users.create()
        try:
            users.insert(postgresql_on_conflict='nothing').execute(id=1, name='name1')
            users.insert(postgresql_on_conflict=DoNothing()).execute(id=1, name='name2')
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name1')])
        finally:
            users.drop()

    @testing.only_if(
        "postgresql >= 9.5", "requires ON CONFLICT clause support")
    def test_on_conflict_do_update(self):
        meta = MetaData(testing.db)
        users = Table(
            'users', meta, Column(
                'id', Integer, primary_key=True), Column(
                'name', String(50)), schema='test_schema')
        users.create()
        try:
            users.insert(postgresql_on_conflict=DoUpdate(users.c.id).set_with_excluded(users.c.name)).execute(id=1, name='name1')
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name1')])
            users.insert(postgresql_on_conflict=DoUpdate(users.c.id).set_with_excluded(users.c.id, users.c.name)).execute(id=1, name='name2')
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name2')])
            users.insert(postgresql_on_conflict='update').execute(id=1, name='name3')
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name3')])
            users.insert(postgresql_on_conflict='update', values=dict(id=1, name='name4')).execute()
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name4')])
        finally:
            users.drop()
