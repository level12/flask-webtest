Flask-WebTest
=============

Flask-WebTest provides a set of utilities to ease testing Flask applications with WebTest.

``flask.ext.webtest.TestApp`` extends ``webtest.TestApp`` by adding few useful fields to response:

* ``response.templates`` ― dictionary containing information about what templates were used to build the response and what their contexts were. The keys are template names and the values are template contexts.  
  If only one template was used, it's name and context can be accessed through ``response.template`` and ``response.context``.

* ``response.flashes`` ― list of tuples (category, message) containing messages that were flashed during request.

  *Note*:  
  Fully supported only starting with Flask 0.10.  
  If you use previous version, ``response.flashes`` will contain only those messages that was consumed by ``get_flashed_messages()`` *template* calls.

* ``response.session`` ― dictionary containing session data.

Using Flask-WebTest with Flask-SQLAlchemy
-----------------------------------------

Let's suppose there is a simple application consisting of two views (and `User` model which
is omitted for brevity):

.. code:: python

    app = Flask(__name__)
    db = SQLAlchemy(app)
    
    @app.route('/user/<int:id>/')
    def user(id):
        return User.query.get_or_404(id).greet()
    
    @app.route('/user/<int:id>/preview/', methods=['POST'])
    def preview(id):
        user = User.query.get_or_404(id)
        user.greeting = request.form['name']
        # Expunge `user` from the Session so that we can call `db.session.commit`
        # later and it will not change the user data in table
        db.session.expunge(user)
        return user.greet()

How can one test it using WebTest?
An approach that comes to mind first may look as follows:

.. code:: python

    class Test(TestCase):
        def setUp(self):
            super(TestCase, self).setUp()
            self.w = TestApp(self.app)
            self.app_context = app.app_context()
            self.app_context.push()
            db.create_all()
    
        def tearDown(self):
            super(TestCase, self).tearDown()
            db.drop_all()
            self.app_context.pop()
    
        def test(self):
            user = User(name='Anton')
            db.session.add(user)
            db.session.commit()
            r = self.w.get('/user/%i/' % user.id)
            self.assertEqual(r.data, 'Hello, Anton!')

Everything looks good, but sometimes strange (at first sight) things happen:

* Uncommitted changes happen to be used to build the response:

.. code:: python

    user.name = 'Petr'
    # Note: we did not commit the change to `user`!
    r = self.w.get('/user/%i/' % user.id)
    
    self.assertEqual(r.data, 'Hello, Anton!')
    # AssertionError: 'Hello, Petr!' != 'Hello, Anton!'

* Model disappear from the Session after request:

.. code:: python

    r = self.w.post('/user/%i/preview/' % user.id, data={
        'greeting': 'Hi, %s.',    
    })
    self.assertEqual(r.data, 'Hi, Anton.')

    db.session.refresh(user)
    # InvalidRequestError: Instance '<User at 0xa8c0e8c>' is 
    # not persistent within this Session

* And so on.

These examples may seem a bit contrived, but they will likely arise in your project as it
uses the ORM more extensively.

Why do they appear? Because we use the same SQLAlchemy Session in our test and application code.

Any time you call ``db.session``, it passes the call to the Session
bound to the current scope (which is defined by ``scopefunc``).
By default, Flask-SQLAlchemy defines ``scopefunc`` to return current thread's identity.

In production, normally:

1. Only one request being handled at a time within each thread;
2. The Session being opened the first time you call ``db.session``;
3. Flask-SQLAlchemy closes the Session for you after request (more exactly,
   on application teardown).

Providing that, the application uses a new separate Session during each request.
The Session is opened at the start and closed at the end of the request.

In the current tests' implementation:

1. Every request being handled in the same thread, hence using the same SQLAlchemy Session;
2. The Session being opened the first time you call ``db.session``, and it happens
   when you load the fixtures;
3. Flask-SQLAlchemy closes the Session on application teardown. It happens
   only in ``tearDown`` method ― when the last context leaves the
   application contexts' stack.

So, the situation is very different: the same SQLAlchemy Session is being used
to handle all the requests made during test. This is a major difference from
how things work in production and it would be great to eliminate it.

Flask-WebTest provides means to easily manage SQLAlchemy scopes:
``SQLAlchemyScope`` that you can enter and exit and custom ``scopefunc``
that has to be used during testing.

How do we make use of them?

1. Replace default ``scopefunc`` with ``SQLAlchemyScope``-aware ``scopefunc`` from Flask-WebTest:

.. code:: python

    from flask.ext.webtest import scopefunc
    
    def make_db(app):
        session_options = {}
        if app.testing:
            session_options['scopefunc'] = scopefunc
        db = SQLAlchemy(app, session_options=session_options)
        return db
    
    
    app = Flask(__name__)
    ...
    db = make_db(app)

2. Whenever you want a code to use a new SQLAlchemy Session, execute it within a new SQLAlchemy scope:

.. code:: python

    user = User(name='Anton')
    db.session.add(user)
    db.session.commit()
    print user in db.session  # True
    
    with SQLAlchemyScope(db):
        # Brand new session!
        print user in db.session  # False 

or

.. code:: python

    scope = SQLAlchemyScope(db):
    scope.push()
    try:
    ...    
    finally:
        scope.pop()

It makes sense to use a fresh SQLAlchemyScope for every request.

If your project uses Celery (or other task queue) and
performs tasks synchronously during tests ― it's a great idea
to run them within separate scopes too.

And you must be aware that models bound to the Session and
in general you can't use objects whose Session was removed:

.. code:: python

    with SQLAlchemyScope(db):
        john = User(name='John')
        db.session.add(john)
        # Note: commit expires all models (SQLAlchemy has
        # expire_on_commit=True by default)...
        db.session.commit()

    print john in db.session  # False
    
    # Any call to the expired model requires database hit, so
    # `print john.name` would cause the following error:
    #
    # DetachedInstanceError: Instance <User at 0x95c756c>
    # is not bound to a Session; attribute refresh
    # operation cannot proceed
    #
    # It would happen because `john`'s Session no longer exists.
    # To continue working with detached object, we need to
    # reconcile it with the current Session:
    john = db.session.merge(john)
    
    print john in db.session  # True
    print john.name  # John

Installation
------------

``pip install flask-webtest``

Usage
-----

.. code:: python

    from unittest import TestCase
    from flask.ext.webtest import TestApp
    from main import app


    class ExampleTest(TestCase):
        def setUp(self):
            self.app = app
            self.w = TestApp(self.app)  # Or self.app.wsgi_app

        def test(self):
            r = self.w.get('/')
            self.assertFalse(r.flashes)
            self.assertEqual(r.context['text'], 'Hello!')
            self.assertEqual(r.template, 'template.html')
            self.assertFalse(r.flashes)
            self.assertNotIn('user_id', r.session)
