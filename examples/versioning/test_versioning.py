from unittest import TestCase
from sqlalchemy.ext.declarative import declarative_base
from .history_meta import Versioned, versioned_session
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import clear_mappers, Session, deferred, relationship
from ._lib import ComparableEntity, eq_

engine = None


def setup():
    global engine
    engine = create_engine('sqlite://', echo=True)

class TestVersioning(TestCase):
    def setUp(self):
        self.session = Session(engine)
        self.Base = declarative_base()
        versioned_session(self.session)

    def tearDown(self):
        self.session.close()
        clear_mappers()
        self.Base.metadata.drop_all(engine)

    def create_tables(self):
        self.Base.metadata.create_all(engine)

    def test_plain(self):
        class SomeClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'sometable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        self.create_tables()
        sess = self.session
        sc = SomeClass(name='sc1')
        sess.add(sc)
        sess.commit()

        sc.name = 'sc1modified'
        sess.commit()

        assert sc.version == 2

        SomeClassHistory = SomeClass.__history_mapper__.class_

        eq_(
            sess.query(SomeClassHistory).filter(SomeClassHistory.version == 1).all(),
            [SomeClassHistory(version=1, name='sc1')]
        )

        sc.name = 'sc1modified2'

        eq_(
            sess.query(SomeClassHistory).order_by(SomeClassHistory.version).all(),
            [
                SomeClassHistory(version=1, name='sc1'),
                SomeClassHistory(version=2, name='sc1modified')
            ]
        )

        assert sc.version == 3

        sess.commit()

        sc.name = 'temp'
        sc.name = 'sc1modified2'

        sess.commit()

        eq_(
            sess.query(SomeClassHistory).order_by(SomeClassHistory.version).all(),
            [
                SomeClassHistory(version=1, name='sc1'),
                SomeClassHistory(version=2, name='sc1modified')
            ]
        )

        sess.delete(sc)
        sess.commit()

        eq_(
            sess.query(SomeClassHistory).order_by(SomeClassHistory.version).all(),
            [
                SomeClassHistory(version=1, name='sc1'),
                SomeClassHistory(version=2, name='sc1modified'),
                SomeClassHistory(version=3, name='sc1modified2')
            ]
        )

    def test_from_null(self):
        class SomeClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'sometable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        self.create_tables()
        sess = self.session
        sc = SomeClass()
        sess.add(sc)
        sess.commit()

        sc.name = 'sc1'
        sess.commit()

        assert sc.version == 2

    def test_deferred(self):
        """test versioning of unloaded, deferred columns."""

        class SomeClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'sometable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            data = deferred(Column(String(25)))

        self.create_tables()
        sess = self.session
        sc = SomeClass(name='sc1', data='somedata')
        sess.add(sc)
        sess.commit()
        sess.close()

        sc = sess.query(SomeClass).first()
        assert 'data' not in sc.__dict__

        sc.name = 'sc1modified'
        sess.commit()

        assert sc.version == 2

        SomeClassHistory = SomeClass.__history_mapper__.class_

        eq_(
            sess.query(SomeClassHistory).filter(SomeClassHistory.version == 1).all(),
            [SomeClassHistory(version=1, name='sc1', data='somedata')]
        )


    def test_joined_inheritance(self):
        class BaseClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'basetable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            type = Column(String(20))

            __mapper_args__ = {'polymorphic_on':type, 'polymorphic_identity':'base'}

        class SubClassSeparatePk(BaseClass):
            __tablename__ = 'subtable1'

            id = Column(Integer, primary_key=True)
            base_id = Column(Integer, ForeignKey('basetable.id'))
            subdata1 = Column(String(50))

            __mapper_args__ = {'polymorphic_identity':'sep'}

        class SubClassSamePk(BaseClass):
            __tablename__ = 'subtable2'

            id = Column(Integer, ForeignKey('basetable.id'), primary_key=True)
            subdata2 = Column(String(50))

            __mapper_args__ = {'polymorphic_identity':'same'}

        self.create_tables()
        sess = self.session

        sep1 = SubClassSeparatePk(name='sep1', subdata1='sep1subdata')
        base1 = BaseClass(name='base1')
        same1 = SubClassSamePk(name='same1', subdata2='same1subdata')
        sess.add_all([sep1, base1, same1])
        sess.commit()

        base1.name = 'base1mod'
        same1.subdata2 = 'same1subdatamod'
        sep1.name ='sep1mod'
        sess.commit()

        BaseClassHistory = BaseClass.__history_mapper__.class_
        SubClassSeparatePkHistory = SubClassSeparatePk.__history_mapper__.class_
        SubClassSamePkHistory = SubClassSamePk.__history_mapper__.class_
        eq_(
            sess.query(BaseClassHistory).order_by(BaseClassHistory.id).all(),
            [
                SubClassSeparatePkHistory(id=1, name='sep1', type='sep', version=1),
                BaseClassHistory(id=2, name='base1', type='base', version=1),
                SubClassSamePkHistory(id=3, name='same1', type='same', version=1)
            ]
        )

        same1.subdata2 = 'same1subdatamod2'

        eq_(
            sess.query(BaseClassHistory).order_by(BaseClassHistory.id, BaseClassHistory.version).all(),
            [
                SubClassSeparatePkHistory(id=1, name='sep1', type='sep', version=1),
                BaseClassHistory(id=2, name='base1', type='base', version=1),
                SubClassSamePkHistory(id=3, name='same1', type='same', version=1),
                SubClassSamePkHistory(id=3, name='same1', type='same', version=2)
            ]
        )

        base1.name = 'base1mod2'
        eq_(
            sess.query(BaseClassHistory).order_by(BaseClassHistory.id, BaseClassHistory.version).all(),
            [
                SubClassSeparatePkHistory(id=1, name='sep1', type='sep', version=1),
                BaseClassHistory(id=2, name='base1', type='base', version=1),
                BaseClassHistory(id=2, name='base1mod', type='base', version=2),
                SubClassSamePkHistory(id=3, name='same1', type='same', version=1),
                SubClassSamePkHistory(id=3, name='same1', type='same', version=2)
            ]
        )

    def test_single_inheritance(self):
        class BaseClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'basetable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            type = Column(String(50))
            __mapper_args__ = {'polymorphic_on':type, 'polymorphic_identity':'base'}

        class SubClass(BaseClass):

            subname = Column(String(50), unique=True)
            __mapper_args__ = {'polymorphic_identity':'sub'}

        self.create_tables()
        sess = self.session

        b1 = BaseClass(name='b1')
        sc = SubClass(name='s1', subname='sc1')

        sess.add_all([b1, sc])

        sess.commit()

        b1.name='b1modified'

        BaseClassHistory = BaseClass.__history_mapper__.class_
        SubClassHistory = SubClass.__history_mapper__.class_

        eq_(
            sess.query(BaseClassHistory).order_by(BaseClassHistory.id, BaseClassHistory.version).all(),
            [BaseClassHistory(id=1, name='b1', type='base', version=1)]
        )

        sc.name ='s1modified'
        b1.name='b1modified2'

        eq_(
            sess.query(BaseClassHistory).order_by(BaseClassHistory.id, BaseClassHistory.version).all(),
            [
                BaseClassHistory(id=1, name='b1', type='base', version=1),
                BaseClassHistory(id=1, name='b1modified', type='base', version=2),
                SubClassHistory(id=2, name='s1', type='sub', version=1)
            ]
        )

        # test the unique constraint on the subclass
        # column
        sc.name ="modifyagain"
        sess.flush()

    def test_unique(self):
        class SomeClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'sometable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50), unique=True)
            data = Column(String(50))

        self.create_tables()
        sess = self.session
        sc = SomeClass(name='sc1', data='sc1')
        sess.add(sc)
        sess.commit()

        sc.data = 'sc1modified'
        sess.commit()

        assert sc.version == 2

        sc.data = 'sc1modified2'
        sess.commit()

        assert sc.version == 3

    def test_relationship(self):

        class SomeRelated(self.Base, ComparableEntity):
            __tablename__ = 'somerelated'

            id = Column(Integer, primary_key=True)

        class SomeClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'sometable'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            related_id = Column(Integer, ForeignKey('somerelated.id'))
            related = relationship("SomeRelated", backref='classes')

        SomeClassHistory = SomeClass.__history_mapper__.class_

        self.create_tables()
        sess = self.session
        sc = SomeClass(name='sc1')
        sess.add(sc)
        sess.commit()

        assert sc.version == 1

        sr1 = SomeRelated()
        sc.related = sr1
        sess.commit()

        assert sc.version == 2

        eq_(
            sess.query(SomeClassHistory).filter(SomeClassHistory.version == 1).all(),
            [SomeClassHistory(version=1, name='sc1', related_id=None)]
        )

        sc.related = None

        eq_(
            sess.query(SomeClassHistory).order_by(SomeClassHistory.version).all(),
            [
                SomeClassHistory(version=1, name='sc1', related_id=None),
                SomeClassHistory(version=2, name='sc1', related_id=sr1.id)
            ]
        )

        assert sc.version == 3

    def test_backref_relationship(self):

        class SomeRelated(self.Base, ComparableEntity):
            __tablename__ = 'somerelated'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            related_id = Column(Integer, ForeignKey('sometable.id'))
            related = relationship("SomeClass", backref='related')

        class SomeClass(Versioned, self.Base, ComparableEntity):
            __tablename__ = 'sometable'

            id = Column(Integer, primary_key=True)

        self.create_tables()
        sess = self.session
        sc = SomeClass()
        sess.add(sc)
        sess.commit()

        assert sc.version == 1

        sr = SomeRelated(name='sr', related=sc)
        sess.add(sr)
        sess.commit()

        assert sc.version == 1

        sr.name = 'sr2'
        sess.commit()

        assert sc.version == 1

        sess.delete(sr)
        sess.commit()

        assert sc.version == 1
