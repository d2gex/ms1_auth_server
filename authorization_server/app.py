from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from authorization_server import config

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "frontend.login"
login_manager.login_message = "Please log in to see restricted access web pages"
login_manager.login_message_category = "info"


def create_app(config_class=config.Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    # require to import models here so that migrate knows what to generate
    from authorization_server import models
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from authorization_server.frontend.views import frontend
    app.register_blueprint(frontend, url_prefix='/')

    return app
