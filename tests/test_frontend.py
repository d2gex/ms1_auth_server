import pytest
from authorization_server.app import db, create_app
from authorization_server import models, config
from tests import utils as test_utils


@pytest.fixture(scope='module', autouse=True)
def app_context():
    app = create_app(config_class=config.TestingConfig)
    with app.app_context():
        yield


@test_utils.reset_database()
def test_registration_form(frontend_app):
    '''Test the registration form as follows:

    1) Registration page is served at /
    2) When all required fields are sent and they have the right format => users are redirected to login
    3) If any required field is missing or invalid => form should be invalid and error shown
        3.1) Required fields
        3.2) Email is invalid
        3.3) Email already exists
        3.4) Password is invalid
        3.5) Confirmed Password is not equal to Password
    '''

    # (1)
    response = frontend_app.get('/')
    assert response.status_code == 200
    assert 'Sign Up' in response.get_data(as_text=True)

    # (2)
    data = {'firstname': 'John',
            'lastname': 'Doe',
            'email': 'validemail@example.com',
            'password': 'password',
            'confirm_password': 'password'}
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'login page!' in response.get_data(as_text=True)

    # (3.1)
    original_value = data['firstname']
    data['firstname'] = ''
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'field is required' in response.get_data(as_text=True)

    # (3.2)
    data['firstname'] = original_value
    original_value = data['email']
    data['email'] = 'this is not a valid email'
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Please enter a valid email address' in response.get_data(as_text=True)

    # (3.3)
    # --> Insert a record in database
    data['email'] = original_value
    db_data = dict(data)
    del db_data['confirm_password']
    db.session.add(models.User(**db_data))
    db.session.commit()
    assert db.session.query(models.User).one()

    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'The email provided already exists. Please use another one' in response.get_data(as_text=True)
    db.session.query(models.User).delete()

    # (3.3)
    original_value = data['password']
    data['password'] = '123456'
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Your password must be between 8  and 15 characters long' in response.get_data(as_text=True)

    # (3.5)
    data['password'] = original_value
    original_value = data['confirm_password']
    data['confirm_password'] = '123456'
    response = frontend_app.post('/', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Please enter the same password again' in response.get_data(as_text=True)
