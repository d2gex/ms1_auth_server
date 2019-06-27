from sqlalchemy.orm import exc
from authorization_server import models
from authorization_server.app import db, bcrypt
from tests import utils as test_utils


def add_user_client_context_to_db():
    '''Add user and client data to the database to emulate a real case scenario
    '''
    constraints = {
        'id': True,
        'email': True,
        'reg_token': True,
        'web_url': True,
        'redirect_uri': True,
        'name': True,
        'description': True
    }
    client_data = test_utils.generate_pair_client_model_data(constraints)
    client = models.Application(**client_data[0])
    client.client_secret = bcrypt.generate_password_hash(client_data[0]['client_secret']).decode()
    client.is_allowed = True
    user_data = test_utils.generate_model_user_instance()
    user = models.User(**user_data)
    user.password = bcrypt.generate_password_hash(user_data['password']).decode()
    db.session.add(client)
    db.session.add(user)
    db.session.commit()

    return client_data, user_data


@test_utils.reset_database()
def test_add_user_client_context_to_db():

    client_data, user_data = add_user_client_context_to_db()
    # Following two statements
    try:
        db.session.query(models.User).one()
        db.session.query(models.Application).one()
    except (exc.NoResultFound, exc.MultipleResultsFound) as ex:
        raise AssertionError('There should only be one row per User and Client, respectively') from ex
    else:
        assert client_data and len(client_data) == 2
        assert user_data


@test_utils.reset_database()
def test_code_login_required(frontend_app):
    '''Ensure that views in auth are login-required

    1) When not logged in => User should be redirected to GrandType Login page
    '''

    client_data, user_data = add_user_client_context_to_db()

    # (1)
    response = frontend_app.get('/auth/code')
    assert response.status_code == 302
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['Forgot Password?', 'This application would like:'])

    # (2)
    data = {
        'email': user_data['email'],
        'password': user_data['password']
    }
    response = frontend_app.post('/login', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Account Details' in response.get_data(as_text=True)
    with frontend_app.session_transaction() as session:
        assert 'user_id' in session

    response = frontend_app.get('/auth/code')
    assert response.status_code == 400
    assert 'Bad Request' in response.get_data(as_text=True)
