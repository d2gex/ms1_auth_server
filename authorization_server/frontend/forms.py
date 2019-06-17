from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from authorization_server.app import db
from authorization_server import models

INVALID_EMAIL_ERROR = 'Please enter a valid email address'
EMAIL_EXIST_ERROR = 'The email provided already exists. Please use another one'
INVALID_PASSWORD_ERROR = 'Your password must be between 8 and 15 characters long'
DIFFERENT_PASSWORD_ERROR = 'Please enter the same password again'


class RegistrationForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(),
                                                     Email(message=INVALID_EMAIL_ERROR)])
    password = PasswordField('Password',
                             validators=[Length(min=8, max=15,
                                                message=INVALID_PASSWORD_ERROR)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                                 EqualTo('password', message=DIFFERENT_PASSWORD_ERROR)])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        data = db.session.query(models.User).filter(models.User.email == email.data).first()
        if data:
            raise ValidationError(EMAIL_EXIST_ERROR)


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(),
                                                     Email(message=INVALID_EMAIL_ERROR)])
    password = PasswordField('Password',
                             validators=[Length(min=8, max=15,
                                                message=INVALID_PASSWORD_ERROR)])
    submit = SubmitField('Sign In')
