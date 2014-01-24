from sqlalchemy.testing import fixtures, eq_
from ..orm._fixtures import FixtureTest
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship, interfaces, backref
from sqlalchemy.ext.automap import generate_relationship
from sqlalchemy.testing.mock import Mock, call

class AutomapTest(fixtures.MappedTest):
    @classmethod
    def define_tables(cls, metadata):
        FixtureTest.define_tables(metadata)

    def test_relationship_o2m_default(self):
        Base = automap_base(metadata=self.metadata)
        Base.prepare()

        User = Base.classes.users
        Address = Base.classes.addresses

        a1 = Address(email_address='e1')
        u1 = User(name='u1', addresses_collection=[a1])
        assert a1.users is u1

    def test_relationship_explicit_override_o2m(self):
        Base = automap_base(metadata=self.metadata)
        prop = relationship("addresses", collection_class=set)
        class User(Base):
            __tablename__ = 'users'

            addresses_collection = prop

        Base.prepare()
        assert User.addresses_collection.property is prop
        Address = Base.classes.addresses

        a1 = Address(email_address='e1')
        u1 = User(name='u1', addresses_collection=set([a1]))
        assert a1.user is u1

    def test_relationship_explicit_override_m2o(self):
        Base = automap_base(metadata=self.metadata)

        prop = relationship("users")
        class Address(Base):
            __tablename__ = 'addresses'

            users = prop

        Base.prepare()
        User = Base.classes.users

        assert Address.users.property is prop
        a1 = Address(email_address='e1')
        u1 = User(name='u1', address_collection=[a1])
        assert a1.users is u1


    def test_relationship_self_referential(self):
        Base = automap_base(metadata=self.metadata)
        Base.prepare()

        Node = Base.classes.nodes

        n1 = Node()
        n2 = Node()
        n1.nodes_collection.append(n2)
        assert n2.nodes is n1

    def test_naming_schemes(self):
        Base = automap_base(metadata=self.metadata)

        def classname_for_table(base, tablename, table):
            return str("cls_" + tablename)

        def name_for_scalar_relationship(base, local_cls, referred_cls, constraint):
            return "scalar_" + referred_cls.__name__

        def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
            return "coll_" + referred_cls.__name__

        Base.prepare(
                    classname_for_table=classname_for_table,
                    name_for_scalar_relationship=name_for_scalar_relationship,
                    name_for_collection_relationship=name_for_collection_relationship
                )

        User = Base.classes.cls_users
        Address = Base.classes.cls_addresses

        u1 = User()
        a1 = Address()
        u1.coll_cls_addresses.append(a1)
        assert a1.scalar_cls_users is u1

    def test_relationship_m2m(self):
        Base = automap_base(metadata=self.metadata)

        Base.prepare()

        Order, Item = Base.classes.orders, Base.classes['items']

        o1 = Order()
        i1 = Item()
        o1.items_collection.append(i1)
        assert o1 in i1.orders_collection

    def test_relationship_explicit_override_forwards_m2m(self):
        Base = automap_base(metadata=self.metadata)

        class Order(Base):
            __tablename__ = 'orders'

            items_collection = relationship("items",
                                    secondary="order_items",
                                    collection_class=set)
        Base.prepare()

        Item = Base.classes['items']

        o1 = Order()
        i1 = Item()
        o1.items_collection.add(i1)

        # it's 'order_collection' because the class name is
        # "Order" !
        assert isinstance(i1.order_collection, list)
        assert o1 in i1.order_collection

    def test_relationship_pass_params(self):
        Base = automap_base(metadata=self.metadata)

        mock = Mock()
        def _gen_relationship(base, direction, return_fn, attrname,
                                    local_cls, referred_cls, **kw):
            mock(base, direction, attrname)
            return generate_relationship(base, direction, return_fn,
                                    attrname, local_cls, referred_cls, **kw)

        Base.prepare(generate_relationship=_gen_relationship)
        assert set(tuple(c[1]) for c in mock.mock_calls).issuperset([
                (Base, interfaces.MANYTOONE, "nodes"),
                (Base, interfaces.MANYTOMANY, "keywords_collection"),
                (Base, interfaces.MANYTOMANY, "items_collection"),
                (Base, interfaces.MANYTOONE, "users"),
                (Base, interfaces.ONETOMANY, "addresses_collection"),
        ])
