from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from authorization_server import config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=config.Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    from authorization_server import models  # require to import models here so that migrate knows what to generate
    migrate.init_app(app, db)
    return app
