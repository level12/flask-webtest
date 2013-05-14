# coding: utf-8
from copy import copy
from functools import partial

from flask import template_rendered
from webtest import TestApp


class ContextList(list):
    def __getitem__(self, key):
        if isinstance(key, basestring):
            for subcontext in self:
                if key in subcontext:
                    return subcontext[key]
            raise KeyError(key)
        else:
            return super(ContextList, self).__getitem__(key)

    def __contains__(self, key):
        try:
            value = self[key]
        except KeyError:
            return False
        return True


def store_rendered_templates(store, app, template, context):
    store.setdefault('templates', []).append(template)
    store.setdefault('contexts', ContextList()).append(copy(context))


class TestClient(TestApp):
    def do_request(self, *args, **kwargs):
        data = {}
        on_template_render = partial(store_rendered_templates, data)

        template_rendered.connect(on_template_render)
        try:
            response = super(TestClient, self).do_request(*args, **kwargs)
        finally:
            template_rendered.disconnect(on_template_render)

        response.context = None
        contexts = data.get('contexts')
        if contexts:
            if len(contexts) == 1:
                response.context = contexts[0]
            else:
                response.context = contexts

        response.template = None
        response.templates = []
        templates = data.get('templates')
        if templates:
            response.templates = templates
            if len(templates) == 1:
                response.template = templates[0]

        return response
