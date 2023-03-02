"""
Flask-WebTest
-------------

Provides a set of utilities to ease testing Flask applications with WebTest.

Links
`````

* `documentation <http://flask-webtest.readthedocs.org/en/latest/>`_
* `development version
  <http://github.com/level12/flask-webtest/zipball/master#egg=Flask-WebTest-dev>`_
"""
import os.path as osp
from setuptools import setup

cdir = osp.abspath(osp.dirname(__file__))
version_fpath = osp.join(cdir, 'version.py')
version_globals = {}
with open(version_fpath) as fo:
    exec(fo.read(), version_globals)

setup(
    name='Flask-WebTest',
    version=version_globals['VERSION'],
    url='https://github.com/level12/flask-webtest',
    license='BSD',
    description = 'Utilities for testing Flask applications with WebTest.',
    long_description=__doc__,
    author='Anton Romanovich',
    author_email='anthony.romanovich@gmail.com',
    include_package_data=True,
    py_modules=['flask_webtest'],
    zip_safe=False,
    install_requires=[
        'Flask>=1.1.0',
        'WebTest',
        'blinker',
    ],
    extras_require={
        'tests': [
            'flask-sqlalchemy',
        ],
    },
    classifiers=[
        'Topic :: Software Development :: Testing',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
)
