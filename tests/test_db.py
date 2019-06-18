import pytest

from sqlalchemy import exc, func
from authorization_server import config, models
from authorization_server.app import db, create_app
from tests import utils as test_utils
import uuid


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
        db.session.rollback()
    else:
        raise AssertionError('user_2 did not throw Integrity error as expected')


def test_client_table():
    ''' Test that client_id as string primary key and reg_token are both unique and don't accept duplicates
    '''

    app_id = str(uuid.uuid4()).replace('-', '')
    client_1 = models.Application(id=app_id, password='something')
    client_2 = models.Application(id=app_id, password='something')
    db.session.add(client_1)
    db.session.commit()
    assert db.session.query(models.Application).one()
    # Necessary to avoid a persistent conflict error given that both client_1 and client_2 do have the same primary key
    db.session.expunge(client_1)
    db.session.add(client_2)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_2 did not throw Integrity error as expected')
    client_3 = models.Application(id=str(uuid.uuid4()).replace('-', ''), password='something', reg_token='sametoken')
    client_4 = models.Application(id=str(uuid.uuid4()).replace('-', ''), password='something', reg_token='sametoken')
    db.session.add(client_3)
    db.session.commit()
    assert db.session.query(func.count(models.Application.id)).first()[0] == 2
    db.session.add(client_4)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_4 did not throw Integrity error as expected')


