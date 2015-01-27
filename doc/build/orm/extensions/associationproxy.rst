.. _associationproxy_toplevel:

Association Proxy
=================

.. module:: sqlalchemy.ext.associationproxy

``associationproxy`` is used to create a read/write view of a
target attribute across a relationship.  It essentially conceals
the usage of a "middle" attribute between two endpoints, and
can be used to cherry-pick fields from a collection of
related objects or to reduce the verbosity of using the association
object pattern.   Applied creatively, the association proxy allows
the construction of sophisticated collections and dictionary
views of virtually any geometry, persisted to the database using
standard, transparently configured relational patterns.


Simplifying Scalar Collections
------------------------------

Consider a many-to-many mapping between two classes, ``User`` and ``Keyword``.
Each ``User`` can have any number of ``Keyword`` objects, and vice-versa
(the many-to-many pattern is described at :ref:`relationships_many_to_many`)::

    from sqlalchemy import Column, Integer, String, ForeignKey, Table
    from sqlalchemy.orm import relationship
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(String(64))
        kw = relationship("Keyword", secondary=lambda: userkeywords_table)

        def __init__(self, name):
            self.name = name

    class Keyword(Base):
        __tablename__ = 'keyword'
        id = Column(Integer, primary_key=True)
        keyword = Column('keyword', String(64))

        def __init__(self, keyword):
            self.keyword = keyword

    userkeywords_table = Table('userkeywords', Base.metadata,
        Column('user_id', Integer, ForeignKey("user.id"),
               primary_key=True),
        Column('keyword_id', Integer, ForeignKey("keyword.id"),
               primary_key=True)
    )

Reading and manipulating the collection of "keyword" strings associated
with ``User`` requires traversal from each collection element to the ``.keyword``
attribute, which can be awkward::

    >>> user = User('jek')
    >>> user.kw.append(Keyword('cheese inspector'))
    >>> print(user.kw)
    [<__main__.Keyword object at 0x12bf830>]
    >>> print(user.kw[0].keyword)
    cheese inspector
    >>> print([keyword.keyword for keyword in user.kw])
    ['cheese inspector']

The ``association_proxy`` is applied to the ``User`` class to produce
a "view" of the ``kw`` relationship, which only exposes the string
value of ``.keyword`` associated with each ``Keyword`` object::

    from sqlalchemy.ext.associationproxy import association_proxy

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(String(64))
        kw = relationship("Keyword", secondary=lambda: userkeywords_table)

        def __init__(self, name):
            self.name = name

        # proxy the 'keyword' attribute from the 'kw' relationship
        keywords = association_proxy('kw', 'keyword')

We can now reference the ``.keywords`` collection as a listing of strings,
which is both readable and writable.  New ``Keyword`` objects are created
for us transparently::

    >>> user = User('jek')
    >>> user.keywords.append('cheese inspector')
    >>> user.keywords
    ['cheese inspector']
    >>> user.keywords.append('snack ninja')
    >>> user.kw
    [<__main__.Keyword object at 0x12cdd30>, <__main__.Keyword object at 0x12cde30>]

The :class:`.AssociationProxy` object produced by the :func:`.association_proxy` function
is an instance of a `Python descriptor <http://docs.python.org/howto/descriptor.html>`_.
It is always declared with the user-defined class being mapped, regardless of
whether Declarative or classical mappings via the :func:`.mapper` function are used.

The proxy functions by operating upon the underlying mapped attribute
or collection in response to operations, and changes made via the proxy are immediately
apparent in the mapped attribute, as well as vice versa.   The underlying
attribute remains fully accessible.

When first accessed, the association proxy performs introspection
operations on the target collection so that its behavior corresponds correctly.
Details such as if the locally proxied attribute is a collection (as is typical)
or a scalar reference, as well as if the collection acts like a set, list,
or dictionary is taken into account, so that the proxy should act just like
the underlying collection or attribute does.

Creation of New Values
-----------------------

When a list append() event (or set add(), dictionary __setitem__(), or scalar
assignment event) is intercepted by the association proxy, it instantiates a
new instance of the "intermediary" object using its constructor, passing as a
single argument the given value. In our example above, an operation like::

    user.keywords.append('cheese inspector')

Is translated by the association proxy into the operation::

    user.kw.append(Keyword('cheese inspector'))

The example works here because we have designed the constructor for ``Keyword``
to accept a single positional argument, ``keyword``.   For those cases where a
single-argument constructor isn't feasible, the association proxy's creational
behavior can be customized using the ``creator`` argument, which references a
callable (i.e. Python function) that will produce a new object instance given the
singular argument.  Below we illustrate this using a lambda as is typical::

    class User(Base):
        # ...

        # use Keyword(keyword=kw) on append() events
        keywords = association_proxy('kw', 'keyword',
                        creator=lambda kw: Keyword(keyword=kw))

The ``creator`` function accepts a single argument in the case of a list-
or set- based collection, or a scalar attribute.  In the case of a dictionary-based
collection, it accepts two arguments, "key" and "value".   An example
of this is below in :ref:`proxying_dictionaries`.

Simplifying Association Objects
-------------------------------

The "association object" pattern is an extended form of a many-to-many
relationship, and is described at :ref:`association_pattern`. Association
proxies are useful for keeping "association objects" out the way during
regular use.

Suppose our ``userkeywords`` table above had additional columns
which we'd like to map explicitly, but in most cases we don't
require direct access to these attributes.  Below, we illustrate
a new mapping which introduces the ``UserKeyword`` class, which
is mapped to the ``userkeywords`` table illustrated earlier.
This class adds an additional column ``special_key``, a value which
we occasionally want to access, but not in the usual case.   We
create an association proxy on the ``User`` class called
``keywords``, which will bridge the gap from the ``user_keywords``
collection of ``User`` to the ``.keyword`` attribute present on each
``UserKeyword``::

    from sqlalchemy import Column, Integer, String, ForeignKey
    from sqlalchemy.orm import relationship, backref

    from sqlalchemy.ext.associationproxy import association_proxy
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(String(64))

        # association proxy of "user_keywords" collection
        # to "keyword" attribute
        keywords = association_proxy('user_keywords', 'keyword')

        def __init__(self, name):
            self.name = name

    class UserKeyword(Base):
        __tablename__ = 'user_keyword'
        user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
        keyword_id = Column(Integer, ForeignKey('keyword.id'), primary_key=True)
        special_key = Column(String(50))

        # bidirectional attribute/collection of "user"/"user_keywords"
        user = relationship(User,
                    backref=backref("user_keywords",
                                    cascade="all, delete-orphan")
                )

        # reference to the "Keyword" object
        keyword = relationship("Keyword")

        def __init__(self, keyword=None, user=None, special_key=None):
            self.user = user
            self.keyword = keyword
            self.special_key = special_key

    class Keyword(Base):
        __tablename__ = 'keyword'
        id = Column(Integer, primary_key=True)
        keyword = Column('keyword', String(64))

        def __init__(self, keyword):
            self.keyword = keyword

        def __repr__(self):
            return 'Keyword(%s)' % repr(self.keyword)

With the above configuration, we can operate upon the ``.keywords``
collection of each ``User`` object, and the usage of ``UserKeyword``
is concealed::

    >>> user = User('log')
    >>> for kw in (Keyword('new_from_blammo'), Keyword('its_big')):
    ...     user.keywords.append(kw)
    ...
    >>> print(user.keywords)
    [Keyword('new_from_blammo'), Keyword('its_big')]

Where above, each ``.keywords.append()`` operation is equivalent to::

    >>> user.user_keywords.append(UserKeyword(Keyword('its_heavy')))

The ``UserKeyword`` association object has two attributes here which are populated;
the ``.keyword`` attribute is populated directly as a result of passing
the ``Keyword`` object as the first argument.   The ``.user`` argument is then
assigned as the ``UserKeyword`` object is appended to the ``User.user_keywords``
collection, where the bidirectional relationship configured between ``User.user_keywords``
and ``UserKeyword.user`` results in a population of the ``UserKeyword.user`` attribute.
The ``special_key`` argument above is left at its default value of ``None``.

For those cases where we do want ``special_key`` to have a value, we
create the ``UserKeyword`` object explicitly.  Below we assign all three
attributes, where the assignment of ``.user`` has the effect of the ``UserKeyword``
being appended to the ``User.user_keywords`` collection::

    >>> UserKeyword(Keyword('its_wood'), user, special_key='my special key')

The association proxy returns to us a collection of ``Keyword`` objects represented
by all these operations::

    >>> user.keywords
    [Keyword('new_from_blammo'), Keyword('its_big'), Keyword('its_heavy'), Keyword('its_wood')]

.. _proxying_dictionaries:

Proxying to Dictionary Based Collections
-----------------------------------------

The association proxy can proxy to dictionary based collections as well.   SQLAlchemy
mappings usually use the :func:`.attribute_mapped_collection` collection type to
create dictionary collections, as well as the extended techniques described in
:ref:`dictionary_collections`.

The association proxy adjusts its behavior when it detects the usage of a
dictionary-based collection. When new values are added to the dictionary, the
association proxy instantiates the intermediary object by passing two
arguments to the creation function instead of one, the key and the value. As
always, this creation function defaults to the constructor of the intermediary
class, and can be customized using the ``creator`` argument.

Below, we modify our ``UserKeyword`` example such that the ``User.user_keywords``
collection will now be mapped using a dictionary, where the ``UserKeyword.special_key``
argument will be used as the key for the dictionary.   We then apply a ``creator``
argument to the ``User.keywords`` proxy so that these values are assigned appropriately
when new elements are added to the dictionary::

    from sqlalchemy import Column, Integer, String, ForeignKey
    from sqlalchemy.orm import relationship, backref
    from sqlalchemy.ext.associationproxy import association_proxy
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm.collections import attribute_mapped_collection

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(String(64))

        # proxy to 'user_keywords', instantiating UserKeyword
        # assigning the new key to 'special_key', values to
        # 'keyword'.
        keywords = association_proxy('user_keywords', 'keyword',
                        creator=lambda k, v:
                                    UserKeyword(special_key=k, keyword=v)
                    )

        def __init__(self, name):
            self.name = name

    class UserKeyword(Base):
        __tablename__ = 'user_keyword'
        user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
        keyword_id = Column(Integer, ForeignKey('keyword.id'), primary_key=True)
        special_key = Column(String)

        # bidirectional user/user_keywords relationships, mapping
        # user_keywords with a dictionary against "special_key" as key.
        user = relationship(User, backref=backref(
                        "user_keywords",
                        collection_class=attribute_mapped_collection("special_key"),
                        cascade="all, delete-orphan"
                        )
                    )
        keyword = relationship("Keyword")

    class Keyword(Base):
        __tablename__ = 'keyword'
        id = Column(Integer, primary_key=True)
        keyword = Column('keyword', String(64))

        def __init__(self, keyword):
            self.keyword = keyword

        def __repr__(self):
            return 'Keyword(%s)' % repr(self.keyword)

We illustrate the ``.keywords`` collection as a dictionary, mapping the
``UserKeyword.string_key`` value to ``Keyword`` objects::

    >>> user = User('log')

    >>> user.keywords['sk1'] = Keyword('kw1')
    >>> user.keywords['sk2'] = Keyword('kw2')

    >>> print(user.keywords)
    {'sk1': Keyword('kw1'), 'sk2': Keyword('kw2')}

.. _composite_association_proxy:

Composite Association Proxies
-----------------------------

Given our previous examples of proxying from relationship to scalar
attribute, proxying across an association object, and proxying dictionaries,
we can combine all three techniques together to give ``User``
a ``keywords`` dictionary that deals strictly with the string value
of ``special_key`` mapped to the string ``keyword``.  Both the ``UserKeyword``
and ``Keyword`` classes are entirely concealed.  This is achieved by building
an association proxy on ``User`` that refers to an association proxy
present on ``UserKeyword``::

    from sqlalchemy import Column, Integer, String, ForeignKey
    from sqlalchemy.orm import relationship, backref

    from sqlalchemy.ext.associationproxy import association_proxy
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm.collections import attribute_mapped_collection

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)
        name = Column(String(64))

        # the same 'user_keywords'->'keyword' proxy as in
        # the basic dictionary example
        keywords = association_proxy(
                    'user_keywords',
                    'keyword',
                    creator=lambda k, v:
                                UserKeyword(special_key=k, keyword=v)
                    )

        def __init__(self, name):
            self.name = name

    class UserKeyword(Base):
        __tablename__ = 'user_keyword'
        user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
        keyword_id = Column(Integer, ForeignKey('keyword.id'),
                                                        primary_key=True)
        special_key = Column(String)
        user = relationship(User, backref=backref(
                "user_keywords",
                collection_class=attribute_mapped_collection("special_key"),
                cascade="all, delete-orphan"
                )
            )

        # the relationship to Keyword is now called
        # 'kw'
        kw = relationship("Keyword")

        # 'keyword' is changed to be a proxy to the
        # 'keyword' attribute of 'Keyword'
        keyword = association_proxy('kw', 'keyword')

    class Keyword(Base):
        __tablename__ = 'keyword'
        id = Column(Integer, primary_key=True)
        keyword = Column('keyword', String(64))

        def __init__(self, keyword):
            self.keyword = keyword


``User.keywords`` is now a dictionary of string to string, where
``UserKeyword`` and ``Keyword`` objects are created and removed for us
transparently using the association proxy. In the example below, we illustrate
usage of the assignment operator, also appropriately handled by the
association proxy, to apply a dictionary value to the collection at once::

    >>> user = User('log')
    >>> user.keywords = {
    ...     'sk1':'kw1',
    ...     'sk2':'kw2'
    ... }
    >>> print(user.keywords)
    {'sk1': 'kw1', 'sk2': 'kw2'}

    >>> user.keywords['sk3'] = 'kw3'
    >>> del user.keywords['sk2']
    >>> print(user.keywords)
    {'sk1': 'kw1', 'sk3': 'kw3'}

    >>> # illustrate un-proxied usage
    ... print(user.user_keywords['sk3'].kw)
    <__main__.Keyword object at 0x12ceb90>

One caveat with our example above is that because ``Keyword`` objects are created
for each dictionary set operation, the example fails to maintain uniqueness for
the ``Keyword`` objects on their string name, which is a typical requirement for
a tagging scenario such as this one.  For this use case the recipe
`UniqueObject <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/UniqueObject>`_, or
a comparable creational strategy, is
recommended, which will apply a "lookup first, then create" strategy to the constructor
of the ``Keyword`` class, so that an already existing ``Keyword`` is returned if the
given name is already present.

Querying with Association Proxies
---------------------------------

The :class:`.AssociationProxy` features simple SQL construction capabilities
which relate down to the underlying :func:`.relationship` in use as well
as the target attribute.  For example, the :meth:`.RelationshipProperty.Comparator.any`
and :meth:`.RelationshipProperty.Comparator.has` operations are available, and will produce
a "nested" EXISTS clause, such as in our basic association object example::

    >>> print(session.query(User).filter(User.keywords.any(keyword='jek')))
    SELECT user.id AS user_id, user.name AS user_name
    FROM user
    WHERE EXISTS (SELECT 1
    FROM user_keyword
    WHERE user.id = user_keyword.user_id AND (EXISTS (SELECT 1
    FROM keyword
    WHERE keyword.id = user_keyword.keyword_id AND keyword.keyword = :keyword_1)))

For a proxy to a scalar attribute, ``__eq__()`` is supported::

    >>> print(session.query(UserKeyword).filter(UserKeyword.keyword == 'jek'))
    SELECT user_keyword.*
    FROM user_keyword
    WHERE EXISTS (SELECT 1
        FROM keyword
        WHERE keyword.id = user_keyword.keyword_id AND keyword.keyword = :keyword_1)

and ``.contains()`` is available for a proxy to a scalar collection::

    >>> print(session.query(User).filter(User.keywords.contains('jek')))
    SELECT user.*
    FROM user
    WHERE EXISTS (SELECT 1
    FROM userkeywords, keyword
    WHERE user.id = userkeywords.user_id
        AND keyword.id = userkeywords.keyword_id
        AND keyword.keyword = :keyword_1)

:class:`.AssociationProxy` can be used with :meth:`.Query.join` somewhat manually
using the :attr:`~.AssociationProxy.attr` attribute in a star-args context::

    q = session.query(User).join(*User.keywords.attr)

.. versionadded:: 0.7.3
    :attr:`~.AssociationProxy.attr` attribute in a star-args context.

:attr:`~.AssociationProxy.attr` is composed of :attr:`.AssociationProxy.local_attr` and :attr:`.AssociationProxy.remote_attr`,
which are just synonyms for the actual proxied attributes, and can also
be used for querying::

    uka = aliased(UserKeyword)
    ka = aliased(Keyword)
    q = session.query(User).\
            join(uka, User.keywords.local_attr).\
            join(ka, User.keywords.remote_attr)

.. versionadded:: 0.7.3
    :attr:`.AssociationProxy.local_attr` and :attr:`.AssociationProxy.remote_attr`,
    synonyms for the actual proxied attributes, and usable for querying.

API Documentation
-----------------

.. autofunction:: association_proxy

.. autoclass:: AssociationProxy
   :members:
   :undoc-members:

.. autodata:: ASSOCIATION_PROXY
