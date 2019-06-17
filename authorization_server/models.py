from authorization_server.app import db


class User(db.Model):

    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(length=20))
    lastname = db.Column(db.String(length=40))
    email = db.Column(db.String(length=50), nullable=False, unique=True)
    password = db.Column(db.String(length=128))
