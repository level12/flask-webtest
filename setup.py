from setuptools import setup

setup(
    name='Flask-WebTest',
    version='0.0.1',
    url='https://github.com/aromanovich/flask-webtest',
    license='BSD',
    author='Anton Romanovich',
    author_email='anthony.romanovich@gmail.com',
    description='WebTest integration for Flask.',
    py_modules=['flask_webtest'],
    install_requires=[
        'Flask>=0.6',
        'WebTest',
        'blinker',
    ],
)
