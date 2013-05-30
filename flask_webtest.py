# coding: utf-8
from copy import copy
from functools import partial

from webtest import (TestApp as BaseTestApp,
                     TestRequest as BaseTestRequest,
                     TestResponse as BaseTestResponse)
from flask import session, get_flashed_messages
from flask.signals import template_rendered, request_started, request_finished
try:
    # Available starting with Flask 0.10
    from flask.signals import message_flashed
except ImportError:
    message_flashed = None


def store_rendered_template(store, app, template, context, **extra):
    store.setdefault('contexts', []).append((template.name, context))


def store_flashed_message(store, app, message, category, **extra):
    store.setdefault('flashes', []).append((category, message))


def store_session(store, app, response, **extra):
    store['session'] = dict(session)


def add_context_processor(store, app):
    """Adds context processor that injects modified version of
    `get_flashed_messages` which stores consumed messages in `store`.
    """
    def flask_webtest_hook():
        def wrapper(*args, **kwargs):
            # `get_flashed_messages` removes messages from session
            flashes_to_be_consumed = copy(session.get('_flashes', []))
            store.setdefault('flashes', []).extend(flashes_to_be_consumed)
            return get_flashed_messages(*args, **kwargs)
        return {'get_flashed_messages': wrapper}
    app.template_context_processors[None].append(flask_webtest_hook)


def remove_context_processor(app, response, **extra):
    processor_to_be_removed = None
    for processor in app.template_context_processors[None]:
        if getattr(processor, 'func_name', None) == 'flask_webtest_hook':
            processor_to_be_removed = processor

    if processor_to_be_removed:
        app.template_context_processors[None].remove(processor_to_be_removed)


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
        store_rendered_template_ = partial(store_rendered_template, store)
        store_session_ = partial(store_session, store)

        template_rendered.connect(store_rendered_template_)
        request_finished.connect(store_session_)
        if message_flashed:
            message_flashed.connect(store_flashed_message)
        else:
            add_context_processor_ = partial(add_context_processor, store)
            request_started.connect(add_context_processor_)
            request_finished.connect(remove_context_processor)

        try:
            response = super(TestApp, self).do_request(*args, **kwargs)
        finally:
            template_rendered.disconnect(store_rendered_template_)
            request_finished.disconnect(store_session_)
            if message_flashed:
                message_flashed.disconnect(store_flashed_message)
            else:
                request_started.disconnect(add_context_processor_)
                request_finished.disconnect(remove_context_processor)

        response.session = store.get('session', {})
        response.flashes = store.get('flashes', [])
        response.contexts = dict(store.get('contexts', []))
        return response
