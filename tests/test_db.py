import pytest

from sqlalchemy import exc
from authorization_server import config, models
from authorization_server.app import db, create_app
from tests import utils as test_utils


@pytest.fixture(scope='module', autouse=True)
def app_context():
    app = create_app(config_class=config.TestingConfig)
    with app.app_context():
        yield


def test_db_connection():
    assert db.engine.execute("select 1").scalar() == 1


@test_utils.reset_database()
def test_user_table():
    user_1 = models.User(email='test@example.com', password='abcD1234')
    user_2 = models.User(email='test@example.com', password='abcD1234')
    db.session.add(user_1)
    db.session.commit()
    assert db.session.query(models.User).one()
    db.session.add(user_2)
    try:
        db.session.commit()
    except exc.IntegrityError:
        pass
    else:
        raise AssertionError('user_2 did not throw Integrity error as expected')
