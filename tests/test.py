import unittest

import sqlalchemy
from flask_webtest import TestApp

from .core import app as app1
from .core_sqlalchemy import app as app2, db, User


class TestMainFeatures(unittest.TestCase):
    def setUp(self):
        self.app = app1
        self.w = TestApp(self.app)

    def test_single_template(self):
        r = self.w.get('/')
        self.assertFalse(r.flashes)
        self.assertEqual(len(r.contexts), 1)

        self.assertEqual(r.context['text'], 'Hello!')
        self.assertEqual(r.template, 'template.html')
        self.assertNotIn('qwerty', r.session)

    def test_two_templates_and_flash_messages(self):
        r = self.w.get('/').form.submit()
        self.assertEqual(len(r.contexts), 2)

        self.assertEqual(len(r.flashes), 2)
        category, message = r.flashes[0]
        self.assertEqual(message, 'You have pressed "Quit"...')

        category, message = r.flashes[1]
        self.assertEqual(message, 'Flash message that will never be shown')

        with self.assertRaises(AssertionError):
            r.context  # Because there are more than one used templates
        self.assertEqual(
            r.contexts['template.html']['text'],
            'Goodbye!')
        self.assertEqual(
            r.contexts['extra-template.html']['extra_text'],
            'Some text.')

    def test_session_transaction(self):
        r = self.w.get('/whoami/')
        self.assertEqual(r.body.decode('utf-8'), 'nobody')

        with self.w.session_transaction() as sess:
            sess['username'] = 'aromanovich'

        r = self.w.get('/whoami/')

        self.assertEqual(r.session['username'], 'aromanovich')
        self.assertEqual(r.body.decode('utf-8'), 'aromanovich')

    def test_init(self):
        w = TestApp(self.app)
        self.assertEqual(w.get('/').status_code, 200)

        original_server_name = self.app.config['SERVER_NAME']
        try:
            self.app.config['SERVER_NAME'] = 'webtest-app.local'
            w = TestApp(self.app)
            self.assertEqual(w.get('/').status_code, 200)
        finally:
            self.app.config['SERVER_NAME'] = original_server_name


class TestSQLAlchemyFeatures(unittest.TestCase):
    def setUp(self):
        self.app = app2
        self.w_without_scoping = TestApp(self.app)
        self.w = TestApp(self.app, db=db, use_session_scopes=True)

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.drop_all()
        self.app_context.pop()

    def test_1(self):
        user = User(name='Anton')
        db.session.add(user)
        db.session.commit()

        r = self.w.get('/user/%i/' % user.id)
        self.assertEqual(r.body.decode('utf-8'), 'Hello, Anton!')

        # Note: we did not commit the change to `user`!
        user.name = 'Petr'

        r = self.w_without_scoping.get('/user/%i/' % user.id)
        self.assertEqual(r.body.decode('utf-8'), 'Hello, Petr!')

        r = self.w.get('/user/%i/' % user.id)
        self.assertEqual(r.body.decode('utf-8'), 'Hello, Anton!')

    def test_2(self):
        user = User(name='Anton')
        db.session.add(user)
        db.session.commit()

        r = self.w.get('/user/%i/' % user.id)
        self.assertEqual(r.body.decode('utf-8'), 'Hello, Anton!')

        r = self.w.post('/user/%i/preview/' % user.id, {
            'greeting': 'Hi, %s.',
        })
        self.assertEqual(r.body.decode('utf-8'), 'Hi, Anton.')
        db.session.refresh(user)

        r = self.w_without_scoping.post('/user/%i/preview/' % user.id, {
            'greeting': 'Hi, %s.',
        })
        self.assertEqual(r.body.decode('utf-8'), 'Hi, Anton.')
        self.assertRaises(
            sqlalchemy.exc.InvalidRequestError,
            lambda: db.session.refresh(user))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMainFeatures))
    suite.addTest(unittest.makeSuite(TestSQLAlchemyFeatures))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
