from flask_sqlalchemy import SQLAlchemy
from authorization_server import config
from authorization_server.app import db, create_app


def test_db_connection():
    app = create_app(config_class=config.TestingConfig)
    with app.app_context():  # the context needs to be pushed as Flask MongoEngine is using current_app
        assert db.engine.execute("select 1").scalar() == 1
