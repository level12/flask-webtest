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
from setuptools import setup, find_packages


setup(
    name='Flask-WebTest',
    version='0.1.0',
    url='https://github.com/aromanovich/flask-webtest',
    license='BSD',
    description = 'Utilities for testing Flask applications with WebTest.',
    long_description=__doc__,
    author='Anton Romanovich',
    author_email='anthony.romanovich@gmail.com',
    include_package_data=True,
    packages=find_packages(exclude=[]),
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
