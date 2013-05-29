# coding: utf-8
from copy import copy
from functools import partial

from webtest import (TestApp as BaseTestApp,
                     TestRequest as BaseTestRequest,
                     TestResponse as BaseTestResponse)
from flask import session, get_flashed_messages
from flask.signals import template_rendered, request_finished
try:
    # Available starting with Flask 0.10
    from flask.signals import message_flashed
except ImportError:
    message_flashed = None


def store_rendered_templates(store, sender, template, context, **extra):
    store.setdefault('contexts', []).append((template.name, context))


def store_flashed_messages(store, sender, message, category, **extra):
    store.setdefault('flashes', []).append((category, message))


def store_session(store, sender, response, **extra):
    store['session'] = dict(session)


def get_context_processor(store):
    """Returns context processor that injects modified version of
    `get_flashed_messages` which stores consumed messages in `store`.
    """
    def context_processor():
        def wrapper(*args, **kwargs):
            # `get_flashed_messages` removes messages from session, so
            # we store them before calling it
            flashes_to_be_consumed = copy(session.get('_flashes', []))
            store.setdefault('flashes', []).extend(flashes_to_be_consumed)
            return get_flashed_messages(*args, **kwargs)
        return {'get_flashed_messages': wrapper}
    return context_processor


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
        on_template_render = partial(store_rendered_templates, store)
        on_request_finish = partial(store_session, store)

        template_rendered.connect(on_template_render)
        request_finished.connect(on_request_finish)
        if message_flashed:
            message_flashed.connect(store_flashed_messages)
        else:
            # If signal is not available, fall back to using
            # context processor which stores consumed flash messages
            # in `store`
            flashes_processor = get_context_processor(store)
            self.app.template_context_processors[None].append(flashes_processor)

        try:
            response = super(TestApp, self).do_request(*args, **kwargs)
        finally:
            template_rendered.disconnect(on_template_render)
            request_finished.disconnect(on_request_finish)
            if message_flashed:
                message_flashed.disconnect(store_flashed_messages)
            else:
                # Remove our context processor
                self.app.template_context_processors[None].remove(flashes_processor)

        response.session = store.get('session', {})
        response.flashes = store.get('flashes', [])
        response.contexts = dict(store.get('contexts', []))
        return response
