from flask import Blueprint, render_template, request, redirect,  url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from authorization_server.frontend.forms import RegistrationForm, SimpleLoginForm, GrandTypeLoginForm
from authorization_server import models, oauth_code
from authorization_server.app import db, bcrypt

frontend = Blueprint('frontend', __name__, static_folder='../static/frontend')
LOGIN_ERROR_MESSAGE = 'Login Unsuccessful. Please check email and password'


@frontend.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        enc_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = models.User(**{key: value for key, value in form.data.items()
                              if key not in ('confirm_password', 'submit', 'csrf_token')})
        user.password = enc_password
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('frontend.login'))
    return render_template('frontend/register.html', form=form)


@frontend.route('/login', methods=['GET', 'POST'])
def login():
    client_app = None
    is_grand_type = request.args.get('grand_type')
    if is_grand_type == 'code':
        auth_code = oauth_code.AuthorisationCode(**request.args)
        client_app = {'name': 'Application Name', 'web_url': 'https://www.bbc.co.uk'}
        form = GrandTypeLoginForm()
    else:
        form = SimpleLoginForm()

    if current_user.is_authenticated:
        return redirect(url_for('frontend.profile'))
    if form.validate_on_submit():
        user = db.session.query(models.User).filter(models.User.email == form.email.data).first()
        if not user or not bcrypt.check_password_hash(user.password, form.password.data):
            flash(LOGIN_ERROR_MESSAGE, category='danger')
        else:
            login_user(user)
            return redirect(url_for('frontend.profile'))
    return render_template('frontend/login.html', form=form, client_app=client_app, test=type(is_grand_type))


@frontend.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('frontend.login'))


@frontend.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return render_template('frontend/profile.html')
