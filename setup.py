"""setup.py

Please see README for basic installation instructions.

"""

import os
import re
import sys
try:
    from setuptools import setup
    has_setuptools = True
except ImportError:
    has_setuptools = False
    from distutils.core import setup

cmdclass = {}
pypy = hasattr(sys, 'pypy_version_info')
jython = sys.platform.startswith('java')
py3k = False
extra = {}
if sys.version_info < (2, 6):
    raise Exception("SQLAlchemy requires Python 2.6 or higher.")
elif sys.version_info >= (3, 0):
    py3k = True

def status_msgs(*msgs):
    print('*' * 75)
    for msg in msgs:
        print(msg)
    print('*' * 75)

def find_packages(location):
    packages = []
    for pkg in ['sqlalchemy']:
        for _dir, subdirectories, files in (
                os.walk(os.path.join(location, pkg))):
            if '__init__.py' in files:
                tokens = _dir.split(os.sep)[len(location.split(os.sep)):]
                packages.append(".".join(tokens))
    return packages

v_file = open(os.path.join(os.path.dirname(__file__),
                        'lib', 'sqlalchemy', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'",
                     re.S).match(v_file.read()).group(1)
v_file.close()

r_file = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = r_file.read()
r_file.close()


def run_setup():
    kwargs = extra.copy()

    setup(name="SQLAlchemy",
        version=VERSION,
        description="Database Abstraction Library",
        author="Mike Bayer",
        author_email="mike_mp@zzzcomputing.com",
        url="http://www.sqlalchemy.org",
        packages=find_packages('lib'),
        package_dir={'': 'lib'},
        license="MIT License",
        cmdclass=cmdclass,
        tests_require=['pytest >= 2.5.2', 'mock'],
        test_suite="pytest.main",
        long_description=readme,
        extras_require=dict(
            speedups=['sqlalchemy-speedups>=1.0,<2.0'],
        ),
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: Jython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Database :: Front-Ends",
            "Operating System :: OS Independent",
            ],
            **kwargs
          )

run_setup()
