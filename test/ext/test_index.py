from sqlalchemy.testing import assert_raises
import sqlalchemy as sa
from sqlalchemy import testing
from sqlalchemy import Integer, Text
from sqlalchemy.sql.sqltypes import ARRAY, JSON
from sqlalchemy.testing.schema import Column
from sqlalchemy.orm import Session
from sqlalchemy.testing import fixtures
from sqlalchemy.ext.index import index_property, json_property


class IndexPropertyTest(fixtures.TestBase):

    def test_array(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column('id', Integer, primary_key=True)
            array = Column('_array', ARRAY(Integer),
                           default=[])
            first = index_property('array', 0, mutable=True)

        a = A(array=[1, 2, 3])
        assert a.first == 1
        a.first = 100
        assert a.first == 100
        assert a.array == [100, 2, 3]

    def test_json(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class J(Base):
            __tablename__ = 'j'
            id = Column('id', Integer, primary_key=True)
            json = Column('_json', JSON, default={})
            field = index_property('json', 'field', default=None, mutable=True)

        j = J(json={'a': 1, 'b': 2})
        assert j.field is None
        j.field = 'test'
        assert j.field == 'test'
        assert j.json == {'a': 1, 'b': 2, 'field': 'test'}

    def test_column_key(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column('id', Integer, primary_key=True)
            array = Column('_array', ARRAY(Integer),
                           default=[])
            first = index_property('array', 0, mutable=True)

        a = A(array=[1, 2, 3])
        assert a.first == 1
        a.first = 100
        assert a.first == 100
        assert a.array == [100, 2, 3]

    def test_get_no_column_default(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column('id', Integer, primary_key=True)
            array = Column('_array', ARRAY(Integer))
            first = index_property('array', 0)

        a = A()
        assert_raises(TypeError, lambda: a.first)

    def test_get_no_index_default(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column('id', Integer, primary_key=True)
            array = Column('_array', ARRAY(Integer))
            first = index_property('array', 0)

        a = A(array=[])
        assert_raises(IndexError, lambda: a.first)

    def test_get_index_default(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)
            array = Column(ARRAY(Integer))
            first = index_property('array', 0, default=5)

        a = A()
        assert a.first == 5

    def test_set_immutable(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)
            array = Column(ARRAY(Integer))
            first = index_property('array', 0)

        a = A()

        def set():
            a.first = 10
        assert_raises(AttributeError, set)

    def test_set_mutable_dict(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class J(Base):
            __tablename__ = 'j'
            id = Column(Integer, primary_key=True)
            json = Column(JSON, default={})
            field = index_property('json', 'field', default=None, mutable=True)

        j = J()

        def set():
            j.field = 10

        assert_raises(TypeError, set)

        j.json = {}
        assert j.field is None
        set()
        assert j.field == 10

    def test_set_without_column_default(self):
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()

        class A(Base):
            __tablename__ = 'a'
            id = Column(Integer, primary_key=True)
            array = Column(ARRAY(Integer))
            first = index_property('array', 0, mutable=True)

        a = A()

        def set():
            a.first = 10
        assert_raises(TypeError, set)

        a.array = []
        assert_raises(IndexError, set)

        a.array = [42]
        assert a.first == 42
        set()
        assert a.first == 10


class IndexPropertyPostgresqlTest(fixtures.DeclarativeMappedTest):

    __only_on__ = 'postgresql'
    __backend__ = True

    @classmethod
    def setup_classes(cls):
        from sqlalchemy.dialects.postgresql import ARRAY, JSON

        Base = cls.DeclarativeBasic

        class Array(fixtures.ComparableEntity, Base):
            __tablename__ = "array"

            id = Column(sa.Integer, primary_key=True,
                        test_needs_autoincrement=True)
            array = Column(ARRAY(Integer), default=[])
            first = index_property('array', 0, default=None)
            mutable = index_property('array', 0, default=None, mutable=True)

        class Json(fixtures.ComparableEntity, Base):
            __tablename__ = "json"

            id = Column(sa.Integer, primary_key=True,
                        test_needs_autoincrement=True)
            json = Column(JSON, default={})
            field = index_property('json', 'field', default=None)
            json_field = json_property('json', 'field')
            int_field = json_property('json', 'field', cast_type=Integer)
            text_field = json_property('json', 'field', cast_type=Text)
            other = index_property('json', 'other', mutable=True,
                                   use_column_default_for_none=True)

        Base.metadata.drop_all()
        Base.metadata.create_all()

    def test_query_array(self):
        Array = self.classes.Array
        s = Session(testing.db)

        s.add_all([
            Array(),
            Array(array=[1, 2, 3]),
            Array(array=[4, 5, 6])])
        s.commit()

        a1 = s.query(Array).filter(Array.array == [1, 2, 3]).one()
        a2 = s.query(Array).filter(Array.first == 1).one()
        assert a1.id == a2.id
        a3 = s.query(Array).filter(Array.first == 4).one()
        assert a1.id != a3.id

    def test_query_json(self):
        Json = self.classes.Json
        s = Session(testing.db)

        s.add_all([
            Json(),
            Json(json={'field': 10}),
            Json(json={'field': 20})])
        s.commit()

        a1 = s.query(Json).filter(Json.json['field'].astext.cast(Integer) == 10)\
            .one()
        a2 = s.query(Json).filter(Json.field.astext == '10').one()
        assert a1.id == a2.id
        a3 = s.query(Json).filter(Json.field.astext == '20').one()
        assert a1.id != a3.id

    def test_mutable_array(self):
        Array = self.classes.Array
        s = Session(testing.db)

        a = Array(array=[1, 2, 3])
        s.add(a)
        s.commit()

        a.mutable = 42
        assert a.first == 42
        s.commit()
        assert a.first == 42

    def test_mutable_json(self):
        Json = self.classes.Json
        s = Session(testing.db)

        j = Json(json={})
        s.add(j)
        s.commit()

        j.other = 42
        assert j.other == 42
        s.commit()
        assert j.other == 42

    def test_set_column_default(self):
        Json = self.classes.Json
        j = Json()

        assert_raises(KeyError, lambda: j.other)
        j.other = 42
        assert j.other == 42
        assert j.json == {'other': 42}

    def test_modified(self):
        from sqlalchemy import inspect

        Array = self.classes.Array
        s = Session(testing.db)

        a = Array(array=[1, 2, 3])
        s.add(a)
        s.commit()

        i = inspect(a)
        assert not i.modified
        assert 'array' in i.unmodified

        a.mutable = 10

        assert i.modified
        assert 'array' not in i.unmodified

    def test_json_type(self):
        Json = self.classes.Json
        s = Session(testing.db)

        j = Json(json={'field': 10})
        s.add(j)
        s.commit()

        jq = s.query(Json).filter(Json.int_field == 10).one()
        assert j.id == jq.id

        jq = s.query(Json).filter(Json.text_field == '10').one()
        assert j.id == jq.id

        jq = s.query(Json).filter(Json.json_field.astext == '10').one()
        assert j.id == jq.id

        jq = s.query(Json).filter(Json.text_field == 'wrong').first()
        assert jq is None

        j.json = {'field': True}
        s.commit()

        jq = s.query(Json).filter(Json.text_field == 'true').one()
        assert j.id == jq.id
