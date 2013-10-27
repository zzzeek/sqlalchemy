.. _overview_toplevel:

========
Overview
========

.. _overview:

Overview
========

The SQLAlchemy SQL Toolkit and Object Relational Mapper
is a comprehensive set of tools for working with
databases and Python. It has several distinct areas of
functionality which can be used individually or combined
together. Its major components are illustrated in below,
with component dependencies organized into layers:

.. image:: sqla_arch_small.png

Above, the two most significant front-facing portions of
SQLAlchemy are the **Object Relational Mapper** and the
**SQL Expression Language**. SQL Expressions can be used
independently of the ORM. When using the ORM, the SQL
Expression language remains part of the public facing API
as it is used within object-relational configurations and
queries.

.. _doc_overview:

Documentation Overview
======================

The documentation is separated into three sections: :ref:`orm_toplevel`,
:ref:`core_toplevel`, and :ref:`dialect_toplevel`.

In :ref:`orm_toplevel`, the Object Relational Mapper is introduced and fully
described. New users should begin with the :ref:`ormtutorial_toplevel`. If you
want to work with higher-level SQL which is constructed automatically for you,
as well as management of Python objects, proceed to this tutorial.

In :ref:`core_toplevel`, the breadth of SQLAlchemy's SQL and database
integration and description services are documented, the core of which is the
SQL Expression language. The SQL Expression Language is a toolkit all its own,
independent of the ORM package, which can be used to construct manipulable SQL
expressions which can be programmatically constructed, modified, and executed,
returning cursor-like result sets. In contrast to the ORM's domain-centric
mode of usage, the expression language provides a schema-centric usage
paradigm. New users should begin here with :ref:`sqlexpression_toplevel`.
SQLAlchemy engine, connection, and pooling services are also described in
:ref:`core_toplevel`.

In :ref:`dialect_toplevel`, reference documentation for all provided
database and DBAPI backends is provided.

Code Examples
=============

Working code examples, mostly regarding the ORM, are included in the
SQLAlchemy distribution. A description of all the included example
applications is at :ref:`examples_toplevel`.

There is also a wide variety of examples involving both core SQLAlchemy
constructs as well as the ORM on the wiki.  See
`Theatrum Chemicum <http://www.sqlalchemy.org/trac/wiki/UsageRecipes>`_.

.. _installation:

Installation Guide
==================

Supported Platforms
-------------------

SQLAlchemy has been tested against the following platforms:

* cPython since version 2.6, through the 2.xx series
* cPython version 3, throughout all 3.xx series
* `Pypy <http://pypy.org/>`_ 2.1 or greater

.. versionchanged:: 0.9
   Python 2.6 is now the minimum Python version supported.

Supported Installation Methods
-------------------------------

SQLAlchemy supports installation using standard Python "distutils" or
"setuptools" methodologies. An overview of potential setups is as follows:

* **Plain Python Distutils** - SQLAlchemy can be installed with a clean
  Python install using the services provided via `Python Distutils <http://docs.python.org/distutils/>`_,
  using the ``setup.py`` script. The C extensions as well as Python 3 builds are supported.
* **Setuptools or Distribute** - When using `setuptools <http://pypi.python.org/pypi/setuptools/>`_,
  SQLAlchemy can be installed via ``setup.py`` or ``easy_install``, and the C
  extensions are supported.  
* **pip** - `pip <http://pypi.python.org/pypi/pip/>`_ is an installer that
  rides on top of ``setuptools`` or ``distribute``, replacing the usage
  of ``easy_install``.  It is often preferred for its simpler mode of usage.

Install via easy_install or pip
-------------------------------

When ``easy_install`` or ``pip`` is available, the distribution can be
downloaded from Pypi and installed in one step::

    easy_install SQLAlchemy

Or with pip::

    pip install SQLAlchemy

This command will download the latest version of SQLAlchemy from the `Python
Cheese Shop <http://pypi.python.org/pypi/SQLAlchemy>`_ and install it to your system.

.. note::
	
    Beta releases of SQLAlchemy may not be present on Pypi, and may instead
    require a direct download first.

Installing using setup.py
----------------------------------

Otherwise, you can install from the distribution using the ``setup.py`` script::

    python setup.py install

Installing the C Extensions
----------------------------------

SQLAlchemy includes C extensions which provide an extra speed boost for
dealing with result sets.   The extensions are supported on both the 2.xx
and 3.xx series of cPython.

.. versionchanged:: 0.9.0

    The C extensions now compile on Python 3 as well as Python 2.

setup.py will automatically build the extensions if an appropriate platform is
detected. If the build of the C extensions fails, due to missing compiler or
other issue, the setup process will output a warning message, and re-run the
build without the C extensions, upon completion reporting final status.

To run the build/install without even attempting to compile the C extensions,
pass the flag ``--without-cextensions`` to the ``setup.py`` script::

    python setup.py --without-cextensions install

Or with pip::

    pip install --global-option='--without-cextensions' SQLAlchemy

.. note::

   The ``--without-cextensions`` flag is available **only** if ``setuptools``
   or ``distribute`` is installed.  It is not available on a plain Python ``distutils``
   installation.  The library will still install without the C extensions if they
   cannot be built, however.

Installing on Python 3
----------------------------------

SQLAlchemy runs directly on Python 2 or Python 3, and can be installed in
either environment without any adjustments or code conversion.

.. versionchanged:: 0.9.0 Python 3 is now supported in place with no 2to3 step
   required.


Installing a Database API
----------------------------------

SQLAlchemy is designed to operate with a :term:`DBAPI` implementation built for a
particular database, and includes support for the most popular databases.
The individual database sections in :doc:`/dialects/index` enumerate
the available DBAPIs for each database, including external links.

Checking the Installed SQLAlchemy Version
------------------------------------------

This documentation covers SQLAlchemy version 0.9. If you're working on a
system that already has SQLAlchemy installed, check the version from your
Python prompt like this:

.. sourcecode:: python+sql

     >>> import sqlalchemy
     >>> sqlalchemy.__version__ # doctest: +SKIP
     0.9.0

.. _migration:

0.8 to 0.9 Migration
=====================

Notes on what's changed from 0.8 to 0.9 is available here at :doc:`changelog/migration_09`.
