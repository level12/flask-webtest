# coding: utf-8
try:
    from http import cookiejar
except ImportError:
    import cookielib as cookiejar
from copy import copy
from functools import partial
from contextlib import contextmanager, nullcontext

from werkzeug.local import LocalStack
from flask import g, session, get_flashed_messages
from flask.signals import template_rendered, request_started, request_finished
from webtest import (TestApp as BaseTestApp,
                     TestRequest as BaseTestRequest,
                     TestResponse as BaseTestResponse)

try:
    import flask_sqlalchemy
except ImportError:
    flask_sqlalchemy = None

try:
    # Available starting with Flask 0.10
    from flask.signals import message_flashed
except ImportError:
    message_flashed = None


_session_scope_stack = LocalStack()


class SessionScope(object):
    """Session scope, being pushed, changes the value of
    :func:`.scopefunc` and, as a result, calls to `db.session`
    are proxied to the new underlying session.
    When popped, removes the current session and swap the value of
    :func:`.scopefunc` to the one that was before.

    :param db: :class:`flask_sqlalchemy.SQLAlchemy` instance
    """

    def __init__(self, db):
        self.db = db

    def push(self):
        """Pushes the session scope."""
        _session_scope_stack.push(self)

    def pop(self):
        """Removes the current session and pops the session scope."""
        self.db.session.remove()
        rv = _session_scope_stack.pop()
        assert rv is self, 'Popped wrong session scope.  (%r instead of %r)' \
            % (rv, self)

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()


def get_scopefunc(original_scopefunc=None):
    """Returns :func:`.SessionScope`-aware `scopefunc` that has to be used
    during testing.
    """

    if original_scopefunc is None:
        assert flask_sqlalchemy, 'Is Flask-SQLAlchemy installed?'

        try:
            # for flask_sqlalchemy older than 2.2 where the connection_stack
            # was either the app stack or the request stack
            original_scopefunc = flask_sqlalchemy.connection_stack.__ident_func__
        except AttributeError:
            try:
                # when flask_sqlalchemy 2.2 or newer, which supports only flask 0.10
                # or newer, we use app stack
                from flask import _app_ctx_stack
                original_scopefunc = _app_ctx_stack.__ident_func__
            except AttributeError:
                # newer flask does not expose an __ident_func__, use greenlet directly
                import greenlet
                original_scopefunc = greenlet.getcurrent

    def scopefunc():
        rv = original_scopefunc()
        sqlalchemy_scope = _session_scope_stack.top
        if sqlalchemy_scope:
            rv = (rv, id(sqlalchemy_scope))
        return rv

    return scopefunc


def store_rendered_template(app, template, context, **extra):
    g._flask_webtest.setdefault('contexts', []).append((template.name, context))


def store_flashed_message(app, message, category, **extra):
    g._flask_webtest.setdefault('flashes', []).append((category, message))


def set_up(app, *args, **extra):
    g._flask_webtest = {}
    if not message_flashed:
        def _get_flashed_messages(*args, **kwargs):
            # `get_flashed_messages` removes messages from session,
            # so we store them in `g._flask_webtest`
            flashes_to_be_consumed = copy(session.get('_flashes', []))
            g._flask_webtest.setdefault('flashes', []).extend(flashes_to_be_consumed)
            return get_flashed_messages(*args, **kwargs)
        app.jinja_env.globals['get_flashed_messages'] = _get_flashed_messages


def tear_down(store, app, response, *args, **extra):
    g._flask_webtest['session'] = dict(session)
    store.update(g._flask_webtest)
    del g._flask_webtest
    if not message_flashed:
        app.jinja_env.globals['get_flashed_messages'] = get_flashed_messages


class TestResponse(BaseTestResponse):
    contexts = {}

    def _make_contexts_assertions(self):
        assert self.contexts, 'No templates used to render the response.'
        assert len(self.contexts) == 1, \
            ('More than one template used to render the response. '
             'Use `contexts` attribute to access their names and contexts.')

    @property
    def context(self):
        self._make_contexts_assertions()
        return list(self.contexts.values())[0]

    @property
    def template(self):
        self._make_contexts_assertions()
        return list(self.contexts.keys())[0]


class TestRequest(BaseTestRequest):
    ResponseClass = TestResponse


class CookieJar(cookiejar.CookieJar):
    """CookieJar that always sets ASCII headers, even if cookies have
    unicode parts such as name, value or path. It is necessary to make
    :meth:`TestApp.session_transaction` work correctly.
    """
    def _cookie_attrs(self, cookies):
        attrs = cookiejar.CookieJar._cookie_attrs(self, cookies)
        return map(str, attrs)


class TestApp(BaseTestApp):
    """Extends :class:`webtest.TestApp` by adding few fields to responses:

    .. attribute:: templates

        Dictionary containing information about what templates were used to
        build the response and what their contexts were.
        The keys are template names and the values are template contexts.

    .. attribute:: flashes

        List of tuples (category, message) containing messages that were
        flashed during request.

        Note: Fully supported only starting with Flask 0.10. If you use
        previous version, `flashes` will contain only those messages that
        were consumed by :func:`flask.get_flashed_messages` template calls.

    .. attribute:: session

        Dictionary that contains session data.

    If exactly one template was used to render the response, it's name and context
    can be accessed using `response.template` and `response.context` properties.

    If `app` config sets SERVER_NAME and HTTP_HOST is not specified in
    `extra_environ`, :class:`TestApp` will also set HTTP_HOST to SERVER_NAME
    for all requests to the app.

    :param app: :class:`flask.Flask` instance
    :param db: :class:`flask_sqlalchemy.SQLAlchemy` instance
    :param use_session_scopes: if specified, application performs each request
                               within it's own separate session scope
    """
    RequestClass = TestRequest

    def __init__(self, app, db=None, use_session_scopes=False, cookiejar=None,
                 extra_environ=None, *args, **kwargs):
        if use_session_scopes:
            assert db, ('`db` (instance of `flask_sqlalchemy.SQLAlchemy`) '
                        'must be passed to use session scopes.')
        self.db = db
        self.use_session_scopes = use_session_scopes

        if extra_environ is None:
            extra_environ = {}
        if app.config['SERVER_NAME'] and 'HTTP_HOST' not in extra_environ:
            extra_environ['HTTP_HOST'] = app.config['SERVER_NAME']

        super(TestApp, self).__init__(app, extra_environ=extra_environ,
                                      *args, **kwargs)
        # cookielib.CookieJar defines __len__ and empty CookieJar evaluates
        # to False in boolan context. That's why we explicitly compare
        # `cookiejar` with None:
        self.cookiejar = CookieJar() if cookiejar is None else cookiejar

    def do_request(self, *args, **kwargs):
        store = {}
        tear_down_ = partial(tear_down, store)

        request_started.connect(set_up)
        request_finished.connect(tear_down_)
        template_rendered.connect(store_rendered_template)
        if message_flashed:
            message_flashed.connect(store_flashed_message)

        if self.use_session_scopes:
            scope = SessionScope(self.db)
            scope.push()

        context = nullcontext
        if self.app.config.get('FLASK_WEBTEST_PUSH_APP_CONTEXT', False):
            context = self.app.app_context
        try:
            with context():
                response = super(TestApp, self).do_request(*args, **kwargs)
        finally:
            if self.use_session_scopes:
                scope.pop()
            template_rendered.disconnect(store_rendered_template)
            request_finished.disconnect(tear_down_)
            request_started.disconnect(set_up)
            if message_flashed:
                message_flashed.disconnect(store_flashed_message)

        response.session = store.get('session', {})
        response.flashes = store.get('flashes', [])
        response.contexts = dict(store.get('contexts', []))
        return response

    @contextmanager
    def session_transaction(self):
        """When used in combination with a with statement this opens
        a session transaction. This can be used to modify the session
        that the test client uses. Once the with block is left the session
        is stored back.

        For example, if you use Flask-Login, you can log in a user using
        this method::

            with client.session_transaction() as sess:
                sess['user_id'] = 1

        Internally it uses :meth:`flask.testing.FlaskClient.session_transaction`.
        """
        with self.app.test_client() as client:
            for cookie in self.cookiejar:
                client.cookie_jar.set_cookie(cookie)

            with client.session_transaction() as sess:
                yield sess

            for cookie in client.cookie_jar:
                # Cookies from `client.cookie_jar` may contain unicode name
                # and value. It would make WebTest linter (:mod:`webtest.lint`)
                # throw assertion errors about unicode environmental
                # variable (HTTP_COOKIE), but we use custom CookieJar that is
                # aware of this oddity and always sets 8-bit headers.
                self.cookiejar.set_cookie(cookie)
