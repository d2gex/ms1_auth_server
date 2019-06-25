from flask_wtf import FlaskForm
from wtforms import SubmitField


class AuthorisationForm(FlaskForm):
    cancel = SubmitField('Cancel')
    allow = SubmitField('Allow')
