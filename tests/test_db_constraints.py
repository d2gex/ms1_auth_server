import pytest

from sqlalchemy import exc, func
from authorization_server import models
from authorization_server.app import db
from tests import utils as test_utils


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


@test_utils.reset_database(tear='up')
def test_client_table():
    ''' Test that application table respect the following constraints:

    1) client_id is unique
    2) name and description cannot be nullable
    3) reg_token is unique and nullable
    4) email is unique and not nullable
    5) web_url unique and not nullable
    6) redirect_uri unique and not nullable
    7) When 1 to 6 is met => insert rows
    '''

    # (1)
    constraints = {
        'id': False,
        'email': True,
        'reg_token': True,
        'web_url': True,
        'redirect_uri': True,
        'name': True,
        'description': True
    }

    rows = test_utils.generate_pair_client_model_data(constraints)

    client_1 = models.Application(**rows[0])
    client_2 = models.Application(**rows[1])

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
    constraints['id'] = True
    constraints['name'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_3 = models.Application(**rows[0])
    db.session.add(client_3)
    try:
        db.session.commit()
    except exc.OperationalError:
        db.session.rollback()
    else:
        raise AssertionError('client_3 did not throw Operation error as expected when name is null')

    # (2.2)
    # --> Description cannot be null
    constraints['name'] = True
    constraints['description'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_3 = models.Application(**rows[0])
    db.session.add(client_3)
    try:
        db.session.commit()
    except exc.OperationalError as ex:
        db.session.rollback()
    else:
        raise AssertionError('client_3 did not throw Operation error as expected when description is null')

    # (3)
    # ---> reg_token need to be unique
    constraints['description'] = True
    constraints['reg_token'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_3 = models.Application(**rows[0])
    client_4 = models.Application(**rows[1])
    db.session.add(client_3)
    db.session.commit()
    db.session.add(client_4)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_4 did not throw Integrity error as expected when reg_token is not unique')
    #
    # (4)
    # --> email need to be unique
    constraints['reg_token'] = True
    constraints['email'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_5 = models.Application(**rows[0])
    client_6 = models.Application(**rows[1])
    db.session.add(client_5)
    db.session.commit()
    db.session.add(client_6)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_6 did not throw Integrity error as expected when email is not unique')

    # (5)
    # --> web_url need to be unique
    constraints['email'] = True
    constraints['web_url'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_7 = models.Application(**rows[0])
    client_8 = models.Application(**rows[1])
    db.session.add(client_7)
    db.session.commit()
    db.session.add(client_8)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_8 did not throw Integrity error as expected when web_url is not unique')

    # (6)
    # --> redirect_uri need to be unique
    constraints['web_url'] = True
    constraints['redirect_uri'] = False
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_9 = models.Application(**rows[0])
    client_10 = models.Application(**rows[1])
    db.session.add(client_9)
    db.session.commit()
    db.session.add(client_10)
    try:
        db.session.commit()
    except exc.IntegrityError:
        db.session.rollback()
    else:
        raise AssertionError('client_10 did not throw Integrity error as expected when redirect_uri is not unique')

    # (7)
    # --> Insert rows whenever the constraints are met
    db_num_clients = db.session.query(func.count(models.Application.id)).scalar()
    constraints['redirect_uri'] = True
    rows = test_utils.generate_pair_client_model_data(constraints)
    client_11 = models.Application(**rows[0])
    client_12 = models.Application(**rows[1])
    db.session.add(client_11)
    db.session.add(client_12)
    db.session.commit()
    assert db.session.query(func.count(models.Application.id)).scalar() == db_num_clients + 2


@test_utils.reset_database(tear='up_down')
def test_authorisation_code_table():
    '''Ensure authorisation_code constrains are met
    '''

    constraints = {
        'id': False,
        'email': True,
        'reg_token': True,
        'web_url': True,
        'redirect_uri': True,
        'name': True,
        'description': True
    }

    rows = test_utils.generate_pair_client_model_data(constraints)

    client = models.Application(**rows[0])
    db.session.add(client)
    db.session.commit()
    db_data = db.session.query(models.Application).one()

    auth_code = models.AuthorisationCode(application_id='this id does not exist in the db yet')
    db.session.add(auth_code)
    with pytest.raises(exc.IntegrityError):
        db.session.commit()

    db.session.rollback()
    auth_code.application_id = db_data.id
    db.session.add(auth_code)
    db.session.commit()
    db_data = db.session.query(models.Application, models.AuthorisationCode).one()
    assert db_data[0].id == db_data[1].application_id
