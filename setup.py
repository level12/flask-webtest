"""
Flask-WebTest
-------------

Provides a set of utilities to ease testing Flask applications with WebTest.

Links
`````

* `documentation <http://flask-webtest.readthedocs.org/en/latest/>`_
* `development version
  <http://github.com/aromanovich/flask-webtest/zipball/master#egg=Flask-WebTest-dev>`_
"""
from setuptools import setup


setup(
    name='Flask-WebTest',
    version='0.0.7',
    url='https://github.com/aromanovich/flask-webtest',
    license='BSD',
    description = 'Utilities for testing Flask applications with WebTest.',
    long_description=__doc__,
    author='Anton Romanovich',
    author_email='anthony.romanovich@gmail.com',
    py_modules=['flask_webtest'],
    test_suite='tests.test',
    tests_require=['Flask-SQLAlchemy'],
    zip_safe=False,
    install_requires=[
        'Flask>=0.8',
        'WebTest',
        'blinker',
    ],
    classifiers=[
        'Topic :: Software Development :: Testing',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
    ],
)
