from flask import Blueprint, render_template, redirect,  url_for
from authorization_server.frontend.forms import RegistrationForm

frontend = Blueprint('frontend', __name__, static_folder='../static/frontend')


@frontend.route('/', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        return redirect(url_for('frontend.login'))
    return render_template('frontend/register.html', form=form)


@frontend.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('frontend/login.html')


@frontend.route('/profile', methods=['GET', 'POST'])
def profile():
    return render_template('frontend/profile.html')
