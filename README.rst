Flask-WebTest
=============

Flask-WebTest provides a set of utilities to ease testing Flask applications with WebTest.

``flask.ext.webtest.TestApp`` extends ``webtest.TestApp`` by adding few useful fields to response:

* ``response.templates`` ― dictionary containing information about what templates were used to build the response and what their contexts were. The keys are template names and the values are template contexts.  
  If only one template was used, it's name and context can be accessed through ``response.template`` and ``response.context``.

* ``response.flashes`` ― list of tuples (category, message) containing messages that were flashed during request.

  *Note*:  
  Fully supported only starting with Flask 0.10 (which is not released at the time of writing).  
  If you use previous version, ``response.flashes`` will contain only those messages that was consumed by ``get_flashed_messages()`` *template* calls.

* ``response.session`` ― dictionary containing session data.

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
