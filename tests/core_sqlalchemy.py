from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_webtest import get_scopefunc


def make_db(app):
    session_options = {}
    if app.testing:
        session_options['scopefunc'] = get_scopefunc()
    return SQLAlchemy(app, session_options=session_options)


app = Flask(__name__)
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
    return User.query.get_or_404(id).greet()


@app.route('/user/<int:id>/preview/', methods=['POST'])
def preview(id):
    user = User.query.get_or_404(id)
    user.greeting = request.form['greeting']
    db.session.expunge(user)
    return user.greet()
