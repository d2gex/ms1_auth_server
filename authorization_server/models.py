from flask_login import UserMixin
from authorization_server.app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User.id == user_id).first()


class User(db.Model, UserMixin):

    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(length=20))
    lastname = db.Column(db.String(length=40))
    email = db.Column(db.String(length=50), nullable=False, unique=True)
    password = db.Column(db.String(length=128))
