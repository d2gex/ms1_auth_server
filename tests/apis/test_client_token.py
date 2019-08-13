import json

from datetime import datetime, timedelta
from jwcrypto import jws, jwk
from authorization_server import models, config
from authorization_server.app import db
from tests import utils as test_utils

RESOURCE_URI = '/api/client/'


def generate_db_auth_code_context(client_secret=None):
    # --> Generate a valid authorization code
    client_data, user_data = test_utils.add_user_client_context_to_db()
    db_auth_code = models.AuthorisationCode(application_id=client_data[0]['id'])
    db.session.add(db_auth_code)
    db.session.commit()
    assert db_auth_code.id

    # --> Create an appropriate payload to be signed in
    now = datetime.utcnow()
    before = now - timedelta(seconds=10)
    payload = {
        'client_id': client_data[0]['id'],
        'redirect_uri': client_data[0]['redirect_uri'],
        'expiration_date': before.strftime("%d-%m-%Y %H:%M:%S"),
        'code_id': db_auth_code.id
    }

    # --> Sign the payload and generate the JWS authorization code
    jws_obj = jws.JWS(json.dumps(payload).encode(config.Config.AUTH_CODE_ENCODING))
    private_key = jwk.JWK.from_json(config.Config.private_jwk)
    jws_obj.add_signature(private_key, None, json.dumps({"alg": config.Config.JWT_ALGORITHM}))
    post_data = {
        'grand_type': 'authorization_code',
        'client_secret': client_data[0]['client_secret'] if not client_secret else client_secret,
        'code': jws_obj.serialize(compact=True)
    }
    return post_data, client_data, db_auth_code


def test_get_token_400_error(frontend_app):
    '''Test that when calling the client's get token endpoint the following 400 error are issued:

    1) if code, grand_type and client_secret are not provided
    2) If code has wrong format
    '''

    # (1.1)

    response = frontend_app.post(RESOURCE_URI, data=json.dumps([]))
    assert response.status_code == 400

    # (1.2)
    post_data = {
        'grand_type': 'authorization_code'
    }
    response = frontend_app.post(RESOURCE_URI, data=json.dumps(post_data), content_type='application/json')
    ret_data = response.get_json()
    assert response.status_code == 400
    assert all(keyword in ret_data['error']['message'] for keyword in ('Invalid receive', 'Required key'))

    # (2)
    post_data['code'] = 'Not a token'
    post_data['client_secret'] = 'not the password'
    response = frontend_app.post(RESOURCE_URI, data=json.dumps(post_data), content_type='application/json')
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message'] for keyword in ('Invalid receive', 'non-valid representation'))
    assert response.status_code == 400


def test_get_token_401_403_error(frontend_app):
    '''Test that when calling the client's get token endpoint a

    1) 401 error is issued if client's details do not match our records
    2) a 403 error is issued if somehow the authorization code has the right format but is invalid
    '''

    post_data, client_data, db_auth_code = generate_db_auth_code_context('not the expected password')

    # (1)
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message']
               for keyword in ('Unauthorised Access', "'client_secret' that don't match"))
    assert response.status_code == 401

    # (2)
    db_auth_code.used = True
    db.session.add(db_auth_code)
    db.session.commit()
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    ret_data = response.get_json()
    assert all(keyword in ret_data['error']['message']
               for keyword in ('Forbidden Access', "has used this 'authorization_code' already"))
    assert response.status_code == 403


def test_get_token_201_success(frontend_app):
    '''When the authorization code is valid, a token is issued back to the client.
    '''

    post_data, client_data, db_auth_code = generate_db_auth_code_context()
    response = frontend_app.post(RESOURCE_URI,
                                 data=json.dumps(post_data),
                                 content_type='application/json')
    assert response.status_code == 201
    assert all(keyword in response.headers for keyword in ('Cache-Control', 'Pragma'))
    ret_data = response.get_json()
    assert all(keyword in ret_data for keyword in ('token', 'token_type'))
