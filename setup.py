from setuptools import setup

setup(
    name='Flask-WebTest',
    version='0.0.2',
    url='https://github.com/aromanovich/flask-webtest',
    license='BSD',
    description = 'Utilities for testing Flask applications with WebTest.',
    author='Anton Romanovich',
    author_email='anthony.romanovich@gmail.com',
    py_modules=['flask_webtest'],
    install_requires=[
        'Flask>=0.6',
        'WebTest',
        'blinker',
    ],
    classifiers=[
        'Topic :: Software Development :: Testing',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
    ],
)
