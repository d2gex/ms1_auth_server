from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from authorization_server.app import db
from authorization_server import models


class RegistrationForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(),
                                                     Email(message='Please enter a valid email address')])
    password = PasswordField('Password',
                             validators=[Length(min=8, max=15,
                                                message='Your password must be between 8  and 15 characters long')])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                                 EqualTo('password', message="Please enter the same password again")])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        data = db.session.query(models.User).filter(models.User.email == email.data).first()
        if data:
            raise ValidationError('The email provided already exists. Please use another one')


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(),
                                                     Email(message='Please enter a valid email address')])
    password = PasswordField('Password',
                             validators=[Length(min=8, max=15,
                                                message='Your password must be between 8  and 15 characters long')])
    submit = SubmitField('Sign In')
