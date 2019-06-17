from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


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
    submit = SubmitField('Register Now')
