import uuid

from datetime import datetime
from flask_login import UserMixin
from authorization_server.app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


class User(db.Model, UserMixin):

    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(length=20))
    lastname = db.Column(db.String(length=40))
    email = db.Column(db.String(length=50), nullable=False, unique=True)
    password = db.Column(db.String(length=128))


class Application(db.Model):

    __tablename__ = 'application'
    id = db.Column(db.String(length=40), primary_key=True, nullable=False)
    client_secret = db.Column(db.String(length=128))
    reg_token = db.Column(db.String(length=40), unique=True)
    email = db.Column(db.String(length=50), unique=True, nullable=False)
    name = db.Column(db.String(length=50), nullable=False)
    description = db.Column(db.String(length=255), nullable=False)
    web_url = db.Column(db.String(length=255), unique=True, nullable=False)
    redirect_uri = db.Column(db.String(length=255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    is_allowed = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.now)
    updated = db.Column(db.DateTime)
    authorisation_code = db.relationship("AuthorisationCode", back_populates='application')

    @classmethod
    def generate_id(cls):
        return str(uuid.uuid4()).replace('-', '')


class AuthorisationCode(db.Model):

    __tablename__ = 'authorisation_code'
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.now)
    updated = db.Column(db.DateTime)
    application_id = db.Column(db.String(length=40), db.ForeignKey('application.id'))
    application = db.relationship('Application', back_populates='authorisation_code')

