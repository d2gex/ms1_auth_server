import base64

from authorization_server import models, oauth_grand_type as oauth_gt
from authorization_server.app import db
from tests import utils as test_utils


@test_utils.reset_database()
def test_valid_request():
    '''Ensure that a request is valid as follows:

    1) client_id is a required argument
    2) response_type is required and must be supported
    3) state is required and must valid
    4) client_id does not exist in the database
    5) redirect_uri, if provided, must match the one stored in the database
    6) Otherwise return True
    '''

    kwargs = {}
    # (1.1)
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.RO_TYPE_ERROR
    assert errors['error'] == oauth_gt.RO_CLIENT_ID_ERROR
    assert 'invalid identifier' in errors['error_description']

    kwargs['client_id'] = ''
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.RO_TYPE_ERROR
    assert errors['error'] == oauth_gt.RO_CLIENT_ID_ERROR
    assert 'invalid identifier' in errors['error_description']

    # (2.1)
    kwargs['client_id'] = 'something'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.CLIENT_TYPE_ERROR
    assert errors['error'] == oauth_gt.CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
    assert 'response_type' in errors['error_description']

    kwargs['response_type'] = 'unexpected value'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.CLIENT_TYPE_ERROR
    assert errors['error'] == oauth_gt.CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
    assert 'response_type' in errors['error_description']

    # (3.1)
    kwargs['response_type'] = oauth_gt.AuthorisationCode.grand_type
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.CLIENT_TYPE_ERROR
    assert errors['error'] == oauth_gt.CLIENT_INVALID_REQUEST_ERROR
    assert 'state' in errors['error_description']

    # (3.2)
    kwargs['state'] = "    "
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.CLIENT_TYPE_ERROR
    assert errors['error'] == oauth_gt.CLIENT_INVALID_REQUEST_ERROR
    assert 'state' in errors['error_description']

    # (4)
    kwargs['state'] = 'something'
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
    db.session.query(models.Application).one()  # It will throw an exception if there is no exactly one row in the table
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.RO_TYPE_ERROR
    assert errors['error'] == oauth_gt.RO_CLIENT_ID_ERROR
    assert 'not registered with us' in errors['error_description']

    # (5.1)
    kwargs['client_id'] = data[0]['id']
    kwargs['redirect_uri'] = 'this is not a base64url encoded'
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.CLIENT_TYPE_ERROR
    assert errors['error'] == oauth_gt.CLIENT_INVALID_REQUEST_ERROR
    assert 'redirect_uri' in errors['error_description']
    assert 'does not match the one' not in errors['error_description']

    # (5.2)
    kwargs['client_id'] = data[0]['id']
    kwargs['redirect_uri'] = base64.urlsafe_b64encode(b'this is not a base64url encoded').decode()
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    errors = auth_code.validate_request()
    assert errors['type'] == oauth_gt.CLIENT_TYPE_ERROR
    assert errors['error'] == oauth_gt.CLIENT_INVALID_REQUEST_ERROR
    assert all([keyword in errors['error_description']] for keyword in ('redirect_uri', 'does not match the one'))

    # (6)
    kwargs['redirect_uri'] = base64.urlsafe_b64encode(data[0]['redirect_uri'].encode()).decode()
    auth_code = oauth_gt.AuthorisationCode(**kwargs)
    success = auth_code.validate_request()
    assert success is True
