from flask import Flask, abort, request
from flask_sqlalchemy import SQLAlchemy
from flask_webtest import get_scopefunc


def make_db(app):
    session_options = {}
    if app.testing:
        session_options['scopefunc'] = get_scopefunc()
    return SQLAlchemy(app, session_options=session_options)


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.testing = True
db = make_db(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    greeting = db.Column(db.String(80), default=u'Hello, %s!')

    def greet(self):
        return self.greeting % self.name


@app.route('/user/<int:id>/')
def user(id):
    user = db.session.get(User, id)
    if not user:
        return abort(404)
    return user.greet()


@app.route('/user/<int:id>/preview/', methods=['POST'])
def preview(id):
    user = db.session.get(User, id)
    if not user:
        return abort(404)
    user.greeting = request.form['greeting']
    db.session.expunge(user)
    return user.greet()
