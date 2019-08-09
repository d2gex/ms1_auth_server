import base64

from sqlalchemy.orm import exc
from authorization_server import models, oauth_code
from authorization_server.app import db
from unittest.mock import patch
from tests import utils as test_utils


def test_add_user_client_context_to_db():

    client_data, user_data = test_utils.add_user_client_context_to_db()
    # Following two statements
    try:
        db.session.query(models.User).one()
        db.session.query(models.Application).one()
    except (exc.NoResultFound, exc.MultipleResultsFound) as ex:
        raise AssertionError('There should only be one row per User and Client, respectively') from ex
    else:
        assert client_data and len(client_data) == 2
        assert user_data


def test_code_request_login_required(frontend_app):
    '''Ensure that views in auth are login-required

    1) When not logged in => User should be redirected to GrandType Login page
    2) When user is logged in => User will have access to the actual rendered view
    '''

    client_data, user_data = test_utils.add_user_client_context_to_db()

    # (1)
    response = frontend_app.get('/auth/code_request')
    assert response.status_code == 302
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['Forgot Password?', 'This application would like:'])

    # (2)
    test_utils.perform_logged_in(frontend_app, user_data)

    response = frontend_app.get('/auth/code_request')
    assert response.status_code == 400
    assert 'Bad Request' in response.get_data(as_text=True)


def test_code_request_view_400_error(frontend_app):
    ''' Test that the authorisation request url:

    1) If not provided a client_id argument => 400 error
    2) Provide a client_id that does not exists in the local db => 400 error
    3) If not provided a Base64_url encoded redirect_uri => 400 error
    4) Provide a Base64_url encoded redirect_uri that does not exist in the database => 400 error
    5) Otherwise it may be a 302 redirection
    '''

    client_data, user_data = test_utils.add_user_client_context_to_db()

    # log in the user
    test_utils.perform_logged_in(frontend_app, user_data)

    # (1)
    response = frontend_app.get('/auth/code_request')
    assert response.status_code == 400
    assert all([keyword in response.get_data(as_text=True)] for keyword in ['Bad Request', 'an invalid identifier'])

    # (2)
    response = frontend_app.get('/auth/code_request?client_id=doesnotexistindb')
    assert response.status_code == 400
    assert all([keyword in response.get_data(as_text=True)] for keyword in ['Bad Request', 'not registered with us'])

    # (3)
    client_id = client_data[0]['id']
    response = frontend_app.get(f'/auth/code_request?client_id={client_id}&redirect_uri=nourlbaseencode')
    assert response.status_code == 400
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['Bad Request', "'redirect_uri' argument is invalid"])

    # (4)
    redirect_uri = base64.urlsafe_b64encode('https://www.idonotexist.com'.encode()).decode()
    response = frontend_app.get(f'/auth/code_request?client_id={client_id}&redirect_uri={redirect_uri}')
    assert response.status_code == 400
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['Bad Request', "'redirect_uri' is not registered with us"])

    # (5)
    redirect_uri = base64.urlsafe_b64encode(client_data[0]['redirect_uri'].encode()).decode()
    response = frontend_app.get(f'/auth/code_request?client_id={client_id}&redirect_uri={redirect_uri}')
    assert response.status_code == 302


def test_code_request_view_302_error(frontend_app):
    '''Test that the authorisation request url:

    1) if response_type is not provided or unsupported => 302 redirection with errors occur
    2) if state is not provided -> 302 redirection with errors occur
    '''
    client_data, user_data = test_utils.add_user_client_context_to_db()

    # log in the user
    test_utils.perform_logged_in(frontend_app, user_data)

    # (1)
    client_id = client_data[0]['id']
    redirect_uri = base64.urlsafe_b64encode(client_data[0]['redirect_uri'].encode()).decode()
    response = frontend_app.get(f'/auth/code_request?client_id={client_id}&redirect_uri={redirect_uri}')
    assert response.status_code == 302
    assert 'unsupported_response_type' in response.headers.get('Location')

    # (2)
    response_type = oauth_code.AuthorisationCode.grand_type
    response = frontend_app.get(f'/auth/code_request?client_id={client_id}&'
                                f'redirect_uri={redirect_uri}&'
                                f'response_type={response_type}')
    assert response.status_code == 302
    assert all([keyword in response.headers.get('Location')] for keyword in ['state', 'unsupported_response_type'])


def test_code_request_view_200_successfully(frontend_app):
    '''Provided the write parameters in the authorisation request url, the resource owner is redirected to form for
    permission approval or revoke.
    '''

    client_data, user_data = test_utils.add_user_client_context_to_db()

    # log in the user
    test_utils.perform_logged_in(frontend_app, user_data)
    client_id = client_data[0]['id']
    redirect_uri = base64.urlsafe_b64encode(client_data[0]['redirect_uri'].encode()).decode()
    response_type = oauth_code.AuthorisationCode.grand_type
    state = 'Something the client sent in first instance'

    response = frontend_app.get(f'/auth/code_request?client_id={client_id}&'
                                f'redirect_uri={redirect_uri}&'
                                f'response_type={response_type}&'
                                f'state={state}')
    assert response.status_code == 200
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['This application would like:', 'Allow', 'Cancel'])
    with frontend_app.session_transaction() as session:
        assert 'auth_code_request' in session


def test_code_response_login_required(frontend_app):
    ''' If resource owner is not logged in => redirect to GrandType Login page
    '''
    client_data, user_data = test_utils.add_user_client_context_to_db()

    # (1)
    response = frontend_app.get('/auth/code_response')
    assert response.status_code == 302
    assert all([keyword in response.get_data(as_text=True)]
               for keyword in ['Forgot Password?', 'This application would like:'])


def test_code_response_view_302_wrong_source(frontend_app):
    '''Test 302 redirection cases for code_response as follows:

    1) If not coming from code_request view => redirect to code_request
    2) if does come from code_request view but the form was not submitted up there => redirect to code_request
    '''

    client_data, user_data = test_utils.add_user_client_context_to_db()
    test_utils.perform_logged_in(frontend_app, user_data)

    # (1)
    response = frontend_app.get('/auth/code_response')
    assert response.status_code == 302
    assert all(keywords in response.headers['Location'] for keywords in ('auth', 'code_request'))

    # (2)
    with frontend_app.session_transaction() as session:
        session['auth_code_request'] = 'something'

    response = frontend_app.get('/auth/code_response')
    assert response.status_code == 302
    assert all(keywords in response.headers['Location'] for keywords in ('auth', 'code_request'))


def test_code_response_view_302_cancel(frontend_app):
    '''Test 302 redirection back to the client when the resource owner explicitly denies the consent
    '''

    client_data, user_data = test_utils.add_user_client_context_to_db()
    test_utils.perform_logged_in(frontend_app, user_data)

    # Emulate that the auth_code request was successfully passed via session variable
    redirect_uri = 'http://client_domain.com/callback'
    state = 'checksum_issued_by_client'
    with frontend_app.session_transaction() as session:
        session['auth_code_request'] = {
            'redirect_uri': redirect_uri,
            'state': state
        }

    # Mock up that 'Cancel' button has been pressed
    with patch('authorization_server.auth.views.AuthorisationForm') as form:
        form.return_value.cancel.data = True
        response = frontend_app.get('/auth/code_response')

    assert response.status_code == 302
    # Client should get a contextual denial response
    assert all(keywords in response.headers['Location'] for keywords in (
        'error',
        'error_description',
        'state',
        redirect_uri,
        oauth_code.CLIENT_ACCESS_DENIED_ERROR,
        state
    ))


def test_code_response_view_302_allow(frontend_app):
    '''Test 302 redirection back to the client when the resource owner explicitly gives consent
    '''

    client_data, user_data = test_utils.add_user_client_context_to_db()
    test_utils.perform_logged_in(frontend_app, user_data)

    # Emulate that the auth_code request was successfully passed via session variable
    redirect_uri = 'http://client_domain.com/callback'
    state = 'checksum_issued_by_client'

    with frontend_app.session_transaction() as session:
        session['auth_code_request'] = {
            'redirect_uri': redirect_uri,
            'state': state,
            'client_id': client_data[0]['id']
        }

    assert not db.session.query(models.AuthorisationCode).all()
    # Mock up that 'OK' button has been pressed
    with patch('authorization_server.auth.views.AuthorisationForm') as form:
        form.return_value.cancel.data = False
        form.return_value.allow.data = True
        response = frontend_app.get('/auth/code_response')

    assert response.status_code == 302
    assert db.session.query(models.AuthorisationCode).one()
    assert all(keywords in response.headers['Location'] for keywords in (
        'code',
        'state',
        redirect_uri,
        state
    ))
