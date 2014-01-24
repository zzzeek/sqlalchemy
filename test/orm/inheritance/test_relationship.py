from sqlalchemy.orm import create_session, relationship, mapper, \
    contains_eager, joinedload, subqueryload, subqueryload_all,\
    Session, aliased, with_polymorphic

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.engine import default

from sqlalchemy.testing import AssertsCompiledSQL, fixtures
from sqlalchemy import testing
from sqlalchemy.testing.schema import Table, Column
from sqlalchemy.testing import assert_raises, eq_, is_

class Company(fixtures.ComparableEntity):
    pass
class Person(fixtures.ComparableEntity):
    pass
class Engineer(Person):
    pass
class Manager(Person):
    pass
class Boss(Manager):
    pass
class Machine(fixtures.ComparableEntity):
    pass
class Paperwork(fixtures.ComparableEntity):
    pass

class SelfReferentialTestJoinedToBase(fixtures.MappedTest):

    run_setup_mappers = 'once'

    @classmethod
    def define_tables(cls, metadata):
        Table('people', metadata,
            Column('person_id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('name', String(50)),
            Column('type', String(30)))

        Table('engineers', metadata,
            Column('person_id', Integer,
                ForeignKey('people.person_id'),
                primary_key=True),
            Column('primary_language', String(50)),
            Column('reports_to_id', Integer,
                ForeignKey('people.person_id')))

    @classmethod
    def setup_mappers(cls):
        engineers, people = cls.tables.engineers, cls.tables.people

        mapper(Person, people,
            polymorphic_on=people.c.type,
            polymorphic_identity='person')

        mapper(Engineer, engineers,
            inherits=Person,
            inherit_condition=engineers.c.person_id == people.c.person_id,
            polymorphic_identity='engineer',
            properties={
                'reports_to':relationship(
                    Person,
                    primaryjoin=
                        people.c.person_id == engineers.c.reports_to_id)})

    def test_has(self):
        p1 = Person(name='dogbert')
        e1 = Engineer(name='dilbert', primary_language='java', reports_to=p1)
        sess = create_session()
        sess.add(p1)
        sess.add(e1)
        sess.flush()
        sess.expunge_all()
        eq_(sess.query(Engineer)
                .filter(Engineer.reports_to.has(Person.name == 'dogbert'))
                .first(),
            Engineer(name='dilbert'))

    def test_oftype_aliases_in_exists(self):
        e1 = Engineer(name='dilbert', primary_language='java')
        e2 = Engineer(name='wally', primary_language='c++', reports_to=e1)
        sess = create_session()
        sess.add_all([e1, e2])
        sess.flush()
        eq_(sess.query(Engineer)
                .filter(Engineer.reports_to
                    .of_type(Engineer)
                    .has(Engineer.name == 'dilbert'))
                .first(),
            e2)

    def test_join(self):
        p1 = Person(name='dogbert')
        e1 = Engineer(name='dilbert', primary_language='java', reports_to=p1)
        sess = create_session()
        sess.add(p1)
        sess.add(e1)
        sess.flush()
        sess.expunge_all()
        eq_(sess.query(Engineer)
                .join('reports_to', aliased=True)
                .filter(Person.name == 'dogbert').first(),
            Engineer(name='dilbert'))

class SelfReferentialJ2JTest(fixtures.MappedTest):

    run_setup_mappers = 'once'

    @classmethod
    def define_tables(cls, metadata):
        people = Table('people', metadata,
            Column('person_id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('name', String(50)),
            Column('type', String(30)))

        engineers = Table('engineers', metadata,
            Column('person_id', Integer,
                ForeignKey('people.person_id'),
                primary_key=True),
            Column('primary_language', String(50)),
            Column('reports_to_id', Integer,
                ForeignKey('managers.person_id'))
          )

        managers = Table('managers', metadata,
            Column('person_id', Integer, ForeignKey('people.person_id'),
                primary_key=True),
        )

    @classmethod
    def setup_mappers(cls):
        engineers = cls.tables.engineers
        managers = cls.tables.managers
        people = cls.tables.people

        mapper(Person, people,
            polymorphic_on=people.c.type,
            polymorphic_identity='person')

        mapper(Manager, managers,
            inherits=Person,
            polymorphic_identity='manager')

        mapper(Engineer, engineers,
            inherits=Person,
            polymorphic_identity='engineer',
            properties={
                'reports_to':relationship(
                    Manager,
                    primaryjoin=
                        managers.c.person_id == engineers.c.reports_to_id,
                    backref='engineers')})


    def test_has(self):
        m1 = Manager(name='dogbert')
        e1 = Engineer(name='dilbert', primary_language='java', reports_to=m1)
        sess = create_session()
        sess.add(m1)
        sess.add(e1)
        sess.flush()
        sess.expunge_all()

        eq_(sess.query(Engineer)
                .filter(Engineer.reports_to.has(Manager.name == 'dogbert'))
                .first(),
            Engineer(name='dilbert'))

    def test_join(self):
        m1 = Manager(name='dogbert')
        e1 = Engineer(name='dilbert', primary_language='java', reports_to=m1)
        sess = create_session()
        sess.add(m1)
        sess.add(e1)
        sess.flush()
        sess.expunge_all()

        eq_(sess.query(Engineer)
                .join('reports_to', aliased=True)
                .filter(Manager.name == 'dogbert').first(),
            Engineer(name='dilbert'))

    def test_filter_aliasing(self):
        m1 = Manager(name='dogbert')
        m2 = Manager(name='foo')
        e1 = Engineer(name='wally', primary_language='java', reports_to=m1)
        e2 = Engineer(name='dilbert', primary_language='c++', reports_to=m2)
        e3 = Engineer(name='etc', primary_language='c++')

        sess = create_session()
        sess.add_all([m1, m2, e1, e2, e3])
        sess.flush()
        sess.expunge_all()

        # filter aliasing applied to Engineer doesn't whack Manager
        eq_(sess.query(Manager)
                .join(Manager.engineers)
                .filter(Manager.name == 'dogbert').all(),
            [m1])

        eq_(sess.query(Manager)
                .join(Manager.engineers)
                .filter(Engineer.name == 'dilbert').all(),
            [m2])

        eq_(sess.query(Manager, Engineer)
                .join(Manager.engineers)
                .order_by(Manager.name.desc()).all(),
            [(m2, e2), (m1, e1)])

    def test_relationship_compare(self):
        m1 = Manager(name='dogbert')
        m2 = Manager(name='foo')
        e1 = Engineer(name='dilbert', primary_language='java', reports_to=m1)
        e2 = Engineer(name='wally', primary_language='c++', reports_to=m2)
        e3 = Engineer(name='etc', primary_language='c++')

        sess = create_session()
        sess.add(m1)
        sess.add(m2)
        sess.add(e1)
        sess.add(e2)
        sess.add(e3)
        sess.flush()
        sess.expunge_all()

        eq_(sess.query(Manager)
                .join(Manager.engineers)
                .filter(Engineer.reports_to == None).all(),
            [])

        eq_(sess.query(Manager)
                .join(Manager.engineers)
                .filter(Engineer.reports_to == m1).all(),
            [m1])

class SelfReferentialJ2JSelfTest(fixtures.MappedTest):

    run_setup_mappers = 'once'

    @classmethod
    def define_tables(cls, metadata):
        people = Table('people', metadata,
            Column('person_id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('name', String(50)),
            Column('type', String(30)))

        engineers = Table('engineers', metadata,
            Column('person_id', Integer,
                ForeignKey('people.person_id'),
                primary_key=True),
            Column('reports_to_id', Integer,
                ForeignKey('engineers.person_id')))

    @classmethod
    def setup_mappers(cls):
        engineers = cls.tables.engineers
        people = cls.tables.people

        mapper(Person, people,
            polymorphic_on=people.c.type,
            polymorphic_identity='person')

        mapper(Engineer, engineers,
            inherits=Person,
            polymorphic_identity='engineer',
            properties={
                'reports_to':relationship(
                    Engineer,
                    primaryjoin=
                        engineers.c.person_id == engineers.c.reports_to_id,
                    backref='engineers',
                    remote_side=engineers.c.person_id)})

    def _two_obj_fixture(self):
        e1 = Engineer(name='wally')
        e2 = Engineer(name='dilbert', reports_to=e1)
        sess = Session()
        sess.add_all([e1, e2])
        sess.commit()
        return sess

    def _five_obj_fixture(self):
        sess = Session()
        e1, e2, e3, e4, e5 = [
            Engineer(name='e%d' % (i + 1)) for i in range(5)
        ]
        e3.reports_to = e1
        e4.reports_to = e2
        sess.add_all([e1, e2, e3, e4, e5])
        sess.commit()
        return sess

    def test_has(self):
        sess = self._two_obj_fixture()
        eq_(sess.query(Engineer)
                .filter(Engineer.reports_to.has(Engineer.name == 'wally'))
                .first(),
            Engineer(name='dilbert'))

    def test_join_explicit_alias(self):
        sess = self._five_obj_fixture()
        ea = aliased(Engineer)
        eq_(sess.query(Engineer)
                .join(ea, Engineer.engineers)
                .filter(Engineer.name == 'e1').all(),
            [Engineer(name='e1')])

    def test_join_aliased_flag_one(self):
        sess = self._two_obj_fixture()
        eq_(sess.query(Engineer)
                .join('reports_to', aliased=True)
                .filter(Engineer.name == 'wally').first(),
            Engineer(name='dilbert'))

    def test_join_aliased_flag_two(self):
        sess = self._five_obj_fixture()
        eq_(sess.query(Engineer)
                .join(Engineer.engineers, aliased=True)
                .filter(Engineer.name == 'e4').all(),
            [Engineer(name='e2')])

    def test_relationship_compare(self):
        sess = self._five_obj_fixture()
        e1 = sess.query(Engineer).filter_by(name='e1').one()

        eq_(sess.query(Engineer)
                .join(Engineer.engineers, aliased=True)
                .filter(Engineer.reports_to == None).all(),
            [])

        eq_(sess.query(Engineer)
                .join(Engineer.engineers, aliased=True)
                .filter(Engineer.reports_to == e1).all(),
            [e1])

class M2MFilterTest(fixtures.MappedTest):

    run_setup_mappers = 'once'
    run_inserts = 'once'
    run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        organizations = Table('organizations', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('name', String(50)))

        engineers_to_org = Table('engineers_to_org', metadata,
            Column('org_id', Integer,
                ForeignKey('organizations.id')),
            Column('engineer_id', Integer,
                ForeignKey('engineers.person_id')))

        people = Table('people', metadata,
            Column('person_id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('name', String(50)),
            Column('type', String(30)))

        engineers = Table('engineers', metadata,
            Column('person_id', Integer,
                ForeignKey('people.person_id'),
                primary_key=True),
            Column('primary_language', String(50)))

    @classmethod
    def setup_mappers(cls):
        organizations = cls.tables.organizations
        people = cls.tables.people
        engineers = cls.tables.engineers
        engineers_to_org = cls.tables.engineers_to_org

        class Organization(cls.Comparable):
            pass

        mapper(Organization, organizations,
            properties={
                'engineers':relationship(
                    Engineer,
                    secondary=engineers_to_org,
                    backref='organizations')})

        mapper(Person, people,
            polymorphic_on=people.c.type,
            polymorphic_identity='person')

        mapper(Engineer, engineers,
            inherits=Person,
            polymorphic_identity='engineer')

    @classmethod
    def insert_data(cls):
        Organization = cls.classes.Organization
        e1 = Engineer(name='e1')
        e2 = Engineer(name='e2')
        e3 = Engineer(name='e3')
        e4 = Engineer(name='e4')
        org1 = Organization(name='org1', engineers=[e1, e2])
        org2 = Organization(name='org2', engineers=[e3, e4])
        sess = create_session()
        sess.add(org1)
        sess.add(org2)
        sess.flush()

    def test_not_contains(self):
        Organization = self.classes.Organization
        sess = create_session()
        e1 = sess.query(Person).filter(Engineer.name == 'e1').one()

        eq_(sess.query(Organization)
                .filter(~Organization.engineers
                    .of_type(Engineer)
                    .contains(e1))
                .all(),
            [Organization(name='org2')])

        # this had a bug
        eq_(sess.query(Organization)
                .filter(~Organization.engineers
                    .contains(e1))
                 .all(),
            [Organization(name='org2')])

    def test_any(self):
        sess = create_session()
        Organization = self.classes.Organization

        eq_(sess.query(Organization)
                .filter(Organization.engineers
                    .of_type(Engineer)
                    .any(Engineer.name == 'e1'))
                .all(),
            [Organization(name='org1')])

        eq_(sess.query(Organization)
                .filter(Organization.engineers
                    .any(Engineer.name == 'e1'))
                .all(),
            [Organization(name='org1')])

class SelfReferentialM2MTest(fixtures.MappedTest, AssertsCompiledSQL):
    __dialect__ = "default"

    @classmethod
    def define_tables(cls, metadata):
        Table('secondary', metadata,
            Column('left_id', Integer,
                ForeignKey('parent.id'),
                nullable=False),
            Column('right_id', Integer,
                ForeignKey('parent.id'),
                nullable=False))

        Table('parent', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('cls', String(50)))

        Table('child1', metadata,
            Column('id', Integer,
                ForeignKey('parent.id'),
                primary_key=True))

        Table('child2', metadata,
            Column('id', Integer,
                ForeignKey('parent.id'),
                primary_key=True))

    @classmethod
    def setup_classes(cls):
        class Parent(cls.Basic):
            pass
        class Child1(Parent):
            pass
        class Child2(Parent):
            pass

    @classmethod
    def setup_mappers(cls):
        child1 = cls.tables.child1
        child2 = cls.tables.child2
        Parent = cls.classes.Parent
        parent = cls.tables.parent
        Child1 = cls.classes.Child1
        Child2 = cls.classes.Child2
        secondary = cls.tables.secondary

        mapper(Parent, parent,
            polymorphic_on=parent.c.cls)

        mapper(Child1, child1,
            inherits=Parent,
            polymorphic_identity='child1',
            properties={
                'left_child2':relationship(
                    Child2,
                    secondary=secondary,
                    primaryjoin=parent.c.id == secondary.c.right_id,
                    secondaryjoin=parent.c.id == secondary.c.left_id,
                    uselist=False,
                    backref="right_children")})

        mapper(Child2, child2,
            inherits=Parent,
            polymorphic_identity='child2')

    def test_query_crit(self):
        Child1, Child2 = self.classes.Child1, self.classes.Child2
        sess = create_session()
        c11, c12, c13 = Child1(), Child1(), Child1()
        c21, c22, c23 = Child2(), Child2(), Child2()
        c11.left_child2 = c22
        c12.left_child2 = c22
        c13.left_child2 = c23
        sess.add_all([c11, c12, c13, c21, c22, c23])
        sess.flush()

        # test that the join to Child2 doesn't alias Child1 in the select
        eq_(set(sess.query(Child1).join(Child1.left_child2)),
            set([c11, c12, c13]))

        eq_(set(sess.query(Child1, Child2).join(Child1.left_child2)),
            set([(c11, c22), (c12, c22), (c13, c23)]))

        # test __eq__() on property is annotating correctly
        eq_(set(sess.query(Child2)
                    .join(Child2.right_children)
                    .filter(Child1.left_child2 == c22)),
            set([c22]))

        # test the same again
        self.assert_compile(
            sess.query(Child2)
                .join(Child2.right_children)
                .filter(Child1.left_child2 == c22)
                .with_labels().statement,
            "SELECT child2.id AS child2_id, parent.id AS parent_id, "
            "parent.cls AS parent_cls FROM secondary AS secondary_1, "
            "parent JOIN child2 ON parent.id = child2.id JOIN secondary AS "
            "secondary_2 ON parent.id = secondary_2.left_id JOIN "
            "(parent AS parent_1 JOIN child1 AS child1_1 ON parent_1.id = child1_1.id) "
            "ON parent_1.id = secondary_2.right_id WHERE "
            "parent_1.id = secondary_1.right_id AND :param_1 = "
            "secondary_1.left_id"
        )

    def test_eager_join(self):
        Child1, Child2 = self.classes.Child1, self.classes.Child2
        sess = create_session()
        c1 = Child1()
        c1.left_child2 = Child2()
        sess.add(c1)
        sess.flush()

        # test that the splicing of the join works here, doesn't break in
        # the middle of "parent join child1"
        q = sess.query(Child1).options(joinedload('left_child2'))
        self.assert_compile(q.limit(1).with_labels().statement,
            "SELECT anon_1.child1_id AS anon_1_child1_id, anon_1.parent_id "
            "AS anon_1_parent_id, anon_1.parent_cls AS anon_1_parent_cls, "
            "child2_1.id AS child2_1_id, parent_1.id AS "
            "parent_1_id, parent_1.cls AS parent_1_cls FROM "
            "(SELECT child1.id AS child1_id, parent.id AS parent_id, "
            "parent.cls AS parent_cls "
            "FROM parent JOIN child1 ON parent.id = child1.id "
            "LIMIT :param_1) AS anon_1 LEFT OUTER JOIN "
            "(secondary AS secondary_1 JOIN "
            "(parent AS parent_1 JOIN child2 AS child2_1 "
            "ON parent_1.id = child2_1.id) ON parent_1.id = secondary_1.left_id) "
            "ON anon_1.parent_id = secondary_1.right_id",
            {'param_1':1})

        # another way to check
        assert q.limit(1).with_labels().subquery().count().scalar() == 1
        assert q.first() is c1

    def test_subquery_load(self):
        Child1, Child2 = self.classes.Child1, self.classes.Child2
        sess = create_session()
        c1 = Child1()
        c1.left_child2 = Child2()
        sess.add(c1)
        sess.flush()
        sess.expunge_all()

        query_ = sess.query(Child1).options(subqueryload('left_child2'))
        for row in query_.all():
            assert row.left_child2

class EagerToSubclassTest(fixtures.MappedTest):
    """Test eager loads to subclass mappers"""

    run_setup_classes = 'once'
    run_setup_mappers = 'once'
    run_inserts = 'once'
    run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        Table('parent', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('data', String(10)))

        Table('base', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('type', String(10)),
            Column('related_id', Integer,
                ForeignKey('related.id')))

        Table('sub', metadata,
            Column('id', Integer,
                ForeignKey('base.id'),
                primary_key=True),
            Column('data', String(10)),
            Column('parent_id', Integer,
                ForeignKey('parent.id'),
                nullable=False))

        Table('related', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('data', String(10)))

    @classmethod
    def setup_classes(cls):
        class Parent(cls.Comparable):
            pass
        class Base(cls.Comparable):
            pass
        class Sub(Base):
            pass
        class Related(cls.Comparable):
            pass

    @classmethod
    def setup_mappers(cls):
        sub = cls.tables.sub
        Sub = cls.classes.Sub
        base = cls.tables.base
        Base = cls.classes.Base
        parent = cls.tables.parent
        Parent = cls.classes.Parent
        related = cls.tables.related
        Related = cls.classes.Related

        mapper(Parent, parent,
            properties={'children':relationship(Sub, order_by=sub.c.data)})

        mapper(Base, base,
            polymorphic_on=base.c.type,
            polymorphic_identity='b',
            properties={'related':relationship(Related)})

        mapper(Sub, sub,
            inherits=Base,
            polymorphic_identity='s')

        mapper(Related, related)

    @classmethod
    def insert_data(cls):
        global p1, p2

        Parent = cls.classes.Parent
        Sub = cls.classes.Sub
        Related = cls.classes.Related
        sess = Session()
        r1, r2 = Related(data='r1'), Related(data='r2')
        s1 = Sub(data='s1', related=r1)
        s2 = Sub(data='s2', related=r2)
        s3 = Sub(data='s3')
        s4 = Sub(data='s4', related=r2)
        s5 = Sub(data='s5')
        p1 = Parent(data='p1', children=[s1, s2, s3])
        p2 = Parent(data='p2', children=[s4, s5])
        sess.add(p1)
        sess.add(p2)
        sess.commit()

    def test_joinedload(self):
        Parent = self.classes.Parent
        sess = Session()
        def go():
            eq_(sess.query(Parent)
                    .options(joinedload(Parent.children)).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 1)

    def test_contains_eager(self):
        Parent = self.classes.Parent
        Sub = self.classes.Sub
        sess = Session()
        def go():
            eq_(sess.query(Parent)
                    .join(Parent.children)
                    .options(contains_eager(Parent.children))
                    .order_by(Parent.data, Sub.data).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 1)

    def test_subq_through_related(self):
        Parent = self.classes.Parent
        Base = self.classes.Base
        sess = Session()

        def go():
            eq_(sess.query(Parent)
                    .options(subqueryload_all(Parent.children, Base.related))
                    .order_by(Parent.data).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 3)

    def test_subq_through_related_aliased(self):
        Parent = self.classes.Parent
        Base = self.classes.Base
        pa = aliased(Parent)
        sess = Session()

        def go():
            eq_(sess.query(pa)
                    .options(subqueryload_all(pa.children, Base.related))
                    .order_by(pa.data).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 3)

class SubClassEagerToSubClassTest(fixtures.MappedTest):
    """Test joinedloads from subclass to subclass mappers"""

    run_setup_classes = 'once'
    run_setup_mappers = 'once'
    run_inserts = 'once'
    run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        Table('parent', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('type', String(10)),
        )

        Table('subparent', metadata,
            Column('id', Integer,
                ForeignKey('parent.id'),
                primary_key=True),
            Column('data', String(10)),
        )

        Table('base', metadata,
            Column('id', Integer,
                primary_key=True,
                test_needs_autoincrement=True),
            Column('type', String(10)),
        )

        Table('sub', metadata,
            Column('id', Integer,
                ForeignKey('base.id'),
                primary_key=True),
            Column('data', String(10)),
            Column('subparent_id', Integer,
                ForeignKey('subparent.id'),
                nullable=False)
        )

    @classmethod
    def setup_classes(cls):
        class Parent(cls.Comparable):
            pass
        class Subparent(Parent):
            pass
        class Base(cls.Comparable):
            pass
        class Sub(Base):
            pass

    @classmethod
    def setup_mappers(cls):
        sub = cls.tables.sub
        Sub = cls.classes.Sub
        base = cls.tables.base
        Base = cls.classes.Base
        parent = cls.tables.parent
        Parent = cls.classes.Parent
        subparent = cls.tables.subparent
        Subparent = cls.classes.Subparent

        mapper(Parent, parent,
            polymorphic_on=parent.c.type,
            polymorphic_identity='b')

        mapper(Subparent, subparent,
            inherits=Parent,
            polymorphic_identity='s',
            properties={
                'children':relationship(Sub, order_by=base.c.id)})

        mapper(Base, base,
            polymorphic_on=base.c.type,
            polymorphic_identity='b')

        mapper(Sub, sub,
            inherits=Base,
            polymorphic_identity='s')

    @classmethod
    def insert_data(cls):
        global p1, p2

        Sub, Subparent = cls.classes.Sub, cls.classes.Subparent
        sess = create_session()
        p1 = Subparent(
            data='p1',
            children=[Sub(data='s1'), Sub(data='s2'), Sub(data='s3')])
        p2 = Subparent(
            data='p2',
            children=[Sub(data='s4'), Sub(data='s5')])
        sess.add(p1)
        sess.add(p2)
        sess.flush()

    def test_joinedload(self):
        Subparent = self.classes.Subparent

        sess = create_session()
        def go():
            eq_(sess.query(Subparent)
                    .options(joinedload(Subparent.children)).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 1)

        sess.expunge_all()
        def go():
            eq_(sess.query(Subparent)
                    .options(joinedload("children")).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 1)

    def test_contains_eager(self):
        Subparent = self.classes.Subparent

        sess = create_session()
        def go():
            eq_(sess.query(Subparent)
                    .join(Subparent.children)
                    .options(contains_eager(Subparent.children)).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 1)

        sess.expunge_all()
        def go():
            eq_(sess.query(Subparent)
                    .join(Subparent.children)
                    .options(contains_eager("children")).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 1)

    def test_subqueryload(self):
        Subparent = self.classes.Subparent

        sess = create_session()
        def go():
            eq_(sess.query(Subparent)
                    .options(subqueryload(Subparent.children)).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 2)

        sess.expunge_all()
        def go():
            eq_(sess.query(Subparent)
                    .options(subqueryload("children")).all(),
                [p1, p2])
        self.assert_sql_count(testing.db, go, 2)

class SameNamedPropTwoPolymorphicSubClassesTest(fixtures.MappedTest):
    """test pathing when two subclasses contain a different property
    for the same name, and polymorphic loading is used.

    #2614

    """
    run_setup_classes = 'once'
    run_setup_mappers = 'once'
    run_inserts = 'once'
    run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        Table('a', metadata,
            Column('id', Integer, primary_key=True,
                    test_needs_autoincrement=True),
            Column('type', String(10))
        )
        Table('b', metadata,
            Column('id', Integer, ForeignKey('a.id'), primary_key=True)
        )
        Table('btod', metadata,
            Column('bid', Integer, ForeignKey('b.id'), nullable=False),
            Column('did', Integer, ForeignKey('d.id'), nullable=False)
        )
        Table('c', metadata,
            Column('id', Integer, ForeignKey('a.id'), primary_key=True)
        )
        Table('ctod', metadata,
            Column('cid', Integer, ForeignKey('c.id'), nullable=False),
            Column('did', Integer, ForeignKey('d.id'), nullable=False)
        )
        Table('d', metadata,
            Column('id', Integer, primary_key=True,
                        test_needs_autoincrement=True)
        )

    @classmethod
    def setup_classes(cls):
        class A(cls.Comparable):
            pass
        class B(A):
            pass
        class C(A):
            pass
        class D(cls.Comparable):
            pass

    @classmethod
    def setup_mappers(cls):
        A = cls.classes.A
        B = cls.classes.B
        C = cls.classes.C
        D = cls.classes.D

        mapper(A, cls.tables.a, polymorphic_on=cls.tables.a.c.type)
        mapper(B, cls.tables.b, inherits=A, polymorphic_identity='b',
                    properties={
                        'related': relationship(D, secondary=cls.tables.btod)
                    })
        mapper(C, cls.tables.c, inherits=A, polymorphic_identity='c',
                    properties={
                        'related': relationship(D, secondary=cls.tables.ctod)
                    })
        mapper(D, cls.tables.d)


    @classmethod
    def insert_data(cls):
        B = cls.classes.B
        C = cls.classes.C
        D = cls.classes.D

        session = Session()

        d = D()
        session.add_all([
            B(related=[d]),
            C(related=[d])
        ])
        session.commit()

    def test_free_w_poly_subquery(self):
        A = self.classes.A
        B = self.classes.B
        C = self.classes.C
        D = self.classes.D

        session = Session()
        d = session.query(D).one()
        a_poly = with_polymorphic(A, [B, C])
        def go():
            for a in session.query(a_poly).\
                options(
                        subqueryload(a_poly.B.related),
                        subqueryload(a_poly.C.related)):
                eq_(a.related, [d])
        self.assert_sql_count(testing.db, go, 3)

    def test_fixed_w_poly_subquery(self):
        A = self.classes.A
        B = self.classes.B
        C = self.classes.C
        D = self.classes.D

        session = Session()
        d = session.query(D).one()
        def go():
            for a in session.query(A).with_polymorphic([B, C]).\
                options(subqueryload(B.related), subqueryload(C.related)):
                eq_(a.related, [d])
        self.assert_sql_count(testing.db, go, 3)

    def test_free_w_poly_joined(self):
        A = self.classes.A
        B = self.classes.B
        C = self.classes.C
        D = self.classes.D

        session = Session()
        d = session.query(D).one()
        a_poly = with_polymorphic(A, [B, C])
        def go():
            for a in session.query(a_poly).\
                options(
                        joinedload(a_poly.B.related),
                        joinedload(a_poly.C.related)):
                eq_(a.related, [d])
        self.assert_sql_count(testing.db, go, 1)

    def test_fixed_w_poly_joined(self):
        A = self.classes.A
        B = self.classes.B
        C = self.classes.C
        D = self.classes.D

        session = Session()
        d = session.query(D).one()
        def go():
            for a in session.query(A).with_polymorphic([B, C]).\
                options(joinedload(B.related), joinedload(C.related)):
                eq_(a.related, [d])
        self.assert_sql_count(testing.db, go, 1)


class SubClassToSubClassFromParentTest(fixtures.MappedTest):
    """test #2617

    """
    run_setup_classes = 'once'
    run_setup_mappers = 'once'
    run_inserts = 'once'
    run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        Table('z', metadata,
            Column('id', Integer, primary_key=True,
                        test_needs_autoincrement=True)
        )
        Table('a', metadata,
            Column('id', Integer, primary_key=True,
                    test_needs_autoincrement=True),
            Column('type', String(10)),
            Column('z_id', Integer, ForeignKey('z.id'))
        )
        Table('b', metadata,
            Column('id', Integer, ForeignKey('a.id'), primary_key=True)
        )
        Table('d', metadata,
            Column('id', Integer, ForeignKey('a.id'), primary_key=True),
            Column('b_id', Integer, ForeignKey('b.id'))
        )

    @classmethod
    def setup_classes(cls):
        class Z(cls.Comparable):
            pass
        class A(cls.Comparable):
            pass
        class B(A):
            pass
        class D(A):
            pass

    @classmethod
    def setup_mappers(cls):
        Z = cls.classes.Z
        A = cls.classes.A
        B = cls.classes.B
        D = cls.classes.D

        mapper(Z, cls.tables.z)
        mapper(A, cls.tables.a, polymorphic_on=cls.tables.a.c.type,
                    with_polymorphic='*',
                    properties={
                        'zs': relationship(Z, lazy="subquery")
                    })
        mapper(B, cls.tables.b, inherits=A, polymorphic_identity='b',
                    properties={
                        'related': relationship(D, lazy="subquery",
                            primaryjoin=cls.tables.d.c.b_id ==
                                                cls.tables.b.c.id)
                    })
        mapper(D, cls.tables.d, inherits=A, polymorphic_identity='d')


    @classmethod
    def insert_data(cls):
        B = cls.classes.B

        session = Session()
        session.add(B())
        session.commit()

    def test_2617(self):
        A = self.classes.A
        session = Session()
        def go():
            a1 = session.query(A).first()
            eq_(a1.related, [])
        self.assert_sql_count(testing.db, go, 3)


class SubClassToSubClassMultiTest(AssertsCompiledSQL, fixtures.MappedTest):
    """
    Two different joined-inh subclasses, led by a
    parent, with two distinct endpoints:

    parent -> subcl1 -> subcl2 -> (ep1, ep2)

    the join to ep2 indicates we need to join
    from the middle of the joinpoint, skipping ep1

    """

    run_create_tables = None
    run_deletes = None
    __dialect__ = 'default'

    @classmethod
    def define_tables(cls, metadata):
        Table('parent', metadata,
            Column('id', Integer, primary_key=True,
                    test_needs_autoincrement=True),
            Column('data', String(30))
            )
        Table('base1', metadata,
            Column('id', Integer, primary_key=True,
                    test_needs_autoincrement=True),
            Column('data', String(30))
            )
        Table('sub1', metadata,
            Column('id', Integer, ForeignKey('base1.id'), primary_key=True),
            Column('parent_id', ForeignKey('parent.id')),
            Column('subdata', String(30))
            )

        Table('base2', metadata,
            Column('id', Integer, primary_key=True,
                    test_needs_autoincrement=True),
            Column('base1_id', ForeignKey('base1.id')),
            Column('data', String(30))
            )
        Table('sub2', metadata,
            Column('id', Integer, ForeignKey('base2.id'), primary_key=True),
            Column('subdata', String(30))
            )
        Table('ep1', metadata,
            Column('id', Integer, primary_key=True,
                                test_needs_autoincrement=True),
            Column('base2_id', Integer, ForeignKey('base2.id')),
            Column('data', String(30))
            )
        Table('ep2', metadata,
            Column('id', Integer, primary_key=True,
                                test_needs_autoincrement=True),
            Column('base2_id', Integer, ForeignKey('base2.id')),
            Column('data', String(30))
            )

    @classmethod
    def setup_classes(cls):
        class Parent(cls.Comparable):
            pass
        class Base1(cls.Comparable):
            pass
        class Sub1(Base1):
            pass
        class Base2(cls.Comparable):
            pass
        class Sub2(Base2):
            pass
        class EP1(cls.Comparable):
            pass
        class EP2(cls.Comparable):
            pass

    @classmethod
    def _classes(cls):
        return cls.classes.Parent, cls.classes.Base1,\
            cls.classes.Base2, cls.classes.Sub1,\
            cls.classes.Sub2, cls.classes.EP1,\
            cls.classes.EP2

    @classmethod
    def setup_mappers(cls):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = cls._classes()

        mapper(Parent, cls.tables.parent, properties={
                'sub1': relationship(Sub1)
            })
        mapper(Base1, cls.tables.base1, properties={
                'sub2': relationship(Sub2)
            })
        mapper(Sub1, cls.tables.sub1, inherits=Base1)
        mapper(Base2, cls.tables.base2, properties={
                'ep1': relationship(EP1),
                'ep2': relationship(EP2)
            })
        mapper(Sub2, cls.tables.sub2, inherits=Base2)
        mapper(EP1, cls.tables.ep1)
        mapper(EP2, cls.tables.ep2)

    def test_one(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s = Session()
        self.assert_compile(
            s.query(Parent).join(Parent.sub1, Sub1.sub2).
                join(Sub2.ep1).
                join(Sub2.ep2),
            "SELECT parent.id AS parent_id, parent.data AS parent_data "
            "FROM parent JOIN (base1 JOIN sub1 ON base1.id = sub1.id) "
            "ON parent.id = sub1.parent_id JOIN "
            "(base2 JOIN sub2 "
            "ON base2.id = sub2.id) "
            "ON base1.id = base2.base1_id "
            "JOIN ep1 ON base2.id = ep1.base2_id "
            "JOIN ep2 ON base2.id = ep2.base2_id"
        )

    def test_two(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s2a = aliased(Sub2, flat=True)

        s = Session()
        self.assert_compile(
            s.query(Parent).join(Parent.sub1).
                join(s2a, Sub1.sub2),
            "SELECT parent.id AS parent_id, parent.data AS parent_data "
            "FROM parent JOIN (base1 JOIN sub1 ON base1.id = sub1.id) "
            "ON parent.id = sub1.parent_id JOIN "
            "(base2 AS base2_1 JOIN sub2 AS sub2_1 "
            "ON base2_1.id = sub2_1.id) "
            "ON base1.id = base2_1.base1_id"
        )

    def test_three(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s = Session()
        self.assert_compile(
            s.query(Base1).join(Base1.sub2).
                join(Sub2.ep1).\
                join(Sub2.ep2),
            "SELECT base1.id AS base1_id, base1.data AS base1_data "
            "FROM base1 JOIN (base2 JOIN sub2 "
            "ON base2.id = sub2.id) ON base1.id = "
            "base2.base1_id "
            "JOIN ep1 ON base2.id = ep1.base2_id "
            "JOIN ep2 ON base2.id = ep2.base2_id"
        )

    def test_four(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s = Session()
        self.assert_compile(
            s.query(Sub2).join(Base1, Base1.id == Sub2.base1_id).
                join(Sub2.ep1).\
                join(Sub2.ep2),
            "SELECT sub2.id AS sub2_id, base2.id AS base2_id, "
            "base2.base1_id AS base2_base1_id, base2.data AS base2_data, "
            "sub2.subdata AS sub2_subdata "
            "FROM base2 JOIN sub2 ON base2.id = sub2.id "
            "JOIN base1 ON base1.id = base2.base1_id "
            "JOIN ep1 ON base2.id = ep1.base2_id "
            "JOIN ep2 ON base2.id = ep2.base2_id"
        )

    def test_five(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s = Session()
        self.assert_compile(
            s.query(Sub2).join(Sub1, Sub1.id == Sub2.base1_id).
                join(Sub2.ep1).\
                join(Sub2.ep2),
            "SELECT sub2.id AS sub2_id, base2.id AS base2_id, "
            "base2.base1_id AS base2_base1_id, base2.data AS base2_data, "
            "sub2.subdata AS sub2_subdata "
            "FROM base2 JOIN sub2 ON base2.id = sub2.id "
            "JOIN "
            "(base1 JOIN sub1 ON base1.id = sub1.id) "
            "ON sub1.id = base2.base1_id "
            "JOIN ep1 ON base2.id = ep1.base2_id "
            "JOIN ep2 ON base2.id = ep2.base2_id"
        )

    def test_six(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s = Session()
        self.assert_compile(
            s.query(Sub2).from_self().\
                join(Sub2.ep1).
                join(Sub2.ep2),
            "SELECT anon_1.sub2_id AS anon_1_sub2_id, "
            "anon_1.base2_id AS anon_1_base2_id, "
            "anon_1.base2_base1_id AS anon_1_base2_base1_id, "
            "anon_1.base2_data AS anon_1_base2_data, "
            "anon_1.sub2_subdata AS anon_1_sub2_subdata "
            "FROM (SELECT sub2.id AS sub2_id, base2.id AS base2_id, "
            "base2.base1_id AS base2_base1_id, base2.data AS base2_data, "
            "sub2.subdata AS sub2_subdata "
            "FROM base2 JOIN sub2 ON base2.id = sub2.id) AS anon_1 "
            "JOIN ep1 ON anon_1.base2_id = ep1.base2_id "
            "JOIN ep2 ON anon_1.base2_id = ep2.base2_id"
        )

    def test_seven(self):
        Parent, Base1, Base2, Sub1, Sub2, EP1, EP2 = self._classes()

        s = Session()
        self.assert_compile(
            # adding Sub2 to the entities list helps it,
            # otherwise the joins for Sub2.ep1/ep2 don't have columns
            # to latch onto.   Can't really make it better than this
            s.query(Parent, Sub2).join(Parent.sub1).\
                join(Sub1.sub2).from_self().\
                join(Sub2.ep1).
                join(Sub2.ep2),
            "SELECT anon_1.parent_id AS anon_1_parent_id, "
            "anon_1.parent_data AS anon_1_parent_data, "
            "anon_1.sub2_id AS anon_1_sub2_id, "
            "anon_1.base2_id AS anon_1_base2_id, "
            "anon_1.base2_base1_id AS anon_1_base2_base1_id, "
            "anon_1.base2_data AS anon_1_base2_data, "
            "anon_1.sub2_subdata AS anon_1_sub2_subdata "
            "FROM (SELECT parent.id AS parent_id, parent.data AS parent_data, "
            "sub2.id AS sub2_id, "
            "base2.id AS base2_id, "
            "base2.base1_id AS base2_base1_id, "
            "base2.data AS base2_data, "
            "sub2.subdata AS sub2_subdata "
            "FROM parent JOIN (base1 JOIN sub1 ON base1.id = sub1.id) "
            "ON parent.id = sub1.parent_id JOIN "
            "(base2 JOIN sub2 ON base2.id = sub2.id) "
            "ON base1.id = base2.base1_id) AS anon_1 "
            "JOIN ep1 ON anon_1.base2_id = ep1.base2_id "
            "JOIN ep2 ON anon_1.base2_id = ep2.base2_id"
        )

class JoinAcrossJoinedInhMultiPath(fixtures.DeclarativeMappedTest,
                                        testing.AssertsCompiledSQL):
    """test long join paths with a joined-inh in the middle, where we go multiple
    times across the same joined-inh to the same target but with other classes
    in the middle.    E.g. test [ticket:2908]
    """


    run_setup_mappers = 'once'
    __dialect__ = 'default'

    @classmethod
    def setup_classes(cls):
        Base = cls.DeclarativeBasic

        class Root(Base):
            __tablename__ = 'root'

            id = Column(Integer, primary_key=True)
            sub1_id = Column(Integer, ForeignKey('sub1.id'))

            intermediate = relationship("Intermediate")
            sub1 = relationship("Sub1")

        class Intermediate(Base):
            __tablename__ = 'intermediate'

            id = Column(Integer, primary_key=True)
            sub1_id = Column(Integer, ForeignKey('sub1.id'))
            root_id = Column(Integer, ForeignKey('root.id'))
            sub1 = relationship("Sub1")

        class Parent(Base):
            __tablename__ = 'parent'

            id = Column(Integer, primary_key=True)

        class Sub1(Parent):
            __tablename__ = 'sub1'
            id = Column(Integer, ForeignKey('parent.id'),
                        primary_key=True)

            target = relationship("Target")

        class Target(Base):
            __tablename__ = 'target'
            id = Column(Integer, primary_key=True)
            sub1_id = Column(Integer, ForeignKey('sub1.id'))

    def test_join(self):
        Root, Intermediate, Sub1, Target = \
                    self.classes.Root, self.classes.Intermediate, \
                    self.classes.Sub1, self.classes.Target
        s1_alias = aliased(Sub1)
        s2_alias = aliased(Sub1)
        t1_alias = aliased(Target)
        t2_alias = aliased(Target)

        sess = Session()
        q = sess.query(Root).\
                join(s1_alias, Root.sub1).join(t1_alias, s1_alias.target).\
                join(Root.intermediate).join(s2_alias, Intermediate.sub1).\
                join(t2_alias, s2_alias.target)
        self.assert_compile(q,
            "SELECT root.id AS root_id, root.sub1_id AS root_sub1_id "
            "FROM root "
            "JOIN (SELECT parent.id AS parent_id, sub1.id AS sub1_id "
                "FROM parent JOIN sub1 ON parent.id = sub1.id) AS anon_1 "
                "ON anon_1.sub1_id = root.sub1_id "
            "JOIN target AS target_1 ON anon_1.sub1_id = target_1.sub1_id "
            "JOIN intermediate ON root.id = intermediate.root_id "
            "JOIN (SELECT parent.id AS parent_id, sub1.id AS sub1_id "
                "FROM parent JOIN sub1 ON parent.id = sub1.id) AS anon_2 "
                "ON anon_2.sub1_id = intermediate.sub1_id "
            "JOIN target AS target_2 ON anon_2.sub1_id = target_2.sub1_id")

    def test_join_flat(self):
        Root, Intermediate, Sub1, Target = \
                    self.classes.Root, self.classes.Intermediate, \
                    self.classes.Sub1, self.classes.Target
        s1_alias = aliased(Sub1, flat=True)
        s2_alias = aliased(Sub1, flat=True)
        t1_alias = aliased(Target)
        t2_alias = aliased(Target)

        sess = Session()
        q = sess.query(Root).\
                join(s1_alias, Root.sub1).join(t1_alias, s1_alias.target).\
                join(Root.intermediate).join(s2_alias, Intermediate.sub1).\
                join(t2_alias, s2_alias.target)
        self.assert_compile(q,
            "SELECT root.id AS root_id, root.sub1_id AS root_sub1_id "
            "FROM root "
            "JOIN (parent AS parent_1 JOIN sub1 AS sub1_1 ON parent_1.id = sub1_1.id) "
                "ON sub1_1.id = root.sub1_id "
            "JOIN target AS target_1 ON sub1_1.id = target_1.sub1_id "
            "JOIN intermediate ON root.id = intermediate.root_id "
            "JOIN (parent AS parent_2 JOIN sub1 AS sub1_2 ON parent_2.id = sub1_2.id) "
                "ON sub1_2.id = intermediate.sub1_id "
            "JOIN target AS target_2 ON sub1_2.id = target_2.sub1_id"
        )

    def test_joinedload(self):
        Root, Intermediate, Sub1, Target = \
                    self.classes.Root, self.classes.Intermediate, \
                    self.classes.Sub1, self.classes.Target

        sess = Session()
        q = sess.query(Root).\
                options(
                    joinedload(Root.sub1).joinedload(Sub1.target),
                    joinedload(Root.intermediate).joinedload(Intermediate.sub1).\
                        joinedload(Sub1.target),
                )
        self.assert_compile(q,
            "SELECT root.id AS root_id, root.sub1_id AS root_sub1_id, "
            "target_1.id AS target_1_id, target_1.sub1_id AS target_1_sub1_id, "
            "sub1_1.id AS sub1_1_id, parent_1.id AS parent_1_id, "
            "intermediate_1.id AS intermediate_1_id, "
            "intermediate_1.sub1_id AS intermediate_1_sub1_id, "
            "intermediate_1.root_id AS intermediate_1_root_id, "
            "target_2.id AS target_2_id, target_2.sub1_id AS target_2_sub1_id, "
            "sub1_2.id AS sub1_2_id, parent_2.id AS parent_2_id "
            "FROM root "
            "LEFT OUTER JOIN intermediate AS intermediate_1 "
                    "ON root.id = intermediate_1.root_id "
            "LEFT OUTER JOIN (parent AS parent_1 JOIN sub1 AS sub1_1 "
                    "ON parent_1.id = sub1_1.id) ON sub1_1.id = intermediate_1.sub1_id "
            "LEFT OUTER JOIN target AS target_1 ON sub1_1.id = target_1.sub1_id "
            "LEFT OUTER JOIN (parent AS parent_2 JOIN sub1 AS sub1_2 "
                    "ON parent_2.id = sub1_2.id) ON sub1_2.id = root.sub1_id "
            "LEFT OUTER JOIN target AS target_2 ON sub1_2.id = target_2.sub1_id")


class MultipleAdaptUsesEntityOverTableTest(AssertsCompiledSQL, fixtures.MappedTest):
    __dialect__ = 'default'
    run_create_tables = None
    run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        Table('a', metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String)
        )
        Table('b', metadata,
                Column('id', Integer, ForeignKey('a.id'), primary_key=True)
        )
        Table('c', metadata,
                Column('id', Integer, ForeignKey('a.id'), primary_key=True),
                Column('bid', Integer, ForeignKey('b.id'))
        )
        Table('d', metadata,
                Column('id', Integer, ForeignKey('a.id'), primary_key=True),
                Column('cid', Integer, ForeignKey('c.id'))
        )

    @classmethod
    def setup_classes(cls):
        class A(cls.Comparable):
            pass
        class B(A):
            pass
        class C(A):
            pass
        class D(A):
            pass

    @classmethod
    def setup_mappers(cls):
        A, B, C, D = cls.classes.A, cls.classes.B, cls.classes.C, cls.classes.D
        a, b, c, d = cls.tables.a, cls.tables.b, cls.tables.c, cls.tables.d
        mapper(A, a)
        mapper(B, b, inherits=A)
        mapper(C, c, inherits=A)
        mapper(D, d, inherits=A)

    def _two_join_fixture(self):
        A, B, C, D = self.classes.A, self.classes.B, self.classes.C, self.classes.D
        s = Session()
        return s.query(B.name, C.name, D.name).select_from(B).\
                        join(C, C.bid == B.id).\
                        join(D, D.cid == C.id)

    def test_two_joins_adaption(self):
        a, b, c, d = self.tables.a, self.tables.b, self.tables.c, self.tables.d
        q = self._two_join_fixture()

        btoc = q._from_obj[0].left

        ac_adapted = btoc.right.element.left
        c_adapted = btoc.right.element.right

        is_(ac_adapted.element, a)
        is_(c_adapted.element, c)

        ctod = q._from_obj[0].right
        ad_adapted = ctod.left
        d_adapted = ctod.right
        is_(ad_adapted.element, a)
        is_(d_adapted.element, d)

        bname, cname, dname = q._entities

        b_name_adapted = bname._resolve_expr_against_query_aliases(
                                        q, bname.column, None)
        c_name_adapted = cname._resolve_expr_against_query_aliases(
                                        q, cname.column, None)
        d_name_adapted = dname._resolve_expr_against_query_aliases(
                                        q, dname.column, None)

        assert bool(b_name_adapted == a.c.name)
        assert bool(c_name_adapted == ac_adapted.c.name)
        assert bool(d_name_adapted == ad_adapted.c.name)

    def test_two_joins_sql(self):
        q = self._two_join_fixture()
        self.assert_compile(q,
            "SELECT a.name AS a_name, a_1.name AS a_1_name, "
            "a_2.name AS a_2_name "
            "FROM a JOIN b ON a.id = b.id JOIN "
            "(a AS a_1 JOIN c AS c_1 ON a_1.id = c_1.id) ON c_1.bid = b.id "
            "JOIN (a AS a_2 JOIN d AS d_1 ON a_2.id = d_1.id) "
            "ON d_1.cid = c_1.id"
        )