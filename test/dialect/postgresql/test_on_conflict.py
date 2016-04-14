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

    @testing.only_if(
        "postgresql >= 9.5", "requires ON CONFLICT clause support")
    def test_on_conflict_do_update_exotic_targets(self):
        meta = MetaData(testing.db)
        users = Table(
            'users', meta, 
            Column('id', Integer, primary_key=True), 
            Column('name', String(50)), 
            Column('login_email', String(50)), 
            Column('lets_index_this', String(50)), 
            schema='test_schema')
        unique_constraint = schema.UniqueConstraint(users.c.login_email, name='uq_login_email')
        bogus_index = schema.Index('idx_special_ops', users.c.lets_index_this, postgresql_where=users.c.lets_index_this > 'm')
        users.create()
        try:
            users.insert().execute(id=1, name='name1', login_email='name1@gmail.com', lets_index_this='not')
            users.insert().execute(id=2, name='name2', login_email='name2@gmail.com', lets_index_this='not')
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name1', 'name1@gmail.com', 'not')])

            # try primary key constraint: cause an upsert on unique id column
            poc = DoUpdate(users.primary_key).set_with_excluded(users.c.name, users.c.login_email)
            users.insert(postgresql_on_conflict=poc).execute(id=1, name='name2', login_email='name1@gmail.com', lets_index_this='not')
            eq_(users.select().where(users.c.id == 1)
                .execute().fetchall(), [(1, 'name2', 'name1@gmail.com', 'not')])

            # try unique constraint: cause an upsert on target login_email, not id
            poc = DoUpdate(unique_constraint).set_with_excluded(users.c.id, users.c.name, users.c.login_email)
            # note: lets_index_this value totally ignored in SET clause.
            users.insert(postgresql_on_conflict=poc).execute(id=42, name='nameunique', login_email='name2@gmail.com', lets_index_this='unique')
            eq_(users.select().where(users.c.login_email == 'name2@gmail.com')
                .execute().fetchall(), [(42, 'nameunique', 'name2@gmail.com', 'not')])

            # try bogus index
            try:
                users.insert(
                    postgresql_on_conflict=DoUpdate(bogus_index).set_with_excluded(users.c.name, users.c.login_email)
                    ).execute(id=1, name='namebogus', login_email='bogus@gmail.com', lets_index_this='bogus')
                raise Exception("Using bogus index should have raised exception")
            except exc.ProgrammingError:
                pass # expected exception
        finally:
            users.drop()
