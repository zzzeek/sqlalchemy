from __future__ import unicode_literals

"""Benchmark for SQLAlchemy.

An adaptation of Robert Brewers' ZooMark speed tests. """


import datetime
import sys
import time
from sqlalchemy import *
from sqlalchemy.testing import fixtures, engines, profiling
from sqlalchemy import testing
ITERATIONS = 1
dbapi_session = engines.ReplayableSession()
metadata = None


class ZooMarkTest(fixtures.TestBase):

    """Runs the ZooMark and squawks if method counts vary from the norm.

    Each test has an associated `call_range`, the total number of
    accepted function calls made during the test.  The count can vary
    between Python 2.4 and 2.5.

    Unlike a unit test, this is a ordered collection of steps.  Running
    components individually will fail.

    """
    __requires__ = 'cpython',
    __only_on__ = 'postgresql+psycopg2'

    def test_baseline_0_setup(self):
        global metadata
        creator = testing.db.pool._creator
        recorder = lambda : dbapi_session.recorder(creator())
        engine = engines.testing_engine(options={'creator': recorder,
                            'use_reaper':False})
        metadata = MetaData(engine)
        engine.connect()

    def test_baseline_1_create_tables(self):
        Zoo = Table(
            'Zoo',
            metadata,
            Column('ID', Integer, Sequence('zoo_id_seq'),
                   primary_key=True, index=True),
            Column('Name', Unicode(255)),
            Column('Founded', Date),
            Column('Opens', Time),
            Column('LastEscape', DateTime),
            Column('Admission', Float),
            )
        Animal = Table(
            'Animal',
            metadata,
            Column('ID', Integer, Sequence('animal_id_seq'),
                   primary_key=True),
            Column('ZooID', Integer, ForeignKey('Zoo.ID'), index=True),
            Column('Name', Unicode(100)),
            Column('Species', Unicode(100)),
            Column('Legs', Integer, default=4),
            Column('LastEscape', DateTime),
            Column('Lifespan', Float(4)),
            Column('MotherID', Integer, ForeignKey('Animal.ID')),
            Column('PreferredFoodID', Integer),
            Column('AlternateFoodID', Integer),
            )
        metadata.create_all()

    def test_baseline_1a_populate(self):
        Zoo = metadata.tables['Zoo']
        Animal = metadata.tables['Animal']
        engine = metadata.bind
        wap = engine.execute(Zoo.insert(), Name='Wild Animal Park',
                                   Founded=datetime.date(2000, 1, 1),
                                   Opens=datetime.time(8, 15, 59),
                                   LastEscape=
                                  datetime.datetime(2004, 7, 29, 5, 6, 7),
                                  Admission=4.95).inserted_primary_key[0]
        sdz = engine.execute(Zoo.insert(), Name='San Diego Zoo',
                                   Founded=datetime.date(1935, 9, 13),
                                   Opens=datetime.time(9, 0, 0),
                                   Admission=0).inserted_primary_key[0]
        engine.execute(Zoo.insert(inline=True), Name='Montr\xe9al Biod\xf4me',
                Founded=datetime.date(1992, 6, 19),
                Opens=datetime.time(9, 0, 0), Admission=11.75)
        seaworld = engine.execute(Zoo.insert(), Name='Sea_World',
                Admission=60).inserted_primary_key[0]

        # Let's add a crazy futuristic Zoo to test large date values.

        lp = engine.execute(Zoo.insert(), Name='Luna Park',
                                  Founded=datetime.date(2072, 7, 17),
                                  Opens=datetime.time(0, 0, 0),
                                  Admission=134.95).inserted_primary_key[0]

        # Animals

        leopardid = engine.execute(Animal.insert(), Species='Leopard',
                Lifespan=73.5).inserted_primary_key[0]
        engine.execute(Animal.update(Animal.c.ID == leopardid), ZooID=wap,
                LastEscape=datetime.datetime( 2004, 12, 21, 8, 15, 0, 999907,)
                )
        lion = engine.execute(Animal.insert(), Species='Lion',
                ZooID=wap).inserted_primary_key[0]
        engine.execute(Animal.insert(), Species='Slug', Legs=1, Lifespan=.75)
        tiger = engine.execute(Animal.insert(), Species='Tiger',
                ZooID=sdz).inserted_primary_key[0]

        # Override Legs.default with itself just to make sure it works.

        engine.execute(Animal.insert(inline=True), Species='Bear', Legs=4)
        engine.execute(Animal.insert(inline=True), Species='Ostrich', Legs=2,
                Lifespan=103.2)
        engine.execute(Animal.insert(inline=True), Species='Centipede',
                Legs=100)
        emp = engine.execute(Animal.insert(), Species='Emperor Penguin',
                Legs=2, ZooID=seaworld).inserted_primary_key[0]
        adelie = engine.execute(Animal.insert(), Species='Adelie Penguin',
                Legs=2, ZooID=seaworld).inserted_primary_key[0]
        engine.execute(Animal.insert(inline=True), Species='Millipede',
                Legs=1000000, ZooID=sdz)

        # Add a mother and child to test relationships

        bai_yun = engine.execute(Animal.insert(), Species='Ape',
                Name='Bai Yun', Legs=2).inserted_primary_key[0]
        engine.execute(Animal.insert(inline=True), Species='Ape',
                Name='Hua Mei', Legs=2, MotherID=bai_yun)

    def test_baseline_2_insert(self):
        Animal = metadata.tables['Animal']
        i = Animal.insert(inline=True)
        for x in range(ITERATIONS):
            tick = i.execute(Species='Tick', Name='Tick %d' % x,
                             Legs=8)

    def test_baseline_3_properties(self):
        Zoo = metadata.tables['Zoo']
        Animal = metadata.tables['Animal']
        engine = metadata.bind

        def fullobject(select):
            """Iterate over the full result row."""

            return list(engine.execute(select).first())

        for x in range(ITERATIONS):

            # Zoos

            WAP = fullobject(Zoo.select(Zoo.c.Name
                             == 'Wild Animal Park'))
            SDZ = fullobject(Zoo.select(Zoo.c.Founded
                             == datetime.date(1935, 9, 13)))
            Biodome = fullobject(Zoo.select(Zoo.c.Name
                                 == 'Montr\xe9al Biod\xf4me'))
            seaworld = fullobject(Zoo.select(Zoo.c.Admission
                                  == float(60)))

            # Animals

            leopard = fullobject(Animal.select(Animal.c.Species
                                 == 'Leopard'))
            ostrich = fullobject(Animal.select(Animal.c.Species
                                 == 'Ostrich'))
            millipede = fullobject(Animal.select(Animal.c.Legs
                                   == 1000000))
            ticks = fullobject(Animal.select(Animal.c.Species == 'Tick'
                               ))

    def test_baseline_4_expressions(self):
        Zoo = metadata.tables['Zoo']
        Animal = metadata.tables['Animal']
        engine = metadata.bind

        def fulltable(select):
            """Iterate over the full result table."""

            return [list(row) for row in engine.execute(select).fetchall()]

        for x in range(ITERATIONS):
            assert len(fulltable(Zoo.select())) == 5
            assert len(fulltable(Animal.select())) == ITERATIONS + 12
            assert len(fulltable(Animal.select(Animal.c.Legs == 4))) \
                == 4
            assert len(fulltable(Animal.select(Animal.c.Legs == 2))) \
                == 5
            assert len(fulltable(Animal.select(and_(Animal.c.Legs >= 2,
                       Animal.c.Legs < 20)))) == ITERATIONS + 9
            assert len(fulltable(Animal.select(Animal.c.Legs > 10))) \
                == 2
            assert len(fulltable(Animal.select(Animal.c.Lifespan
                       > 70))) == 2
            assert len(fulltable(Animal.select(Animal.c.Species.
                        startswith('L')))) == 2
            assert len(fulltable(Animal.select(Animal.c.Species.
                        endswith('pede')))) == 2
            assert len(fulltable(Animal.select(Animal.c.LastEscape
                       != None))) == 1
            assert len(fulltable(Animal.select(None
                       == Animal.c.LastEscape))) == ITERATIONS + 11

            # In operator (containedby)

            assert len(fulltable(Animal.select(Animal.c.Species.like('%pede%'
                       )))) == 2
            assert len(fulltable(Animal.select(Animal.c.Species.in_(['Lion'
                       , 'Tiger', 'Bear'])))) == 3

            # Try In with cell references
            class thing(object):
                pass


            pet, pet2 = thing(), thing()
            pet.Name, pet2.Name = 'Slug', 'Ostrich'
            assert len(fulltable(Animal.select(Animal.c.Species.in_([pet.Name,
                       pet2.Name])))) == 2

            # logic and other functions

            assert len(fulltable(Animal.select(Animal.c.Species.like('Slug'
                       )))) == 1
            assert len(fulltable(Animal.select(Animal.c.Species.like('%pede%'
                       )))) == 2
            name = 'Lion'
            assert len(fulltable(Animal.select(func.length(Animal.c.Species)
                       == len(name)))) == ITERATIONS + 3
            assert len(fulltable(Animal.select(Animal.c.Species.like('%i%'
                       )))) == ITERATIONS + 7

            # Test now(), today(), year(), month(), day()

            assert len(fulltable(Zoo.select(and_(Zoo.c.Founded != None,
                       Zoo.c.Founded
                       < func.current_timestamp(_type=Date))))) == 3
            assert len(fulltable(Animal.select(Animal.c.LastEscape
                       == func.current_timestamp(_type=Date)))) == 0
            assert len(fulltable(Animal.select(func.date_part('year',
                       Animal.c.LastEscape) == 2004))) == 1
            assert len(fulltable(Animal.select(func.date_part('month',
                       Animal.c.LastEscape) == 12))) == 1
            assert len(fulltable(Animal.select(func.date_part('day',
                       Animal.c.LastEscape) == 21))) == 1

    def test_baseline_5_aggregates(self):
        Animal = metadata.tables['Animal']
        Zoo = metadata.tables['Zoo']
        engine = metadata.bind

        for x in range(ITERATIONS):

            # views

            view = engine.execute(select([Animal.c.Legs])).fetchall()
            legs = [x[0] for x in view]
            legs.sort()
            expected = {
                'Leopard': 73.5,
                'Slug': .75,
                'Tiger': None,
                'Lion': None,
                'Bear': None,
                'Ostrich': 103.2,
                'Centipede': None,
                'Emperor Penguin': None,
                'Adelie Penguin': None,
                'Millipede': None,
                'Ape': None,
                'Tick': None,
                }
            for species, lifespan in engine.execute(select([Animal.c.Species,
                    Animal.c.Lifespan])).fetchall():
                assert lifespan == expected[species]
            expected = ['Montr\xe9al Biod\xf4me', 'Wild Animal Park']
            e = select([Zoo.c.Name], and_(Zoo.c.Founded != None,
                       Zoo.c.Founded <= func.current_timestamp(),
                       Zoo.c.Founded >= datetime.date(1990, 1, 1)))
            values = [val[0] for val in engine.execute(e).fetchall()]
            assert set(values) == set(expected)

            # distinct

            legs = [x[0] for x in engine.execute(select([Animal.c.Legs],
                    distinct=True)).fetchall()]
            legs.sort()

    def test_baseline_6_editing(self):
        Zoo = metadata.tables['Zoo']
        engine = metadata.bind
        for x in range(ITERATIONS):

            # Edit

            SDZ = engine.execute(Zoo.select(Zoo.c.Name == 'San Diego Zoo'
                             )).first()
            engine.execute(Zoo.update(Zoo.c.ID == SDZ['ID'
                       ]), Name='The San Diego Zoo',
                                  Founded=datetime.date(1900, 1, 1),
                                  Opens=datetime.time(7, 30, 0),
                                  Admission='35.00')

            # Test edits

            SDZ = engine.execute(Zoo.select(Zoo.c.Name == 'The San Diego Zoo'
                             )).first()
            assert SDZ['Founded'] == datetime.date(1900, 1, 1), \
                SDZ['Founded']

            # Change it back

            engine.execute(Zoo.update(Zoo.c.ID == SDZ['ID'
                       ]), Name='San Diego Zoo',
                                  Founded=datetime.date(1935, 9, 13),
                                  Opens=datetime.time(9, 0, 0),
                                  Admission='0')

            # Test re-edits

            SDZ = engine.execute(Zoo.select(Zoo.c.Name == 'San Diego Zoo'
                             )).first()
            assert SDZ['Founded'] == datetime.date(1935, 9, 13)

    def test_baseline_7_multiview(self):
        Zoo = metadata.tables['Zoo']
        Animal = metadata.tables['Animal']
        engine = metadata.bind

        def fulltable(select):
            """Iterate over the full result table."""

            return [list(row) for row in engine.execute(select).fetchall()]

        for x in range(ITERATIONS):
            za = fulltable(select([Zoo.c.ID] + list(Animal.c),
                           Zoo.c.Name == 'San Diego Zoo',
                           from_obj=[join(Zoo, Animal)]))
            SDZ = Zoo.select(Zoo.c.Name == 'San Diego Zoo')
            e = fulltable(select([Zoo.c.ID, Animal.c.ID],
                          and_(Zoo.c.Name == 'San Diego Zoo',
                          Animal.c.Species == 'Leopard'),
                          from_obj=[join(Zoo, Animal)]))

            # Now try the same query with INNER, LEFT, and RIGHT JOINs.

            e = fulltable(select([Zoo.c.Name, Animal.c.Species],
                          from_obj=[join(Zoo, Animal)]))
            e = fulltable(select([Zoo.c.Name, Animal.c.Species],
                          from_obj=[outerjoin(Zoo, Animal)]))
            e = fulltable(select([Zoo.c.Name, Animal.c.Species],
                          from_obj=[outerjoin(Animal, Zoo)]))

    def test_baseline_8_drop(self):
        metadata.drop_all()

    # Now, run all of these tests again with the DB-API driver factored
    # out: the ReplayableSession playback stands in for the database.
    #
    # How awkward is this in a unittest framework?  Very.

    def test_profile_0(self):
        global metadata
        player = lambda : dbapi_session.player()
        engine = create_engine('postgresql:///', creator=player,
                        use_native_hstore=False)
        metadata = MetaData(engine)
        engine.connect()

    def test_profile_1_create_tables(self):
        self.test_baseline_1_create_tables()

    @profiling.function_call_count()
    def test_profile_1a_populate(self):
        self.test_baseline_1a_populate()

    @profiling.function_call_count()
    def test_profile_2_insert(self):
        self.test_baseline_2_insert()

    @profiling.function_call_count()
    def test_profile_3_properties(self):
        self.test_baseline_3_properties()

    @profiling.function_call_count()
    def test_profile_4_expressions(self):
        self.test_baseline_4_expressions()

    @profiling.function_call_count()
    def test_profile_5_aggregates(self):
        self.test_baseline_5_aggregates()

    @profiling.function_call_count()
    def test_profile_6_editing(self):
        self.test_baseline_6_editing()

    @profiling.function_call_count()
    def test_profile_7_multiview(self):
        self.test_baseline_7_multiview()

    def test_profile_8_drop(self):
        self.test_baseline_8_drop()
