"""basic tests of lazy loaded attributes"""

from sqlalchemy.testing import assert_raises, assert_raises_message
import datetime
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import attributes, exc as orm_exc
import sqlalchemy as sa
from sqlalchemy import testing
from sqlalchemy import Integer, String, ForeignKey, SmallInteger
from sqlalchemy.types import TypeDecorator
from sqlalchemy.testing.schema import Table
from sqlalchemy.testing.schema import Column
from sqlalchemy.orm import mapper, relationship, create_session
from sqlalchemy.testing import eq_
from sqlalchemy.testing import fixtures
from test.orm import _fixtures


class LazyTest(_fixtures.FixtureTest):
    run_inserts = 'once'
    run_deletes = None

    def test_basic(self):
        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)

        mapper(User, users, properties={
            'addresses':relationship(mapper(Address, addresses), lazy='select')
        })
        sess = create_session()
        q = sess.query(User)
        assert [User(id=7, addresses=[Address(id=1, email_address='jack@bean.com')])] == q.filter(users.c.id == 7).all()

    def test_needs_parent(self):
        """test the error raised when parent object is not bound."""

        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)


        mapper(User, users, properties={
            'addresses':relationship(mapper(Address, addresses), lazy='select')
        })
        sess = create_session()
        q = sess.query(User)
        u = q.filter(users.c.id == 7).first()
        sess.expunge(u)
        assert_raises(orm_exc.DetachedInstanceError, getattr, u, 'addresses')

    def test_orderby(self):
        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)

        mapper(User, users, properties = {
            'addresses':relationship(mapper(Address, addresses), lazy='select', order_by=addresses.c.email_address),
        })
        q = create_session().query(User)
        assert [
            User(id=7, addresses=[
                Address(id=1)
            ]),
            User(id=8, addresses=[
                Address(id=3, email_address='ed@bettyboop.com'),
                Address(id=4, email_address='ed@lala.com'),
                Address(id=2, email_address='ed@wood.com')
            ]),
            User(id=9, addresses=[
                Address(id=5)
            ]),
            User(id=10, addresses=[])
        ] == q.all()

    def test_orderby_secondary(self):
        """tests that a regular mapper select on a single table can order by a relationship to a second table"""

        Address, addresses, users, User = (self.classes.Address,
                                self.tables.addresses,
                                self.tables.users,
                                self.classes.User)


        mapper(Address, addresses)

        mapper(User, users, properties = dict(
            addresses = relationship(Address, lazy='select'),
        ))
        q = create_session().query(User)
        l = q.filter(users.c.id==addresses.c.user_id).order_by(addresses.c.email_address).all()
        assert [
            User(id=8, addresses=[
                Address(id=2, email_address='ed@wood.com'),
                Address(id=3, email_address='ed@bettyboop.com'),
                Address(id=4, email_address='ed@lala.com'),
            ]),
            User(id=9, addresses=[
                Address(id=5)
            ]),
            User(id=7, addresses=[
                Address(id=1)
            ]),
        ] == l

    def test_orderby_desc(self):
        Address, addresses, users, User = (self.classes.Address,
                                self.tables.addresses,
                                self.tables.users,
                                self.classes.User)

        mapper(Address, addresses)

        mapper(User, users, properties = dict(
            addresses = relationship(Address, lazy='select',  order_by=[sa.desc(addresses.c.email_address)]),
        ))
        sess = create_session()
        assert [
            User(id=7, addresses=[
                Address(id=1)
            ]),
            User(id=8, addresses=[
                Address(id=2, email_address='ed@wood.com'),
                Address(id=4, email_address='ed@lala.com'),
                Address(id=3, email_address='ed@bettyboop.com'),
            ]),
            User(id=9, addresses=[
                Address(id=5)
            ]),
            User(id=10, addresses=[])
        ] == sess.query(User).all()

    def test_no_orphan(self):
        """test that a lazily loaded child object is not marked as an orphan"""

        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)


        mapper(User, users, properties={
            'addresses':relationship(Address, cascade="all,delete-orphan", lazy='select')
        })
        mapper(Address, addresses)

        sess = create_session()
        user = sess.query(User).get(7)
        assert getattr(User, 'addresses').hasparent(attributes.instance_state(user.addresses[0]), optimistic=True)
        assert not sa.orm.class_mapper(Address)._is_orphan(attributes.instance_state(user.addresses[0]))

    def test_limit(self):
        """test limit operations combined with lazy-load relationships."""

        users, items, order_items, orders, Item, User, Address, Order, addresses = (self.tables.users,
                                self.tables.items,
                                self.tables.order_items,
                                self.tables.orders,
                                self.classes.Item,
                                self.classes.User,
                                self.classes.Address,
                                self.classes.Order,
                                self.tables.addresses)


        mapper(Item, items)
        mapper(Order, orders, properties={
            'items':relationship(Item, secondary=order_items, lazy='select')
        })
        mapper(User, users, properties={
            'addresses':relationship(mapper(Address, addresses), lazy='select'),
            'orders':relationship(Order, lazy='select')
        })

        sess = create_session()
        q = sess.query(User)

        if testing.against('mssql'):
            l = q.limit(2).all()
            assert self.static.user_all_result[:2] == l
        else:
            l = q.limit(2).offset(1).all()
            assert self.static.user_all_result[1:3] == l

    def test_distinct(self):
        users, items, order_items, orders, Item, User, Address, Order, addresses = (self.tables.users,
                                self.tables.items,
                                self.tables.order_items,
                                self.tables.orders,
                                self.classes.Item,
                                self.classes.User,
                                self.classes.Address,
                                self.classes.Order,
                                self.tables.addresses)

        mapper(Item, items)
        mapper(Order, orders, properties={
            'items':relationship(Item, secondary=order_items, lazy='select')
        })
        mapper(User, users, properties={
            'addresses':relationship(mapper(Address, addresses), lazy='select'),
            'orders':relationship(Order, lazy='select')
        })

        sess = create_session()
        q = sess.query(User)

        # use a union all to get a lot of rows to join against
        u2 = users.alias('u2')
        s = sa.union_all(u2.select(use_labels=True), u2.select(use_labels=True), u2.select(use_labels=True)).alias('u')
        l = q.filter(s.c.u2_id==User.id).order_by(User.id).distinct().all()
        eq_(self.static.user_all_result, l)

    def test_uselist_false_warning(self):
        """test that multiple rows received by a uselist=False raises a warning."""

        User, users, orders, Order = (self.classes.User,
                                self.tables.users,
                                self.tables.orders,
                                self.classes.Order)


        mapper(User, users, properties={
            'order':relationship(Order, uselist=False)
        })
        mapper(Order, orders)
        s = create_session()
        u1 = s.query(User).filter(User.id==7).one()
        assert_raises(sa.exc.SAWarning, getattr, u1, 'order')

    def test_one_to_many_scalar(self):
        Address, addresses, users, User = (self.classes.Address,
                                self.tables.addresses,
                                self.tables.users,
                                self.classes.User)

        mapper(User, users, properties = dict(
            address = relationship(mapper(Address, addresses), lazy='select', uselist=False)
        ))
        q = create_session().query(User)
        l = q.filter(users.c.id == 7).all()
        assert [User(id=7, address=Address(id=1))] == l

    def test_many_to_one_binds(self):
        Address, addresses, users, User = (self.classes.Address,
                                self.tables.addresses,
                                self.tables.users,
                                self.classes.User)

        mapper(Address, addresses, primary_key=[addresses.c.user_id, addresses.c.email_address])

        mapper(User, users, properties = dict(
            address = relationship(Address, uselist=False,
                primaryjoin=sa.and_(users.c.id==addresses.c.user_id, addresses.c.email_address=='ed@bettyboop.com')
            )
        ))
        q = create_session().query(User)
        eq_(
            [
                User(id=7, address=None),
                User(id=8, address=Address(id=3)),
                User(id=9, address=None),
                User(id=10, address=None),
            ],
            list(q)
        )


    def test_double(self):
        """tests lazy loading with two relationships simulatneously, from the same table, using aliases.  """

        users, orders, User, Address, Order, addresses = (self.tables.users,
                                self.tables.orders,
                                self.classes.User,
                                self.classes.Address,
                                self.classes.Order,
                                self.tables.addresses)


        openorders = sa.alias(orders, 'openorders')
        closedorders = sa.alias(orders, 'closedorders')

        mapper(Address, addresses)

        mapper(Order, orders)

        open_mapper = mapper(Order, openorders, non_primary=True)
        closed_mapper = mapper(Order, closedorders, non_primary=True)
        mapper(User, users, properties = dict(
            addresses = relationship(Address, lazy = True),
            open_orders = relationship(open_mapper, primaryjoin = sa.and_(openorders.c.isopen == 1, users.c.id==openorders.c.user_id), lazy='select'),
            closed_orders = relationship(closed_mapper, primaryjoin = sa.and_(closedorders.c.isopen == 0, users.c.id==closedorders.c.user_id), lazy='select')
        ))
        q = create_session().query(User)

        assert [
            User(
                id=7,
                addresses=[Address(id=1)],
                open_orders = [Order(id=3)],
                closed_orders = [Order(id=1), Order(id=5)]
            ),
            User(
                id=8,
                addresses=[Address(id=2), Address(id=3), Address(id=4)],
                open_orders = [],
                closed_orders = []
            ),
            User(
                id=9,
                addresses=[Address(id=5)],
                open_orders = [Order(id=4)],
                closed_orders = [Order(id=2)]
            ),
            User(id=10)

        ] == q.all()

        sess = create_session()
        user = sess.query(User).get(7)
        assert [Order(id=1), Order(id=5)] == create_session().query(closed_mapper).with_parent(user, property='closed_orders').all()
        assert [Order(id=3)] == create_session().query(open_mapper).with_parent(user, property='open_orders').all()

    def test_many_to_many(self):
        keywords, items, item_keywords, Keyword, Item = (self.tables.keywords,
                                self.tables.items,
                                self.tables.item_keywords,
                                self.classes.Keyword,
                                self.classes.Item)


        mapper(Keyword, keywords)
        mapper(Item, items, properties = dict(
                keywords = relationship(Keyword, secondary=item_keywords, lazy='select'),
        ))

        q = create_session().query(Item)
        assert self.static.item_keyword_result == q.all()

        assert self.static.item_keyword_result[0:2] == q.join('keywords').filter(keywords.c.name == 'red').all()

    def test_uses_get(self):
        """test that a simple many-to-one lazyload optimizes to use query.get()."""

        Address, addresses, users, User = (self.classes.Address,
                                self.tables.addresses,
                                self.tables.users,
                                self.classes.User)


        for pj in (
            None,
            users.c.id==addresses.c.user_id,
            addresses.c.user_id==users.c.id
        ):
            mapper(Address, addresses, properties = dict(
                user = relationship(mapper(User, users), lazy='select', primaryjoin=pj)
            ))

            sess = create_session()

            # load address
            a1 = sess.query(Address).filter_by(email_address="ed@wood.com").one()

            # load user that is attached to the address
            u1 = sess.query(User).get(8)

            def go():
                # lazy load of a1.user should get it from the session
                assert a1.user is u1
            self.assert_sql_count(testing.db, go, 0)
            sa.orm.clear_mappers()

    def test_uses_get_compatible_types(self):
        """test the use_get optimization with compatible but non-identical types"""

        User, Address = self.classes.User, self.classes.Address


        class IntDecorator(TypeDecorator):
            impl = Integer

        class SmallintDecorator(TypeDecorator):
            impl = SmallInteger

        class SomeDBInteger(sa.Integer):
            pass

        for tt in [
            Integer,
            SmallInteger,
            IntDecorator,
            SmallintDecorator,
            SomeDBInteger,
        ]:
            m = sa.MetaData()
            users = Table('users', m,
                Column('id', Integer, primary_key=True, test_needs_autoincrement=True),
                Column('name', String(30), nullable=False),
            )
            addresses = Table('addresses', m,
                  Column('id', Integer, primary_key=True, test_needs_autoincrement=True),
                  Column('user_id', tt, ForeignKey('users.id')),
                  Column('email_address', String(50), nullable=False),
            )

            mapper(Address, addresses, properties = dict(
                user = relationship(mapper(User, users))
            ))

            sess = create_session(bind=testing.db)

            # load address
            a1 = sess.query(Address).filter_by(email_address="ed@wood.com").one()

            # load user that is attached to the address
            u1 = sess.query(User).get(8)

            def go():
                # lazy load of a1.user should get it from the session
                assert a1.user is u1
            self.assert_sql_count(testing.db, go, 0)
            sa.orm.clear_mappers()

    def test_many_to_one(self):
        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)

        mapper(Address, addresses, properties = dict(
            user = relationship(mapper(User, users), lazy='select')
        ))
        sess = create_session()
        q = sess.query(Address)
        a = q.filter(addresses.c.id==1).one()

        assert a.user is not None

        u1 = sess.query(User).get(7)

        assert a.user is u1



    def test_backrefs_dont_lazyload(self):
        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)

        mapper(User, users, properties={
            'addresses':relationship(Address, backref='user')
        })
        mapper(Address, addresses)
        sess = create_session()
        ad = sess.query(Address).filter_by(id=1).one()
        assert ad.user.id == 7
        def go():
            ad.user = None
            assert ad.user is None
        self.assert_sql_count(testing.db, go, 0)

        u1 = sess.query(User).filter_by(id=7).one()
        def go():
            assert ad not in u1.addresses
        self.assert_sql_count(testing.db, go, 1)

        sess.expire(u1, ['addresses'])
        def go():
            assert ad in u1.addresses
        self.assert_sql_count(testing.db, go, 1)

        sess.expire(u1, ['addresses'])
        ad2 = Address()
        def go():
            ad2.user = u1
            assert ad2.user is u1
        self.assert_sql_count(testing.db, go, 0)

        def go():
            assert ad2 in u1.addresses
        self.assert_sql_count(testing.db, go, 1)

class GetterStateTest(_fixtures.FixtureTest):
    """test lazyloader on non-existent attribute returns
    expected attribute symbols, maintain expected state"""

    run_inserts = None

    def _u_ad_fixture(self, populate_user):
        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)

        mapper(User, users, properties={
            'addresses':relationship(Address, backref='user')
        })
        mapper(Address, addresses)

        sess = create_session()
        a1 = Address(email_address='a1')
        sess.add(a1)
        if populate_user:
            a1.user = User(name='ed')
        sess.flush()
        if populate_user:
            sess.expire_all()
        return User, Address, sess, a1

    def test_get_empty_passive_return_never_set(self):
        User, Address, sess, a1 = self._u_ad_fixture(False)
        eq_(
            Address.user.impl.get(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_RETURN_NEVER_SET),
            attributes.NEVER_SET
        )
        assert 'user_id' not in a1.__dict__
        assert 'user' not in a1.__dict__

    def test_history_empty_passive_return_never_set(self):
        User, Address, sess, a1 = self._u_ad_fixture(False)
        eq_(
            Address.user.impl.get_history(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_RETURN_NEVER_SET),
            ((), (), ())
        )
        assert 'user_id' not in a1.__dict__
        assert 'user' not in a1.__dict__

    def test_get_empty_passive_no_initialize(self):
        User, Address, sess, a1 = self._u_ad_fixture(False)
        eq_(
            Address.user.impl.get(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_NO_INITIALIZE),
            attributes.PASSIVE_NO_RESULT
        )
        assert 'user_id' not in a1.__dict__
        assert 'user' not in a1.__dict__

    def test_history_empty_passive_no_initialize(self):
        User, Address, sess, a1 = self._u_ad_fixture(False)
        eq_(
            Address.user.impl.get_history(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_NO_INITIALIZE),
            attributes.HISTORY_BLANK
        )
        assert 'user_id' not in a1.__dict__
        assert 'user' not in a1.__dict__

    def test_get_populated_passive_no_initialize(self):
        User, Address, sess, a1 = self._u_ad_fixture(True)
        eq_(
            Address.user.impl.get(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_NO_INITIALIZE),
            attributes.PASSIVE_NO_RESULT
        )
        assert 'user_id' not in a1.__dict__
        assert 'user' not in a1.__dict__

    def test_history_populated_passive_no_initialize(self):
        User, Address, sess, a1 = self._u_ad_fixture(True)
        eq_(
            Address.user.impl.get_history(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_NO_INITIALIZE),
            attributes.HISTORY_BLANK
        )
        assert 'user_id' not in a1.__dict__
        assert 'user' not in a1.__dict__

    def test_get_populated_passive_return_never_set(self):
        User, Address, sess, a1 = self._u_ad_fixture(True)
        eq_(
            Address.user.impl.get(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_RETURN_NEVER_SET),
            User(name='ed')
        )

    def test_history_populated_passive_return_never_set(self):
        User, Address, sess, a1 = self._u_ad_fixture(True)
        eq_(
            Address.user.impl.get_history(
                attributes.instance_state(a1),
                attributes.instance_dict(a1),
                passive=attributes.PASSIVE_RETURN_NEVER_SET),
            ((), [User(name='ed'), ], ())
        )

class M2OGetTest(_fixtures.FixtureTest):
    run_inserts = 'once'
    run_deletes = None

    def test_m2o_noload(self):
        """test that a NULL foreign key doesn't trigger a lazy load"""

        users, Address, addresses, User = (self.tables.users,
                                self.classes.Address,
                                self.tables.addresses,
                                self.classes.User)

        mapper(User, users)

        mapper(Address, addresses, properties={
            'user':relationship(User)
        })

        sess = create_session()
        ad1 = Address(email_address='somenewaddress', id=12)
        sess.add(ad1)
        sess.flush()
        sess.expunge_all()

        ad2 = sess.query(Address).get(1)
        ad3 = sess.query(Address).get(ad1.id)
        def go():
            # one lazy load
            assert ad2.user.name == 'jack'
            # no lazy load
            assert ad3.user is None
        self.assert_sql_count(testing.db, go, 1)

class CorrelatedTest(fixtures.MappedTest):

    @classmethod
    def define_tables(self, meta):
        Table('user_t', meta,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)))

        Table('stuff', meta,
              Column('id', Integer, primary_key=True),
              Column('date', sa.Date),
              Column('user_id', Integer, ForeignKey('user_t.id')))

    @classmethod
    def insert_data(cls):
        stuff, user_t = cls.tables.stuff, cls.tables.user_t

        user_t.insert().execute(
            {'id':1, 'name':'user1'},
            {'id':2, 'name':'user2'},
            {'id':3, 'name':'user3'})

        stuff.insert().execute(
            {'id':1, 'user_id':1, 'date':datetime.date(2007, 10, 15)},
            {'id':2, 'user_id':1, 'date':datetime.date(2007, 12, 15)},
            {'id':3, 'user_id':1, 'date':datetime.date(2007, 11, 15)},
            {'id':4, 'user_id':2, 'date':datetime.date(2008, 1, 15)},
            {'id':5, 'user_id':3, 'date':datetime.date(2007, 6, 15)})

    def test_correlated_lazyload(self):
        stuff, user_t = self.tables.stuff, self.tables.user_t

        class User(fixtures.ComparableEntity):
            pass

        class Stuff(fixtures.ComparableEntity):
            pass

        mapper(Stuff, stuff)

        stuff_view = sa.select([stuff.c.id]).where(stuff.c.user_id==user_t.c.id).correlate(user_t).order_by(sa.desc(stuff.c.date)).limit(1)

        mapper(User, user_t, properties={
            'stuff':relationship(Stuff, primaryjoin=sa.and_(user_t.c.id==stuff.c.user_id, stuff.c.id==(stuff_view.as_scalar())))
        })

        sess = create_session()

        eq_(sess.query(User).all(), [
            User(name='user1', stuff=[Stuff(date=datetime.date(2007, 12, 15), id=2)]),
            User(name='user2', stuff=[Stuff(id=4, date=datetime.date(2008, 1 , 15))]),
            User(name='user3', stuff=[Stuff(id=5, date=datetime.date(2007, 6, 15))])
        ])


