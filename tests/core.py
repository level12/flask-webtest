from flask import Flask, request, flash, render_template, session


app = Flask(__name__)
app.testing = True
app.config['SECRET_KEY'] = '123'
app.config['DEBUG'] = '123'


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        flash('You have pressed "Quit"...')
        render_template('extra-template.html', extra_text='Some text.')
        response = render_template('template.html', text='Goodbye!')
        flash('Flash message that will never be shown')
        return response
    else:
        return render_template('template.html', text='Hello!')


@app.route('/whoami/')
def whoami():
    return session.get('username', 'nobody')
