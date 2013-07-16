# coding: utf-8
from copy import copy
from functools import partial

from werkzeug.local import LocalStack
from flask import g, session, get_flashed_messages
from flask.signals import template_rendered, request_started, request_finished
from flask.ext.sqlalchemy import connection_stack
from webtest import (TestApp as BaseTestApp,
                     TestRequest as BaseTestRequest,
                     TestResponse as BaseTestResponse)

try:
    # Available starting with Flask 0.10
    from flask.signals import message_flashed
except ImportError:
    message_flashed = None


_sqlalchemy_scope_stack = LocalStack()


class SQLAlchemyScope(object):
    def __init__(self, db, original_scopefunc=connection_stack.__ident_func__):
        self.db = db
        self.original_scopefunc = original_scopefunc

    def push(self):
        _sqlalchemy_scope_stack.push(self)

    def pop(self):
        self.db.session.remove()
        rv = _sqlalchemy_scope_stack.pop()
        assert rv is self, 'Popped wrong SQLAlchemy scope.  (%r instead of %r)' \
            % (rv, self)

    def scopefunc(self):
        return (self.original_scopefunc(), id(self))
    
    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()


def scopefunc(original_scopefunc=connection_stack.__ident_func__):
    sqlalchemy_scope = _sqlalchemy_scope_stack.top
    if sqlalchemy_scope:
        rv = _sqlalchemy_scope_stack.top.scopefunc()
    else:
        rv = original_scopefunc()
    return rv


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
    def _make_contexts_assertions(self):
        assert self.contexts, 'No templates used to render the response.'
        assert len(self.contexts) == 1, \
            ('More than one template used to render the response. '
             'Use `contexts` attribute to access their names and contexts.')

    @property
    def context(self):
        self._make_contexts_assertions()
        return self.contexts.values()[0]

    @property
    def template(self):
        self._make_contexts_assertions()
        return self.contexts.keys()[0]


class TestRequest(BaseTestRequest):
    ResponseClass = TestResponse


class TestApp(BaseTestApp):
    RequestClass = TestRequest

    def do_request(self, *args, **kwargs):
        store = {}
        tear_down_ = partial(tear_down, store)

        request_started.connect(set_up)
        request_finished.connect(tear_down_)
        template_rendered.connect(store_rendered_template)
        if message_flashed:
            message_flashed.connect(store_flashed_message)

        try:
            response = super(TestApp, self).do_request(*args, **kwargs)
        finally:
            template_rendered.disconnect(store_rendered_template)
            request_finished.disconnect(tear_down_)
            request_started.disconnect(set_up)
            if message_flashed:
                message_flashed.disconnect(store_flashed_message)

        response.session = store.get('session', {})
        response.flashes = store.get('flashes', [])
        response.contexts = dict(store.get('contexts', []))
        return response
