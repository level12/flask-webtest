from unittest import TestCase

from flask.ext.webtest import TestApp

from main import app


class ExampleTest(TestCase):
    def setUp(self):
        self.app = app
        self.w = TestApp(self.app)  # Or even self.app.wsgi_app

    def test_single_template(self):
        r = self.w.get('/')
        self.assertFalse(r.flashes)
        self.assertEqual(len(r.contexts), 1)

        self.assertEqual(r.context['text'], 'Hello!')
        self.assertEqual(r.template, 'template.html')

    def test_two_templates_and_flash_messages(self):
        r = self.w.get('/').form.submit()
        self.assertEqual(len(r.contexts), 2)
        self.assertEqual(len(r.flashes), 1)

        with self.assertRaises(AssertionError):
            r.context  # Because there are more than one used templates
        self.assertEqual(
            r.contexts['template.html']['text'],
            'Goodbye!')
        self.assertEqual(
            r.contexts['extra-template.html']['extra_text'],
            'Some text.')
