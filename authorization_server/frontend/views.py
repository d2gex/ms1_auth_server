from flask import Blueprint, render_template, redirect,  url_for
from authorization_server.frontend.forms import RegistrationForm, LoginForm
from authorization_server import models
from authorization_server.app import db, bcrypt

frontend = Blueprint('frontend', __name__, static_folder='../static/frontend')


@frontend.route('/', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        enc_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = models.User(**{key: value for key, value in form.data.items() if key not in ('confirm_password', 'submit')})
        user.password = enc_password
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('frontend.login'))
    return render_template('frontend/register.html', form=form)


@frontend.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    return render_template('frontend/login.html', form=form)


@frontend.route('/profile', methods=['GET', 'POST'])
def profile():
    return render_template('frontend/profile.html')
