=============
Flask-WebTest
=============
.. currentmodule:: flask.ext.webtest

.. contents::
   :local:

Overview
========

Flask-WebTest provides a set of utilities to ease testing `Flask`_
applications with `WebTest`_.

* :class:`.TestApp` extends :class:`webtest.TestApp`'s response by adding fields that
  provide access to the template contexts, session data and flashed messages.
* :class:`SessionScope` and :func:`get_scopefunc` allow to manage SQLAlchemy session
  scoping ―  it's very useful for testing.

Installation
============

``pip install flask-webtest``

Example of usage
================

::

    from unittest import TestCase
    from flask.ext.webtest import TestApp
    from main import app, db

    class ExampleTest(TestCase):
        def setUp(self):
            self.app = app
            self.w = TestApp(self.app, db=db, use_session_scopes=True)

        def test(self):
            r = self.w.get('/')
            # Assert there was no messages flushed:
            self.assertFalse(r.flashes)
            # Access and check any variable from template context...
            self.assertEqual(r.context['text'], 'Hello!')
            self.assertEqual(r.template, 'template.html')
            # ...and from session
            self.assertNotIn('user_id', r.session)

Using Flask-WebTest with Flask-SQLAlchemy
=========================================

Let's suppose there is a simple application consisting of two views (and `User` model which
is omitted for brevity):

::

    app = Flask(__name__)
    db = SQLAlchemy(app)
    
    @app.route('/user/<int:id>/')
    def user(id):
        return User.query.get_or_404(id).greet()
    
    @app.route('/user/<int:id>/preview/', methods=['POST'])
    def preview(id):
        user = User.query.get_or_404(id)
        user.greeting = request.form['name']
        # Expunge `user` from the session so that we can
        # call `db.session.commit` later and do not change
        # user data in table
        db.session.expunge(user)
        return user.greet()

How can one test it using WebTest?
An approach that comes to mind first may look as follows:

::

    class Test(TestCase):
        def setUp(self):
            self.w = TestApp(self.app)
            self.app_context = app.app_context()
            self.app_context.push()
            db.create_all()
    
        def tearDown(self):
            db.drop_all()
            self.app_context.pop()
    
        def test(self):
            user = User(name='Anton')
            db.session.add(user)
            db.session.commit()
            r = self.w.get('/user/%i/' % user.id)
            self.assertEqual(r.body, 'Hello, Anton!')

Everything looks good, but sometimes strange (at first sight) things happen:

* Uncommitted changes happen to be used to build the response:

  ::

      user.name = 'Petr'
      # Note: we did not commit the change to `user`!
      r = self.w.get('/user/%i/' % user.id)
        
      self.assertEqual(r.body, 'Hello, Anton!')
      # AssertionError: 'Hello, Petr!' != 'Hello, Anton!'

* Model disappears from the session after request:

  ::

      r = self.w.post('/user/%i/preview/' % user.id, {
          'greeting': 'Hi, %s.',    
      })
      self.assertEqual(r.body, 'Hi, Anton.')

      db.session.refresh(user)
      # InvalidRequestError: Instance '<User at 0xa8c0e8c>' is 
      # not persistent within this session

* And so on.

These examples may seem a bit contrived, but they will likely arise in your project as it
uses the ORM more extensively.

Why do they appear? Because we use the same SQLAlchemy session in our test and application code.

Any time you call ``db.session`` it passes the call to the session
bound to the current scope (which is defined by ``scopefunc``).
By default, Flask-SQLAlchemy defines ``scopefunc`` to return current thread's identity.

In production normally:

1. Only one request being handled at a time within each thread;
2. The session being opened when ``db.session`` is called the first time;
3. Flask-SQLAlchemy closes the session after request (exactly on application teardown).

Providing that, the application uses a separate session during each request.
The session is opened at the start and closed at the end of the request.

In the current tests' implementation:

1. Every request being handled in the same thread, hence using the same SQLAlchemy session;
2. The session being opened the first time ``db.session`` is called, and it happens
   when the test loads fixtures;
3. Flask-SQLAlchemy closes the session on application teardown. It happens
   only in ``tearDown`` method ― when the last context leaves the
   application contexts' stack.

So, the situation is very different: the same SQLAlchemy session is being used
to handle all the requests made during test. This is a major difference from
how things work in production and it would be great to eliminate it.

Flask-WebTest provides means to easily manage SQLAlchemy scopes:
``SQLAlchemyScope`` that you can enter and exit and custom ``scopefunc``
that has to be used during testing.

How to make use of them:

1. Replace default ``scopefunc`` with ``SQLAlchemyScope``-aware ``scopefunc`` from Flask-WebTest:
    
   ::

      from flask.ext.webtest import get_scopefunc
        
      def make_db(app):
          session_options = {}
          if app.testing:
              session_options['scopefunc'] = get_scopefunc()
          return SQLAlchemy(app, session_options=session_options)
        
      app = Flask(__name__)
      ...
      db = make_db(app)

2. Whenever you want a piece of code to use a new SQLAlchemy session, execute it within a scope:

   ::

      user = User(name='Anton')
      db.session.add(user)
      db.session.commit()
      print user in db.session  # True
        
      with SessionScope(db):
          # Brand new session!
          print user in db.session  # False 
   or
   
   ::

      scope = SessionScope(db)
      scope.push()
      try:
          ...    
      finally:
          scope.pop()

It makes sense to use a fresh SQLAlchemyScope for every request.
:class:`.TestApp` will do it for you if you pass `db` to it's
constructor and specify `use_session_scopes`.

If your project uses Celery (or other task queue) and
performs tasks synchronously during tests ― it's a great idea
to run them within separate scopes too.

.. note::

    Be aware that model is bound to the session and
    in general you can't use object whose session was removed:

    ::

        with SessionScope(db):
            john = User(name='John')
            db.session.add(john)
            # Note: commit expires all models (SQLAlchemy has
            # expire_on_commit=True by default)...
            db.session.commit()

        print john in db.session  # False
        
        # Any call to an expired model requires database hit, so
        # `print john.name` would cause the following error:
        #
        # DetachedInstanceError: Instance <User at 0x95c756c>
        # is not bound to a Session; attribute refresh
        # operation cannot proceed
        #
        # It would happen because `john`'s session no longer exists.
        # To continue working with detached object, we need to
        # reconcile it with the current session:
        john = db.session.merge(john)
        
        print john in db.session  # True
        print john.name  # John

Dealing with transaction isolation levels 
-----------------------------------------

Using a high isolation level may cause some inconveniences during testing.
Consider this example:

::
    
    # Current session represents transaction X
    user = User.query.filter(User.name == 'Anton').first()

    with SessionScope(db):
        # Now current session represents transaction Y
        user_copy = User.query.filter(User.name == 'Anton').first()
        user_copy.name = 'Petr'
        db.session.add(user_copy)
        db.session.commit()

    # Again, current session represents transaction X
    db.session.refresh(layout)
    self.assertEqual(layout.name, 'Petr')

The last assertion would fail if ``REPEATABLE READ`` level is being used,
because transaction ``X`` is isolated from any changes made by transaction ``Y``.

To make changes from ``Y`` visible you need to either commit or rollback ``X``:

::
    
    ...

    # Again, current session represents transaction X
    db.session.rollback()
    self.assertEqual(layout.name, 'Petr')  # Yay!


If it's acceptable, you can just lower the isolation level to ``READ COMMITTED``
and avoid thinking about this issue:

::

    from flask.ext.sqlalchemy import SQLAlchemy as BaseSQLAlchemy

    class SQLAlchemy(BaseSQLAlchemy):
        def apply_driver_hacks(self, app, info, options):
            if 'isolation_level' not in options:
                options['isolation_level'] = 'READ COMMITTED'
            return super(SQLAlchemy, self).apply_driver_hacks(
                app, info, options)


API Documentation
=================

This documentation is automatically generated from Flask-WebTest's source code.

.. autoclass:: TestApp
   
    .. automethod:: session_transaction


API related to Flask-SQLAlchemy 
-------------------------------
.. autofunction:: get_scopefunc

.. autoclass:: SessionScope

   .. automethod:: push

   .. automethod:: pop

.. _WebTest: http://webtest.readthedocs.org/
.. _Flask: http://flask.pocoo.org/
