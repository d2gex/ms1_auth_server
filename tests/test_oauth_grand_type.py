import uuid
import base64
import json

from jwcrypto import jws, jwk
from authorization_server import config, models, oauth_grand_type as oauth_gt
from authorization_server.app import db
from tests import utils as test_utils


@test_utils.reset_database()
def test_valid_request():
    '''Ensure that a request is valid as follows:

    1) client_id is a required argument and must exist in the database
    2) redirect_uri, if provided, must match the one stored in the database
    3) response_type is required and must be supported
    4) state is required and must valid
    5) Otherwise return True
    '''

    kwargs = {}

    # (1.1)
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.RESOURCE_OWNER_ERROR
    assert errors['error'] is None
    assert 'invalid identifier' in errors['error_description']

    # (1.2)
    kwargs['client_id'] = ''
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.RESOURCE_OWNER_ERROR
    assert errors['error'] is None
    assert 'invalid identifier' in errors['error_description']

    # (1.3)
    kwargs['client_id'] = 'something'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.RESOURCE_OWNER_ERROR
    assert errors['error'] is None
    assert 'is not registered with us' in errors['error_description']

    # (2)
    # --> Pre-fill the database with some client data
    constraints = {
        'id': True,
        'email': True,
        'reg_token': True,
        'web_url': True,
        'redirect_uri': True,
        'name': True,
        'description': True
    }
    data = test_utils.generate_pair_client_model_data(constraints)
    db.session.add(models.Application(**data[0]))
    db.session.commit()
    # It will throw an exception if there is no exactly one row in the table
    db_data = db.session.query(models.Application).one()

    # -->(2.1)
    kwargs['client_id'] = db_data.id
    kwargs['redirect_uri'] = 'this is not a base64url encoded'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.RESOURCE_OWNER_ERROR
    assert errors['error'] is None
    assert all([words in errors['error_description']] for words in ('redirect_uri', 'does not match the one'))

    # --> (2.2)
    kwargs['redirect_uri'] = base64.urlsafe_b64encode(b'https://www.donotexist.com').decode()
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.RESOURCE_OWNER_ERROR
    assert errors['error'] is None
    assert all([words in errors['error_description']] for words in ('redirect_uri', 'is not registered with us'))

    # (3)
    kwargs['redirect_uri'] = base64.urlsafe_b64encode(db_data.redirect_uri.encode()).decode()
    kwargs['response_type'] = 'unexpected value'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.CLIENT_ERROR
    assert errors['error'] == oauth_gt.CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
    assert 'response_type' in errors['error_description']

    # (4.1)
    kwargs['response_type'] = oauth_gt.AuthorisationCode.grand_type
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.CLIENT_ERROR
    assert errors['error'] == oauth_gt.CLIENT_INVALID_REQUEST_ERROR
    assert 'state' in errors['error_description']

    # (4.2)
    kwargs['state'] = "    "
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['addressee'] == oauth_gt.CLIENT_ERROR
    assert errors['error'] == oauth_gt.CLIENT_INVALID_REQUEST_ERROR
    assert 'state' in errors['error_description']

    # (5)
    kwargs['state'] = 'something'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    success = auth_code.validate_request()
    assert success is True
    assert auth_code.id == db_data.id
    assert auth_code.name == db_data.name
    assert auth_code.description == db_data.description
    assert auth_code.web_url == db_data.web_url
    assert auth_code.redirect_uri == db_data.redirect_uri


@test_utils.reset_database()
def test_response():
    '''Ensure that response is up to the standards set by oAuth2
    '''

    # Prepare underlying database and request context for successful response generation
    # --> Create database context
    constraints = {
        'id': True,
        'email': True,
        'reg_token': True,
        'web_url': True,
        'redirect_uri': True,
        'name': True,
        'description': True
    }
    data = test_utils.generate_pair_client_model_data(constraints)
    db.session.add(models.Application(**data[0]))
    db.session.commit()
    db_data = db.session.query(models.Application).one()

    # --> Create request context
    kwargs = {
        'client_id': db_data.id,
        'response_type': oauth_gt.AuthorisationCode.grand_type,
        'state': str(uuid.uuid4()).replace('-', ''),
        'redirect_uri': base64.urlsafe_b64encode(db_data.redirect_uri.encode()).decode()
    }
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    assert auth_code.validate_request()

    # Get response
    signed_token = auth_code.response(db_data.id)
    # --> Ensure returned structured is the one expected
    assert all([key in signed_token] for key in ['code', 'state'])
    assert signed_token['state'] == kwargs['state']

    # Verify signature
    private_jwk = jwk.JWK.from_json(config.Config.JWK_PRIVATE)
    jws_obj = jws.JWS()
    jws_obj.deserialize(signed_token['code'])
    try:
        jws_obj.verify(private_jwk)
    except jws.InvalidJWSSignature as ex:
        raise AssertionError('An invalid signature exception was raised when should have not') from ex

    # Check payload is the one expected
    payload = json.loads(jws_obj.payload.decode(config.Config.AUTH_CODE_ENCODING))
    assert payload['client_id'] == kwargs['client_id']
    assert payload['redirect_uri'] == kwargs['redirect_uri']
    assert base64.urlsafe_b64decode(payload['redirect_uri'].
                                    encode(config.Config.AUTH_CODE_ENCODING)).decode() == db_data.redirect_uri
    auth_code_id = db.session.\
        query(models.AuthorisationCode.id).\
        order_by(models.AuthorisationCode.id.desc()).\
        limit(1).\
        scalar()
    assert payload['code_id'] == auth_code_id
