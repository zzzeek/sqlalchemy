from sqlalchemy.testing import eq_, assert_raises, \
    assert_raises_message, is_
from sqlalchemy.ext import declarative as decl
import sqlalchemy as sa
from sqlalchemy import testing
from sqlalchemy import Integer, String, ForeignKey, select, func
from sqlalchemy.testing.schema import Table, Column
from sqlalchemy.orm import relationship, create_session, class_mapper, \
    configure_mappers, clear_mappers, \
    deferred, column_property, Session, base as orm_base
from sqlalchemy.util import classproperty
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import events as orm_events
from sqlalchemy.testing import fixtures, mock
from sqlalchemy.testing.util import gc_collect

Base = None


class DeclarativeTestBase(fixtures.TestBase, testing.AssertsExecutionResults):

    def setup(self):
        global Base
        Base = decl.declarative_base(testing.db)

    def teardown(self):
        Session.close_all()
        clear_mappers()
        Base.metadata.drop_all()


class DeclarativeMixinTest(DeclarativeTestBase):

    def test_simple(self):

        class MyMixin(object):

            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

            def foo(self):
                return 'bar' + str(self.id)

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            name = Column(String(100), nullable=False, index=True)

        Base.metadata.create_all()
        session = create_session()
        session.add(MyModel(name='testing'))
        session.flush()
        session.expunge_all()
        obj = session.query(MyModel).one()
        eq_(obj.id, 1)
        eq_(obj.name, 'testing')
        eq_(obj.foo(), 'bar1')

    def test_unique_column(self):

        class MyMixin(object):

            id = Column(Integer, primary_key=True)
            value = Column(String, unique=True)

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'

        assert MyModel.__table__.c.value.unique

    def test_hierarchical_bases(self):

        class MyMixinParent:

            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

            def foo(self):
                return 'bar' + str(self.id)

        class MyMixin(MyMixinParent):

            baz = Column(String(100), nullable=False, index=True)

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            name = Column(String(100), nullable=False, index=True)

        Base.metadata.create_all()
        session = create_session()
        session.add(MyModel(name='testing', baz='fu'))
        session.flush()
        session.expunge_all()
        obj = session.query(MyModel).one()
        eq_(obj.id, 1)
        eq_(obj.name, 'testing')
        eq_(obj.foo(), 'bar1')
        eq_(obj.baz, 'fu')

    def test_mixin_overrides(self):
        """test a mixin that overrides a column on a superclass."""

        class MixinA(object):
            foo = Column(String(50))

        class MixinB(MixinA):
            foo = Column(Integer)

        class MyModelA(Base, MixinA):
            __tablename__ = 'testa'
            id = Column(Integer, primary_key=True)

        class MyModelB(Base, MixinB):
            __tablename__ = 'testb'
            id = Column(Integer, primary_key=True)

        eq_(MyModelA.__table__.c.foo.type.__class__, String)
        eq_(MyModelB.__table__.c.foo.type.__class__, Integer)

    def test_not_allowed(self):

        class MyMixin:
            foo = Column(Integer, ForeignKey('bar.id'))

        def go():
            class MyModel(Base, MyMixin):
                __tablename__ = 'foo'

        assert_raises(sa.exc.InvalidRequestError, go)

        class MyRelMixin:
            foo = relationship('Bar')

        def go():
            class MyModel(Base, MyRelMixin):

                __tablename__ = 'foo'

        assert_raises(sa.exc.InvalidRequestError, go)

        class MyDefMixin:
            foo = deferred(Column('foo', String))

        def go():
            class MyModel(Base, MyDefMixin):
                __tablename__ = 'foo'

        assert_raises(sa.exc.InvalidRequestError, go)

        class MyCPropMixin:
            foo = column_property(Column('foo', String))

        def go():
            class MyModel(Base, MyCPropMixin):
                __tablename__ = 'foo'

        assert_raises(sa.exc.InvalidRequestError, go)

    def test_table_name_inherited(self):

        class MyMixin:

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()
            id = Column(Integer, primary_key=True)

        class MyModel(Base, MyMixin):
            pass

        eq_(MyModel.__table__.name, 'mymodel')

    def test_classproperty_still_works(self):
        class MyMixin(object):

            @classproperty
            def __tablename__(cls):
                return cls.__name__.lower()
            id = Column(Integer, primary_key=True)

        class MyModel(Base, MyMixin):
            __tablename__ = 'overridden'

        eq_(MyModel.__table__.name, 'overridden')

    def test_table_name_not_inherited(self):

        class MyMixin:

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()
            id = Column(Integer, primary_key=True)

        class MyModel(Base, MyMixin):
            __tablename__ = 'overridden'

        eq_(MyModel.__table__.name, 'overridden')

    def test_table_name_inheritance_order(self):

        class MyMixin1:

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower() + '1'

        class MyMixin2:

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower() + '2'

        class MyModel(Base, MyMixin1, MyMixin2):
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__table__.name, 'mymodel1')

    def test_table_name_dependent_on_subclass(self):

        class MyHistoryMixin:

            @declared_attr
            def __tablename__(cls):
                return cls.parent_name + '_changelog'

        class MyModel(Base, MyHistoryMixin):
            parent_name = 'foo'
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__table__.name, 'foo_changelog')

    def test_table_args_inherited(self):

        class MyMixin:
            __table_args__ = {'mysql_engine': 'InnoDB'}

        class MyModel(Base, MyMixin):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__table__.kwargs, {'mysql_engine': 'InnoDB'})

    def test_table_args_inherited_descriptor(self):

        class MyMixin:

            @declared_attr
            def __table_args__(cls):
                return {'info': cls.__name__}

        class MyModel(Base, MyMixin):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__table__.info, 'MyModel')

    def test_table_args_inherited_single_table_inheritance(self):

        class MyMixin:
            __table_args__ = {'mysql_engine': 'InnoDB'}

        class General(Base, MyMixin):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)
            type_ = Column(String(50))
            __mapper__args = {'polymorphic_on': type_}

        class Specific(General):
            __mapper_args__ = {'polymorphic_identity': 'specific'}

        assert Specific.__table__ is General.__table__
        eq_(General.__table__.kwargs, {'mysql_engine': 'InnoDB'})

    def test_columns_single_table_inheritance(self):
        """Test a column on a mixin with an alternate attribute name,
        mapped to a superclass and single-table inheritance subclass.
        The superclass table gets the column, the subclass shares
        the MapperProperty.

        """

        class MyMixin(object):
            foo = Column('foo', Integer)
            bar = Column('bar_newname', Integer)

        class General(Base, MyMixin):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)
            type_ = Column(String(50))
            __mapper__args = {'polymorphic_on': type_}

        class Specific(General):
            __mapper_args__ = {'polymorphic_identity': 'specific'}

        assert General.bar.prop.columns[0] is General.__table__.c.bar_newname
        assert len(General.bar.prop.columns) == 1
        assert Specific.bar.prop is General.bar.prop

    @testing.skip_if(lambda: testing.against('oracle'),
                     "Test has an empty insert in it at the moment")
    def test_columns_single_inheritance_conflict_resolution(self):
        """Test that a declared_attr can return the existing column and it will
        be ignored.  this allows conditional columns to be added.

        See [ticket:2472].

        """
        class Person(Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)

        class Mixin(object):

            @declared_attr
            def target_id(cls):
                return cls.__table__.c.get(
                    'target_id',
                    Column(Integer, ForeignKey('other.id'))
                )

            @declared_attr
            def target(cls):
                return relationship("Other")

        class Engineer(Mixin, Person):

            """single table inheritance"""

        class Manager(Mixin, Person):

            """single table inheritance"""

        class Other(Base):
            __tablename__ = 'other'
            id = Column(Integer, primary_key=True)

        is_(
            Engineer.target_id.property.columns[0],
            Person.__table__.c.target_id
        )
        is_(
            Manager.target_id.property.columns[0],
            Person.__table__.c.target_id
        )
        # do a brief round trip on this
        Base.metadata.create_all()
        session = Session()
        o1, o2 = Other(), Other()
        session.add_all([
            Engineer(target=o1),
            Manager(target=o2),
            Manager(target=o1)
        ])
        session.commit()
        eq_(session.query(Engineer).first().target, o1)

    def test_columns_joined_table_inheritance(self):
        """Test a column on a mixin with an alternate attribute name,
        mapped to a superclass and joined-table inheritance subclass.
        Both tables get the column, in the case of the subclass the two
        columns are joined under one MapperProperty.

        """

        class MyMixin(object):
            foo = Column('foo', Integer)
            bar = Column('bar_newname', Integer)

        class General(Base, MyMixin):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)
            type_ = Column(String(50))
            __mapper__args = {'polymorphic_on': type_}

        class Specific(General):
            __tablename__ = 'sub'
            id = Column(Integer, ForeignKey('test.id'), primary_key=True)
            __mapper_args__ = {'polymorphic_identity': 'specific'}

        assert General.bar.prop.columns[0] is General.__table__.c.bar_newname
        assert len(General.bar.prop.columns) == 1
        assert Specific.bar.prop is General.bar.prop
        eq_(len(Specific.bar.prop.columns), 1)
        assert Specific.bar.prop.columns[0] is General.__table__.c.bar_newname

    def test_column_join_checks_superclass_type(self):
        """Test that the logic which joins subclass props to those
        of the superclass checks that the superclass property is a column.

        """

        class General(Base):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)
            general_id = Column(Integer, ForeignKey('test.id'))
            type_ = relationship("General")

        class Specific(General):
            __tablename__ = 'sub'
            id = Column(Integer, ForeignKey('test.id'), primary_key=True)
            type_ = Column('foob', String(50))

        assert isinstance(General.type_.property, sa.orm.RelationshipProperty)
        assert Specific.type_.property.columns[0] is Specific.__table__.c.foob

    def test_column_join_checks_subclass_type(self):
        """Test that the logic which joins subclass props to those
        of the superclass checks that the subclass property is a column.

        """

        def go():
            class General(Base):
                __tablename__ = 'test'
                id = Column(Integer, primary_key=True)
                type_ = Column('foob', Integer)

            class Specific(General):
                __tablename__ = 'sub'
                id = Column(Integer, ForeignKey('test.id'), primary_key=True)
                specific_id = Column(Integer, ForeignKey('sub.id'))
                type_ = relationship("Specific")
        assert_raises_message(
            sa.exc.ArgumentError, "column 'foob' conflicts with property", go
        )

    def test_table_args_overridden(self):

        class MyMixin:
            __table_args__ = {'mysql_engine': 'Foo'}

        class MyModel(Base, MyMixin):
            __tablename__ = 'test'
            __table_args__ = {'mysql_engine': 'InnoDB'}
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__table__.kwargs, {'mysql_engine': 'InnoDB'})

    @testing.teardown_events(orm_events.MapperEvents)
    def test_declare_first_mixin(self):
        canary = mock.Mock()

        class MyMixin(object):
            @classmethod
            def __declare_first__(cls):
                canary.declare_first__(cls)

            @classmethod
            def __declare_last__(cls):
                canary.declare_last__(cls)

        class MyModel(Base, MyMixin):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        configure_mappers()

        eq_(
            canary.mock_calls,
            [
                mock.call.declare_first__(MyModel),
                mock.call.declare_last__(MyModel),
            ]
        )

    @testing.teardown_events(orm_events.MapperEvents)
    def test_declare_first_base(self):
        canary = mock.Mock()

        class MyMixin(object):
            @classmethod
            def __declare_first__(cls):
                canary.declare_first__(cls)

            @classmethod
            def __declare_last__(cls):
                canary.declare_last__(cls)

        class Base(MyMixin):
            pass
        Base = declarative_base(cls=Base)

        class MyModel(Base):
            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        configure_mappers()

        eq_(
            canary.mock_calls,
            [
                mock.call.declare_first__(MyModel),
                mock.call.declare_last__(MyModel),
            ]
        )

    @testing.teardown_events(orm_events.MapperEvents)
    def test_declare_first_direct(self):
        canary = mock.Mock()

        class MyOtherModel(Base):
            __tablename__ = 'test2'
            id = Column(Integer, primary_key=True)

            @classmethod
            def __declare_first__(cls):
                canary.declare_first__(cls)

            @classmethod
            def __declare_last__(cls):
                canary.declare_last__(cls)

        configure_mappers()

        eq_(
            canary.mock_calls,
            [
                mock.call.declare_first__(MyOtherModel),
                mock.call.declare_last__(MyOtherModel)
            ]
        )

    def test_mapper_args_declared_attr(self):

        class ComputedMapperArgs:

            @declared_attr
            def __mapper_args__(cls):
                if cls.__name__ == 'Person':
                    return {'polymorphic_on': cls.discriminator}
                else:
                    return {'polymorphic_identity': cls.__name__}

        class Person(Base, ComputedMapperArgs):
            __tablename__ = 'people'
            id = Column(Integer, primary_key=True)
            discriminator = Column('type', String(50))

        class Engineer(Person):
            pass

        configure_mappers()
        assert class_mapper(Person).polymorphic_on \
            is Person.__table__.c.type
        eq_(class_mapper(Engineer).polymorphic_identity, 'Engineer')

    def test_mapper_args_declared_attr_two(self):

        # same as test_mapper_args_declared_attr, but we repeat
        # ComputedMapperArgs on both classes for no apparent reason.

        class ComputedMapperArgs:

            @declared_attr
            def __mapper_args__(cls):
                if cls.__name__ == 'Person':
                    return {'polymorphic_on': cls.discriminator}
                else:
                    return {'polymorphic_identity': cls.__name__}

        class Person(Base, ComputedMapperArgs):

            __tablename__ = 'people'
            id = Column(Integer, primary_key=True)
            discriminator = Column('type', String(50))

        class Engineer(Person, ComputedMapperArgs):
            pass

        configure_mappers()
        assert class_mapper(Person).polymorphic_on \
            is Person.__table__.c.type
        eq_(class_mapper(Engineer).polymorphic_identity, 'Engineer')

    def test_table_args_composite(self):

        class MyMixin1:

            __table_args__ = {'info': {'baz': 'bob'}}

        class MyMixin2:

            __table_args__ = {'info': {'foo': 'bar'}}

        class MyModel(Base, MyMixin1, MyMixin2):

            __tablename__ = 'test'

            @declared_attr
            def __table_args__(self):
                info = {}
                args = dict(info=info)
                info.update(MyMixin1.__table_args__['info'])
                info.update(MyMixin2.__table_args__['info'])
                return args
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__table__.info, {'foo': 'bar', 'baz': 'bob'})

    def test_mapper_args_inherited(self):

        class MyMixin:

            __mapper_args__ = {'always_refresh': True}

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__mapper__.always_refresh, True)

    def test_mapper_args_inherited_descriptor(self):

        class MyMixin:

            @declared_attr
            def __mapper_args__(cls):

                # tenuous, but illustrates the problem!

                if cls.__name__ == 'MyModel':
                    return dict(always_refresh=True)
                else:
                    return dict(always_refresh=False)

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__mapper__.always_refresh, True)

    def test_mapper_args_polymorphic_on_inherited(self):

        class MyMixin:

            type_ = Column(String(50))
            __mapper_args__ = {'polymorphic_on': type_}

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        col = MyModel.__mapper__.polymorphic_on
        eq_(col.name, 'type_')
        assert col.table is not None

    def test_mapper_args_overridden(self):

        class MyMixin:

            __mapper_args__ = dict(always_refresh=True)

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            __mapper_args__ = dict(always_refresh=False)
            id = Column(Integer, primary_key=True)

        eq_(MyModel.__mapper__.always_refresh, False)

    def test_mapper_args_composite(self):

        class MyMixin1:

            type_ = Column(String(50))
            __mapper_args__ = {'polymorphic_on': type_}

        class MyMixin2:

            __mapper_args__ = {'always_refresh': True}

        class MyModel(Base, MyMixin1, MyMixin2):

            __tablename__ = 'test'

            @declared_attr
            def __mapper_args__(cls):
                args = {}
                args.update(MyMixin1.__mapper_args__)
                args.update(MyMixin2.__mapper_args__)
                if cls.__name__ != 'MyModel':
                    args.pop('polymorphic_on')
                    args['polymorphic_identity'] = cls.__name__

                return args
            id = Column(Integer, primary_key=True)

        class MySubModel(MyModel):
            pass

        eq_(
            MyModel.__mapper__.polymorphic_on.name,
            'type_'
        )
        assert MyModel.__mapper__.polymorphic_on.table is not None
        eq_(MyModel.__mapper__.always_refresh, True)
        eq_(MySubModel.__mapper__.always_refresh, True)
        eq_(MySubModel.__mapper__.polymorphic_identity, 'MySubModel')

    def test_mapper_args_property(self):
        class MyModel(Base):

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()

            @declared_attr
            def __table_args__(cls):
                return {'mysql_engine': 'InnoDB'}

            @declared_attr
            def __mapper_args__(cls):
                args = {}
                args['polymorphic_identity'] = cls.__name__
                return args
            id = Column(Integer, primary_key=True)

        class MySubModel(MyModel):
            id = Column(Integer, ForeignKey('mymodel.id'), primary_key=True)

        class MySubModel2(MyModel):
            __tablename__ = 'sometable'
            id = Column(Integer, ForeignKey('mymodel.id'), primary_key=True)

        eq_(MyModel.__mapper__.polymorphic_identity, 'MyModel')
        eq_(MySubModel.__mapper__.polymorphic_identity, 'MySubModel')
        eq_(MyModel.__table__.kwargs['mysql_engine'], 'InnoDB')
        eq_(MySubModel.__table__.kwargs['mysql_engine'], 'InnoDB')
        eq_(MySubModel2.__table__.kwargs['mysql_engine'], 'InnoDB')
        eq_(MyModel.__table__.name, 'mymodel')
        eq_(MySubModel.__table__.name, 'mysubmodel')

    def test_mapper_args_custom_base(self):
        """test the @declared_attr approach from a custom base."""

        class Base(object):

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()

            @declared_attr
            def __table_args__(cls):
                return {'mysql_engine': 'InnoDB'}

            @declared_attr
            def id(self):
                return Column(Integer, primary_key=True)

        Base = decl.declarative_base(cls=Base)

        class MyClass(Base):
            pass

        class MyOtherClass(Base):
            pass

        eq_(MyClass.__table__.kwargs['mysql_engine'], 'InnoDB')
        eq_(MyClass.__table__.name, 'myclass')
        eq_(MyOtherClass.__table__.name, 'myotherclass')
        assert MyClass.__table__.c.id.table is MyClass.__table__
        assert MyOtherClass.__table__.c.id.table is MyOtherClass.__table__

    def test_single_table_no_propagation(self):

        class IdColumn:

            id = Column(Integer, primary_key=True)

        class Generic(Base, IdColumn):

            __tablename__ = 'base'
            discriminator = Column('type', String(50))
            __mapper_args__ = dict(polymorphic_on=discriminator)
            value = Column(Integer())

        class Specific(Generic):

            __mapper_args__ = dict(polymorphic_identity='specific')

        assert Specific.__table__ is Generic.__table__
        eq_(list(Generic.__table__.c.keys()), ['id', 'type', 'value'])
        assert class_mapper(Specific).polymorphic_on \
            is Generic.__table__.c.type
        eq_(class_mapper(Specific).polymorphic_identity, 'specific')

    def test_joined_table_propagation(self):

        class CommonMixin:

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()
            __table_args__ = {'mysql_engine': 'InnoDB'}
            timestamp = Column(Integer)
            id = Column(Integer, primary_key=True)

        class Generic(Base, CommonMixin):

            discriminator = Column('python_type', String(50))
            __mapper_args__ = dict(polymorphic_on=discriminator)

        class Specific(Generic):

            __mapper_args__ = dict(polymorphic_identity='specific')
            id = Column(Integer, ForeignKey('generic.id'),
                        primary_key=True)

        eq_(Generic.__table__.name, 'generic')
        eq_(Specific.__table__.name, 'specific')
        eq_(list(Generic.__table__.c.keys()), ['timestamp', 'id',
                                               'python_type'])
        eq_(list(Specific.__table__.c.keys()), ['id'])
        eq_(Generic.__table__.kwargs, {'mysql_engine': 'InnoDB'})
        eq_(Specific.__table__.kwargs, {'mysql_engine': 'InnoDB'})

    def test_some_propagation(self):

        class CommonMixin:

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()
            __table_args__ = {'mysql_engine': 'InnoDB'}
            timestamp = Column(Integer)

        class BaseType(Base, CommonMixin):

            discriminator = Column('type', String(50))
            __mapper_args__ = dict(polymorphic_on=discriminator)
            id = Column(Integer, primary_key=True)
            value = Column(Integer())

        class Single(BaseType):

            __tablename__ = None
            __mapper_args__ = dict(polymorphic_identity='type1')

        class Joined(BaseType):

            __mapper_args__ = dict(polymorphic_identity='type2')
            id = Column(Integer, ForeignKey('basetype.id'),
                        primary_key=True)

        eq_(BaseType.__table__.name, 'basetype')
        eq_(list(BaseType.__table__.c.keys()), ['timestamp', 'type', 'id',
                                                'value'])
        eq_(BaseType.__table__.kwargs, {'mysql_engine': 'InnoDB'})
        assert Single.__table__ is BaseType.__table__
        eq_(Joined.__table__.name, 'joined')
        eq_(list(Joined.__table__.c.keys()), ['id'])
        eq_(Joined.__table__.kwargs, {'mysql_engine': 'InnoDB'})

    def test_col_copy_vs_declared_attr_joined_propagation(self):
        class Mixin(object):
            a = Column(Integer)

            @declared_attr
            def b(cls):
                return Column(Integer)

        class A(Mixin, Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)

        class B(A):
            __tablename__ = 'b'
            id = Column(Integer, ForeignKey('a.id'), primary_key=True)

        assert 'a' in A.__table__.c
        assert 'b' in A.__table__.c
        assert 'a' not in B.__table__.c
        assert 'b' not in B.__table__.c

    def test_col_copy_vs_declared_attr_joined_propagation_newname(self):
        class Mixin(object):
            a = Column('a1', Integer)

            @declared_attr
            def b(cls):
                return Column('b1', Integer)

        class A(Mixin, Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)

        class B(A):
            __tablename__ = 'b'
            id = Column(Integer, ForeignKey('a.id'), primary_key=True)

        assert 'a1' in A.__table__.c
        assert 'b1' in A.__table__.c
        assert 'a1' not in B.__table__.c
        assert 'b1' not in B.__table__.c

    def test_col_copy_vs_declared_attr_single_propagation(self):
        class Mixin(object):
            a = Column(Integer)

            @declared_attr
            def b(cls):
                return Column(Integer)

        class A(Mixin, Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)

        class B(A):
            pass

        assert 'a' in A.__table__.c
        assert 'b' in A.__table__.c

    def test_non_propagating_mixin(self):

        class NoJoinedTableNameMixin:

            @declared_attr
            def __tablename__(cls):
                if decl.has_inherited_table(cls):
                    return None
                return cls.__name__.lower()

        class BaseType(Base, NoJoinedTableNameMixin):

            discriminator = Column('type', String(50))
            __mapper_args__ = dict(polymorphic_on=discriminator)
            id = Column(Integer, primary_key=True)
            value = Column(Integer())

        class Specific(BaseType):

            __mapper_args__ = dict(polymorphic_identity='specific')

        eq_(BaseType.__table__.name, 'basetype')
        eq_(list(BaseType.__table__.c.keys()), ['type', 'id', 'value'])
        assert Specific.__table__ is BaseType.__table__
        assert class_mapper(Specific).polymorphic_on \
            is BaseType.__table__.c.type
        eq_(class_mapper(Specific).polymorphic_identity, 'specific')

    def test_non_propagating_mixin_used_for_joined(self):

        class TableNameMixin:

            @declared_attr
            def __tablename__(cls):
                if decl.has_inherited_table(cls) and TableNameMixin \
                        not in cls.__bases__:
                    return None
                return cls.__name__.lower()

        class BaseType(Base, TableNameMixin):

            discriminator = Column('type', String(50))
            __mapper_args__ = dict(polymorphic_on=discriminator)
            id = Column(Integer, primary_key=True)
            value = Column(Integer())

        class Specific(BaseType, TableNameMixin):

            __mapper_args__ = dict(polymorphic_identity='specific')
            id = Column(Integer, ForeignKey('basetype.id'),
                        primary_key=True)

        eq_(BaseType.__table__.name, 'basetype')
        eq_(list(BaseType.__table__.c.keys()), ['type', 'id', 'value'])
        eq_(Specific.__table__.name, 'specific')
        eq_(list(Specific.__table__.c.keys()), ['id'])

    def test_single_back_propagate(self):

        class ColumnMixin:

            timestamp = Column(Integer)

        class BaseType(Base):

            __tablename__ = 'foo'
            discriminator = Column('type', String(50))
            __mapper_args__ = dict(polymorphic_on=discriminator)
            id = Column(Integer, primary_key=True)

        class Specific(BaseType, ColumnMixin):

            __mapper_args__ = dict(polymorphic_identity='specific')

        eq_(list(BaseType.__table__.c.keys()), ['type', 'id', 'timestamp'])

    def test_table_in_model_and_same_column_in_mixin(self):

        class ColumnMixin:

            data = Column(Integer)

        class Model(Base, ColumnMixin):

            __table__ = Table('foo', Base.metadata,
                              Column('data', Integer),
                              Column('id', Integer, primary_key=True))

        model_col = Model.__table__.c.data
        mixin_col = ColumnMixin.data
        assert model_col is not mixin_col
        eq_(model_col.name, 'data')
        assert model_col.type.__class__ is mixin_col.type.__class__

    def test_table_in_model_and_different_named_column_in_mixin(self):

        class ColumnMixin:
            tada = Column(Integer)

        def go():

            class Model(Base, ColumnMixin):

                __table__ = Table('foo', Base.metadata,
                                  Column('data', Integer),
                                  Column('id', Integer, primary_key=True))
                foo = relationship("Dest")

        assert_raises_message(sa.exc.ArgumentError,
                              "Can't add additional column 'tada' when "
                              "specifying __table__", go)

    def test_table_in_model_and_different_named_alt_key_column_in_mixin(self):

        # here, the __table__ has a column 'tada'.  We disallow
        # the add of the 'foobar' column, even though it's
        # keyed to 'tada'.

        class ColumnMixin:
            tada = Column('foobar', Integer)

        def go():

            class Model(Base, ColumnMixin):

                __table__ = Table('foo', Base.metadata,
                                  Column('data', Integer),
                                  Column('tada', Integer),
                                  Column('id', Integer, primary_key=True))
                foo = relationship("Dest")

        assert_raises_message(sa.exc.ArgumentError,
                              "Can't add additional column 'foobar' when "
                              "specifying __table__", go)

    def test_table_in_model_overrides_different_typed_column_in_mixin(self):

        class ColumnMixin:

            data = Column(String)

        class Model(Base, ColumnMixin):

            __table__ = Table('foo', Base.metadata,
                              Column('data', Integer),
                              Column('id', Integer, primary_key=True))

        model_col = Model.__table__.c.data
        mixin_col = ColumnMixin.data
        assert model_col is not mixin_col
        eq_(model_col.name, 'data')
        assert model_col.type.__class__ is Integer

    def test_mixin_column_ordering(self):

        class Foo(object):

            col1 = Column(Integer)
            col3 = Column(Integer)

        class Bar(object):

            col2 = Column(Integer)
            col4 = Column(Integer)

        class Model(Base, Foo, Bar):

            id = Column(Integer, primary_key=True)
            __tablename__ = 'model'

        eq_(list(Model.__table__.c.keys()), ['col1', 'col3', 'col2', 'col4',
                                             'id'])

    def test_honor_class_mro_one(self):
        class HasXMixin(object):

            @declared_attr
            def x(self):
                return Column(Integer)

        class Parent(HasXMixin, Base):
            __tablename__ = 'parent'
            id = Column(Integer, primary_key=True)

        class Child(Parent):
            __tablename__ = 'child'
            id = Column(Integer, ForeignKey('parent.id'), primary_key=True)

        assert "x" not in Child.__table__.c

    def test_honor_class_mro_two(self):
        class HasXMixin(object):

            @declared_attr
            def x(self):
                return Column(Integer)

        class Parent(HasXMixin, Base):
            __tablename__ = 'parent'
            id = Column(Integer, primary_key=True)

            def x(self):
                return "hi"

        class C(Parent):
            __tablename__ = 'c'
            id = Column(Integer, ForeignKey('parent.id'), primary_key=True)

        assert C().x() == 'hi'

    def test_arbitrary_attrs_one(self):
        class HasMixin(object):

            @declared_attr
            def some_attr(cls):
                return cls.__name__ + "SOME ATTR"

        class Mapped(HasMixin, Base):
            __tablename__ = 't'
            id = Column(Integer, primary_key=True)

        eq_(Mapped.some_attr, "MappedSOME ATTR")
        eq_(Mapped.__dict__['some_attr'], "MappedSOME ATTR")

    def test_arbitrary_attrs_two(self):
        from sqlalchemy.ext.associationproxy import association_proxy

        class FilterA(Base):
            __tablename__ = 'filter_a'
            id = Column(Integer(), primary_key=True)
            parent_id = Column(Integer(),
                               ForeignKey('type_a.id'))
            filter = Column(String())

            def __init__(self, filter_, **kw):
                self.filter = filter_

        class FilterB(Base):
            __tablename__ = 'filter_b'
            id = Column(Integer(), primary_key=True)
            parent_id = Column(Integer(),
                               ForeignKey('type_b.id'))
            filter = Column(String())

            def __init__(self, filter_, **kw):
                self.filter = filter_

        class FilterMixin(object):

            @declared_attr
            def _filters(cls):
                return relationship(cls.filter_class,
                                    cascade='all,delete,delete-orphan')

            @declared_attr
            def filters(cls):
                return association_proxy('_filters', 'filter')

        class TypeA(Base, FilterMixin):
            __tablename__ = 'type_a'
            filter_class = FilterA
            id = Column(Integer(), primary_key=True)

        class TypeB(Base, FilterMixin):
            __tablename__ = 'type_b'
            filter_class = FilterB
            id = Column(Integer(), primary_key=True)

        TypeA(filters=['foo'])
        TypeB(filters=['foo'])


class DeclarativeMixinPropertyTest(DeclarativeTestBase):

    def test_column_property(self):

        class MyMixin(object):

            @declared_attr
            def prop_hoho(cls):
                return column_property(Column('prop', String(50)))

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

        class MyOtherModel(Base, MyMixin):

            __tablename__ = 'othertest'
            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

        assert MyModel.__table__.c.prop is not None
        assert MyOtherModel.__table__.c.prop is not None
        assert MyModel.__table__.c.prop \
            is not MyOtherModel.__table__.c.prop
        assert MyModel.prop_hoho.property.columns \
            == [MyModel.__table__.c.prop]
        assert MyOtherModel.prop_hoho.property.columns \
            == [MyOtherModel.__table__.c.prop]
        assert MyModel.prop_hoho.property \
            is not MyOtherModel.prop_hoho.property
        Base.metadata.create_all()
        sess = create_session()
        m1, m2 = MyModel(prop_hoho='foo'), MyOtherModel(prop_hoho='bar')
        sess.add_all([m1, m2])
        sess.flush()
        eq_(sess.query(MyModel).filter(MyModel.prop_hoho == 'foo'
                                       ).one(), m1)
        eq_(sess.query(MyOtherModel).filter(MyOtherModel.prop_hoho
                                            == 'bar').one(), m2)

    def test_doc(self):
        """test documentation transfer.

        the documentation situation with @declared_attr is problematic.
        at least see if mapped subclasses get the doc.

        """

        class MyMixin(object):

            @declared_attr
            def type_(cls):
                """this is a document."""

                return Column(String(50))

            @declared_attr
            def t2(cls):
                """this is another document."""

                return column_property(Column(String(50)))

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        configure_mappers()
        eq_(MyModel.type_.__doc__, """this is a document.""")
        eq_(MyModel.t2.__doc__, """this is another document.""")

    def test_column_in_mapper_args(self):

        class MyMixin(object):

            @declared_attr
            def type_(cls):
                return Column(String(50))
            __mapper_args__ = {'polymorphic_on': type_}

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True)

        configure_mappers()
        col = MyModel.__mapper__.polymorphic_on
        eq_(col.name, 'type_')
        assert col.table is not None

    def test_column_in_mapper_args_used_multiple_times(self):

        class MyMixin(object):

            version_id = Column(Integer)
            __mapper_args__ = {'version_id_col': version_id}

        class ModelOne(Base, MyMixin):

            __tablename__ = 'm1'
            id = Column(Integer, primary_key=True)

        class ModelTwo(Base, MyMixin):

            __tablename__ = 'm2'
            id = Column(Integer, primary_key=True)

        is_(
            ModelOne.__mapper__.version_id_col,
            ModelOne.__table__.c.version_id
        )
        is_(
            ModelTwo.__mapper__.version_id_col,
            ModelTwo.__table__.c.version_id
        )

    def test_deferred(self):

        class MyMixin(object):

            @declared_attr
            def data(cls):
                return deferred(Column('data', String(50)))

        class MyModel(Base, MyMixin):

            __tablename__ = 'test'
            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

        Base.metadata.create_all()
        sess = create_session()
        sess.add_all([MyModel(data='d1'), MyModel(data='d2')])
        sess.flush()
        sess.expunge_all()
        d1, d2 = sess.query(MyModel).order_by(MyModel.data)
        assert 'data' not in d1.__dict__
        assert d1.data == 'd1'
        assert 'data' in d1.__dict__

    def _test_relationship(self, usestring):

        class RefTargetMixin(object):

            @declared_attr
            def target_id(cls):
                return Column('target_id', ForeignKey('target.id'))
            if usestring:

                @declared_attr
                def target(cls):
                    return relationship('Target',
                                        primaryjoin='Target.id==%s.target_id'
                                        % cls.__name__)
            else:

                @declared_attr
                def target(cls):
                    return relationship('Target')

        class Foo(Base, RefTargetMixin):

            __tablename__ = 'foo'
            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

        class Bar(Base, RefTargetMixin):

            __tablename__ = 'bar'
            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

        class Target(Base):

            __tablename__ = 'target'
            id = Column(Integer, primary_key=True,
                        test_needs_autoincrement=True)

        Base.metadata.create_all()
        sess = create_session()
        t1, t2 = Target(), Target()
        f1, f2, b1 = Foo(target=t1), Foo(target=t2), Bar(target=t1)
        sess.add_all([f1, f2, b1])
        sess.flush()
        eq_(sess.query(Foo).filter(Foo.target == t2).one(), f2)
        eq_(sess.query(Bar).filter(Bar.target == t2).first(), None)
        sess.expire_all()
        eq_(f1.target, t1)

    def test_relationship(self):
        self._test_relationship(False)

    def test_relationship_primryjoin(self):
        self._test_relationship(True)


class DeclaredAttrTest(DeclarativeTestBase, testing.AssertsCompiledSQL):
    __dialect__ = 'default'

    def test_singleton_behavior_within_decl(self):
        counter = mock.Mock()

        class Mixin(object):
            @declared_attr
            def my_prop(cls):
                counter(cls)
                return Column('x', Integer)

        class A(Base, Mixin):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)

            @declared_attr
            def my_other_prop(cls):
                return column_property(cls.my_prop + 5)

        eq_(counter.mock_calls, [mock.call(A)])

        class B(Base, Mixin):
            __tablename__ = 'b'
            id = Column(Integer, primary_key=True)

            @declared_attr
            def my_other_prop(cls):
                return column_property(cls.my_prop + 5)

        eq_(
            counter.mock_calls,
            [mock.call(A), mock.call(B)])

        # this is why we need singleton-per-class behavior.   We get
        # an un-bound "x" column otherwise here, because my_prop() generates
        # multiple columns.
        a_col = A.my_other_prop.__clause_element__().element.left
        b_col = B.my_other_prop.__clause_element__().element.left
        is_(a_col.table, A.__table__)
        is_(b_col.table, B.__table__)
        is_(a_col, A.__table__.c.x)
        is_(b_col, B.__table__.c.x)

        s = Session()
        self.assert_compile(
            s.query(A),
            "SELECT a.x AS a_x, a.x + :x_1 AS anon_1, a.id AS a_id FROM a"
        )
        self.assert_compile(
            s.query(B),
            "SELECT b.x AS b_x, b.x + :x_1 AS anon_1, b.id AS b_id FROM b"
        )

    @testing.requires.predictable_gc
    def test_singleton_gc(self):
        counter = mock.Mock()

        class Mixin(object):
            @declared_attr
            def my_prop(cls):
                counter(cls.__name__)
                return Column('x', Integer)

        class A(Base, Mixin):
            __tablename__ = 'b'
            id = Column(Integer, primary_key=True)

            @declared_attr
            def my_other_prop(cls):
                return column_property(cls.my_prop + 5)

        eq_(counter.mock_calls, [mock.call("A")])
        del A
        gc_collect()
        assert "A" not in Base._decl_class_registry

    def test_can_we_access_the_mixin_straight(self):
        class Mixin(object):
            @declared_attr
            def my_prop(cls):
                return Column('x', Integer)

        assert_raises_message(
            sa.exc.SAWarning,
            "Unmanaged access of declarative attribute my_prop "
            "from non-mapped class Mixin",
            getattr, Mixin, "my_prop"
        )

    def test_non_decl_access(self):
        counter = mock.Mock()

        class Mixin(object):
            @declared_attr
            def __tablename__(cls):
                counter(cls)
                return "foo"

        class Foo(Mixin, Base):
            id = Column(Integer, primary_key=True)

            @declared_attr
            def x(cls):
                cls.__tablename__

            @declared_attr
            def y(cls):
                cls.__tablename__

        eq_(
            counter.mock_calls,
            [mock.call(Foo)]
        )

        eq_(Foo.__tablename__, 'foo')
        eq_(Foo.__tablename__, 'foo')

        eq_(
            counter.mock_calls,
            [mock.call(Foo), mock.call(Foo), mock.call(Foo)]
        )

    def test_property_noncascade(self):
        counter = mock.Mock()

        class Mixin(object):
            @declared_attr
            def my_prop(cls):
                counter(cls)
                return column_property(cls.x + 2)

        class A(Base, Mixin):
            __tablename__ = 'a'

            id = Column(Integer, primary_key=True)
            x = Column(Integer)

        class B(A):
            pass

        eq_(counter.mock_calls, [mock.call(A)])

    def test_property_cascade(self):
        counter = mock.Mock()

        class Mixin(object):
            @declared_attr.cascading
            def my_prop(cls):
                counter(cls)
                return column_property(cls.x + 2)

        class A(Base, Mixin):
            __tablename__ = 'a'

            id = Column(Integer, primary_key=True)
            x = Column(Integer)

        class B(A):
            pass

        eq_(counter.mock_calls, [mock.call(A), mock.call(B)])

    def test_col_prop_attrs_associated_w_class_for_mapper_args(self):
        from sqlalchemy import Column
        import collections

        asserted = collections.defaultdict(set)

        class Mixin(object):
            @declared_attr.cascading
            def my_attr(cls):
                if decl.has_inherited_table(cls):
                    id = Column(ForeignKey('a.my_attr'), primary_key=True)
                    asserted['b'].add(id)
                else:
                    id = Column(Integer, primary_key=True)
                    asserted['a'].add(id)
                return id

        class A(Base, Mixin):
            __tablename__ = 'a'

            @declared_attr
            def __mapper_args__(cls):
                asserted['a'].add(cls.my_attr)
                return {}

        # here:
        # 1. A is mapped.  so A.my_attr is now the InstrumentedAttribute.
        # 2. B wants to call my_attr also.  Due to .cascading, it has been
        # invoked specific to B, and is present in the dict_ that will
        # be used when we map the class.  But except for the
        # special setattr() we do in _scan_attributes() in this case, would
        # otherwise not been set on the class as anything from this call;
        # the usual mechanics of calling it from the descriptor also do not
        # work because A is fully mapped and because A set it up, is currently
        # that non-expected InstrumentedAttribute and replaces the
        # descriptor from being invoked.

        class B(A):
            __tablename__ = 'b'

            @declared_attr
            def __mapper_args__(cls):
                asserted['b'].add(cls.my_attr)
                return {}

        eq_(
            asserted,
            {
                'a': set([A.my_attr.property.columns[0]]),
                'b': set([B.my_attr.property.columns[0]])
            }
        )

    def test_column_pre_map(self):
        counter = mock.Mock()

        class Mixin(object):
            @declared_attr
            def my_col(cls):
                counter(cls)
                assert not orm_base._mapper_or_none(cls)
                return Column('x', Integer)

        class A(Base, Mixin):
            __tablename__ = 'a'

            id = Column(Integer, primary_key=True)

        eq_(counter.mock_calls, [mock.call(A)])

    def test_mixin_attr_refers_to_column_copies(self):
        # this @declared_attr can refer to User.id
        # freely because we now do the "copy column" operation
        # before the declared_attr is invoked.

        counter = mock.Mock()

        class HasAddressCount(object):
            id = Column(Integer, primary_key=True)

            @declared_attr
            def address_count(cls):
                counter(cls.id)
                return column_property(
                    select([func.count(Address.id)]).
                    where(Address.user_id == cls.id).
                    as_scalar()
                )

        class Address(Base):
            __tablename__ = 'address'
            id = Column(Integer, primary_key=True)
            user_id = Column(ForeignKey('user.id'))

        class User(Base, HasAddressCount):
            __tablename__ = 'user'

        eq_(
            counter.mock_calls,
            [mock.call(User.id)]
        )

        sess = Session()
        self.assert_compile(
            sess.query(User).having(User.address_count > 5),
            'SELECT (SELECT count(address.id) AS '
            'count_1 FROM address WHERE address.user_id = "user".id) '
            'AS anon_1, "user".id AS user_id FROM "user" '
            'HAVING (SELECT count(address.id) AS '
            'count_1 FROM address WHERE address.user_id = "user".id) '
            '> :param_1'
        )


class AbstractTest(DeclarativeTestBase):

    def test_abstract_boolean(self):

        class A(Base):
            __abstract__ = True
            __tablename__ = 'x'
            id = Column(Integer, primary_key=True)

        class B(Base):
            __abstract__ = False
            __tablename__ = 'y'
            id = Column(Integer, primary_key=True)

        class C(Base):
            __abstract__ = False
            __tablename__ = 'z'
            id = Column(Integer, primary_key=True)

        class D(Base):
            __tablename__ = 'q'
            id = Column(Integer, primary_key=True)

        eq_(set(Base.metadata.tables), set(['y', 'z', 'q']))

    def test_middle_abstract_attributes(self):
        # test for [ticket:3219]
        class A(Base):
            __tablename__ = 'a'

            id = Column(Integer, primary_key=True)
            name = Column(String)

        class B(A):
            __abstract__ = True
            data = Column(String)

        class C(B):
            c_value = Column(String)

        eq_(
            sa.inspect(C).attrs.keys(), ['id', 'name', 'data', 'c_value']
        )

    def test_middle_abstract_inherits(self):
        # test for [ticket:3240]

        class A(Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)

        class AAbs(A):
            __abstract__ = True

        class B1(A):
            __tablename__ = 'b1'
            id = Column(ForeignKey('a.id'), primary_key=True)

        class B2(AAbs):
            __tablename__ = 'b2'
            id = Column(ForeignKey('a.id'), primary_key=True)

        assert B1.__mapper__.inherits is A.__mapper__

        assert B2.__mapper__.inherits is A.__mapper__
