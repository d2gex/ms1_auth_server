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


@test_utils.reset_database(tear='up_down')
def test_client_table():
    ''' Test that application table respect the following constraints:

    1) client_id is unique
    2) name and description cannot be nullable
    3) reg_token is unique and nullable
    4) email is unique and not nullable
    '''

    # (1)
    app_id = str(uuid.uuid4()).replace('-', '')
    client_1 = models.Application(id=app_id, name='client_1', description='Client 1 ...',
                                  password='something', email='email_a@example.com')
    client_2 = models.Application(id=app_id, name='client_2', description='Client 2 ...',
                                  password='something', email='email_b@example.com')
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
        raise AssertionError('client_2 did not throw Integrity error as expected when client_id is not  unique')

    # (2.1)
    # --> Name cannot be null
    client_2.id = 'something else'
    client_2.name = None
    db.session.add(client_2)
    try:
        db.session.commit()
    except exc.OperationalError:
        db.session.rollback()
    else:
        raise AssertionError('client_2 did not throw Operation error as expected when name is null')

    # (2.2)
    # --> Description cannot be null
    client_2.name = 'something'
    client_2.description = None
    db.session.add(client_2)
    try:
        db.session.commit()
    except exc.OperationalError:
        db.session.rollback()
    else:
        raise AssertionError('client_2 did not throw Operation error as expected when description is null')

    # (3)
    # ---> reg_token need to be unique
    client_3 = models.Application(id=str(uuid.uuid4()).replace('-', ''), password='something', reg_token='sametoken',
                                  email='email_c@example.com', name='client 3', description='client 3 ...')
    client_4 = models.Application(id=str(uuid.uuid4()).replace('-', ''), password='something', reg_token='sametoken',
                                  email='email_d@example.com', name='client 4', description='client 4 ...')
    db.session.add(client_3)
    db.session.commit()
    db.session.add(client_4)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_4 did not throw Integrity error as expected when reg_token is not unique')

    # (4)
    # --> email need to be unique
    client_5 = models.Application(id=str(uuid.uuid4()).replace('-', ''), password='something', reg_token='token_1',
                                  email='email_e@example.com', name='client 5', description='client 5 ...')
    client_6 = models.Application(id=str(uuid.uuid4()).replace('-', ''), password='something', reg_token='token_2',
                                  email='email_e@example.com', name='client 6', description='client 6 ...')
    db.session.add(client_5)
    db.session.commit()
    db.session.add(client_6)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_6 did not throw Integrity error as expected when email is not unique')
