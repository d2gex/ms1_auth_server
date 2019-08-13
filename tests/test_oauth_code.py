import pytest
import uuid
import base64
import json

from datetime import datetime, timedelta
from jwcrypto import jws, jwk, jwt
from authorization_server import config, models, oauth_code
from authorization_server.app import db
from unittest.mock import patch
from tests import utils as test_utils


@pytest.fixture(scope='module')
def other_private_jwk():
    jwk_obj = jwk.JWK.generate(kty='RSA', size=2048)
    private_key_obj = json.loads(jwk_obj.export_private())
    private_key_obj['alg'] = config.Config.alg
    return jwk.JWK.from_json(json.dumps(private_key_obj))


def test_asdict():
    auth_code = oauth_code.AuthorisationCode()
    assert all([getattr(auth_code, key) == value for key, value in auth_code.as_dict().items()])


class TestAuthorisationCode:

    def test_valid_request(self):
        '''Ensure that a request is valid as follows:

        1) client_id is a required argument and must exist in the database
        2) redirect_uri, if provided, must match the one stored in the database
        3) response_type is required and must be supported
        4) state is required and must valid
        5) Otherwise return True
        '''

        url_args = {}

        # (1.1)
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.RESOURCE_OWNER_ERROR
        assert errors['error'] is None
        assert 'invalid identifier' in errors['error_description']

        # (1.2)
        url_args['client_id'] = ''
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.RESOURCE_OWNER_ERROR
        assert errors['error'] is None
        assert 'invalid identifier' in errors['error_description']

        # (1.3)
        url_args['client_id'] = 'something'
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.RESOURCE_OWNER_ERROR
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
        url_args['client_id'] = db_data.id
        url_args['redirect_uri'] = 'this is not a base64url encoded'
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.RESOURCE_OWNER_ERROR
        assert errors['error'] is None
        assert all([words in errors['error_description']] for words in ('redirect_uri', 'does not match the one'))

        # --> (2.2)
        url_args['redirect_uri'] = base64.urlsafe_b64encode(b'https://www.donotexist.com').decode()
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.RESOURCE_OWNER_ERROR
        assert errors['error'] is None
        assert all([words in errors['error_description']] for words in ('redirect_uri', 'is not registered with us'))

        # (3)
        url_args['redirect_uri'] = base64.urlsafe_b64encode(db_data.redirect_uri.encode()).decode()
        url_args['response_type'] = 'unexpected value'
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.CLIENT_ERROR
        assert errors['error'] == oauth_code.CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
        assert 'response_type' in errors['error_description']

        # (4.1)
        url_args['response_type'] = oauth_code.AuthorisationCode.grand_type
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.CLIENT_ERROR
        assert errors['error'] == oauth_code.CLIENT_INVALID_REQUEST_ERROR
        assert 'state' in errors['error_description']

        # (4.2)
        url_args['state'] = "    "
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert not auth_code.validate_request()
        errors = auth_code.errors
        assert errors['addressee'] == oauth_code.CLIENT_ERROR
        assert errors['error'] == oauth_code.CLIENT_INVALID_REQUEST_ERROR
        assert 'state' in errors['error_description']

        # (5)
        url_args['state'] = 'something'
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert auth_code.validate_request()
        assert auth_code.client_id == db_data.id
        assert auth_code.name == db_data.name
        assert auth_code.description == db_data.description
        assert auth_code.web_url == db_data.web_url
        assert auth_code.redirect_uri == db_data.redirect_uri

    def test_response(self):
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
        url_args = {
            'client_id': db_data.id,
            'response_type': oauth_code.AuthorisationCode.grand_type,
            'state': str(uuid.uuid4()).replace('-', ''),
            'redirect_uri': base64.urlsafe_b64encode(db_data.redirect_uri.encode()).decode()
        }
        auth_code = oauth_code.AuthorisationCode(url_args=url_args)
        assert auth_code.validate_request()

        # Get response
        signed_token = auth_code.response()
        # --> Ensure returned structured is the one expected
        assert all([key in signed_token] for key in ['code', 'state'])
        assert signed_token['state'] == url_args['state']

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
        assert payload['client_id'] == url_args['client_id']
        assert payload['redirect_uri'] == url_args['redirect_uri']
        assert base64.urlsafe_b64decode(payload['redirect_uri'].
                                        encode(config.Config.AUTH_CODE_ENCODING)).decode() == db_data.redirect_uri
        auth_code_id = db.session.\
            query(models.AuthorisationCode.id).\
            order_by(models.AuthorisationCode.id.desc()).\
            limit(1).\
            scalar()
        assert payload['code_id'] == auth_code_id


class TestAuthorisationToken:

    def test_valid_request_grand_type(self):
        '''Ensure grand_type url parameter is passed and valid
        '''

        auth_token = oauth_code.AuthorisationToken(url_args=None)
        assert not auth_token.validate_request()
        assert all(keywords in auth_token.errors['error_description']
                   for keywords in ("'authorization_code'", 'grand_type'))
        assert auth_token.errors['code'] == 400

        auth_token.grand_type = 'something unexpected'
        assert not auth_token.validate_request()
        assert all(keywords in auth_token.errors['error_description']
                   for keywords in ("'authorization_code'", 'grand_type'))
        assert auth_token.errors['code'] == 400

        auth_token.grand_type = 'authorization_code'
        assert not auth_token.validate_request()
        assert 'authorisation code' in auth_token.errors['error_description']
        assert auth_token.errors['code'] == 400

    def test_client_secret_provided(self):
        '''Ensure client_secret url parameter has been provided
        '''
        url_args = {'grand_type': 'authorization_code', 'code': 'Not a valid token'}
        auth_token = oauth_code.AuthorisationToken(url_args=url_args)
        assert not auth_token.validate_request()
        assert 'did not provide a client_secret' in auth_token.errors['error_description']
        assert auth_token.errors['code'] == 400

    def test_valid_request_correct_url_code(self, other_private_jwk):
        '''Ensure that the a code url parameter is passed and is valid
        '''

        url_args = {'grand_type': 'authorization_code',
                    'client_secret': 'something',
                    'code': 'Not a valid token'}

        # ---> Invalid representation of JWS Format
        auth_token = oauth_code.AuthorisationToken(url_args=url_args)
        assert not auth_token.validate_request()
        assert 'non-valid representation' in auth_token.errors['error_description']
        assert auth_token.errors['code'] == 400

        # ---> JWS has not been signed by us
        # Create a JWS with given payload and a different private key
        payload = {'dummy': 'data'}
        jws_obj = jws.JWS(json.dumps(payload).encode(config.Config.AUTH_CODE_ENCODING))
        jws_obj.add_signature(other_private_jwk, None, json.dumps({"alg": config.Config.JWT_ALGORITHM}))
        auth_token.code = jws_obj.serialize(compact=True)

        assert not auth_token.validate_request()
        assert 'token that has not been signed in' in auth_token.errors['error_description']
        assert auth_token.errors['code'] == 403

    def test_valid_request_correct_url_code_payload_fields(self):
        '''Ensure all fields in the payload are the ones expected and are valid
        '''

        url_args = {'grand_type': 'authorization_code',
                    'client_secret': 'something',
                    'code': 'Not a valid token'}
        auth_token = oauth_code.AuthorisationToken(url_args=url_args)

        with patch.object(oauth_code, 'jwk'):
            with patch.object(oauth_code, 'jws'):
                with patch.object(oauth_code.json, 'loads') as mock_loads:
                    # No fields
                    mock_loads.return_value = {}
                    assert not auth_token.validate_request()
                    assert 'did not provide all the required fields' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    # only 'client_id' provided
                    mock_loads.return_value = {
                        'client_id': '',
                    }
                    assert not auth_token.validate_request()
                    assert 'did not provide all the required fields' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    # only 'client_id'  and 'redirect_uri' provided
                    mock_loads.return_value = {
                        'client_id': '',
                        'redirect_uri': '',
                    }
                    assert not auth_token.validate_request()
                    assert 'did not provide all the required fields' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    # only 'client_id', 'redirect_uri' and 'expiration_date' provided
                    mock_loads.return_value = {
                        'client_id': '',
                        'redirect_uri': '',
                        'expiration_date': '',
                    }
                    assert not auth_token.validate_request()
                    assert 'did not provide all the required fields' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    mock_loads.return_value = {
                        'client_id': '',
                        'redirect_uri': '',
                        'expiration_date': '',
                        'code_id': ''
                    }
                    # client_id and/or code_id are not recognised
                    assert not auth_token.validate_request()
                    assert 'Either the client does not exist' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

    def test_valid_request_correct_url_code_payload_fields_and_values(self):
        '''Ensure that fields provided in the payload are those expected and the authorisation code provided was not
        used before
        '''

        # Prepare underlying database so that an application and code exist
        client_data, user_data = test_utils.add_user_client_context_to_db()
        db_auth_code = models.AuthorisationCode(application_id=client_data[0]['id'],  used=True)
        db.session.add(db_auth_code)
        db.session.commit()
        assert db_auth_code.id

        url_args = {'grand_type': 'authorization_code',
                    'client_secret': 'something',
                    'code': 'Not a valid token'}
        auth_token = oauth_code.AuthorisationToken(url_args=url_args)

        with patch.object(oauth_code, 'jwk'):
            with patch.object(oauth_code, 'jws'):
                with patch.object(oauth_code.json, 'loads') as mock_loads:

                    # If either client_id or code_id does not exist
                    payload = {
                        'client_id': 'something that does not match our records',
                        'redirect_uri': '',
                        'expiration_date': '',
                        'code_id': db_auth_code.id
                    }
                    mock_loads.return_value = payload
                    assert not auth_token.validate_request()
                    assert 'Either the client does not exist' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    payload['client_id'] = db_auth_code.application_id
                    payload['code_id'] = 5555555555
                    assert not auth_token.validate_request()
                    assert 'Either the client does not exist' in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    # If code has already being used
                    payload['code_id'] = db_auth_code.id
                    assert not auth_token.validate_request()
                    assert "'authorization_code' already" in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    # If code has expired
                    db_auth_code.used = False
                    db.session.commit()
                    now = datetime.utcnow()
                    after = now + timedelta(seconds=10)
                    payload['expiration_date'] = after.strftime("%d-%m-%Y %H:%M:%S")
                    assert not auth_token.validate_request()
                    assert "expired" in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

                    # if client_id and client_secret do not coincide
                    before = now - timedelta(seconds=10)
                    payload['expiration_date'] = before.strftime("%d-%m-%Y %H:%M:%S")
                    assert not auth_token.validate_request()
                    assert "that don't match" in auth_token.errors['error_description']
                    auth_token.client_secret = 'no within the database'
                    assert not auth_token.validate_request()
                    assert "that don't match" in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 401

                    # if redirect_uri does not match our records
                    auth_token.client_secret = client_data[0]['client_secret']
                    payload['redirect_uri'] = 'something that does not exist in the db'
                    assert not auth_token.validate_request()
                    assert "'redirect_uri'" in auth_token.errors['error_description']
                    assert auth_token.errors['code'] == 403

    def test_response(self):
        '''Test the issuing of a Authorisation Token. A Token that encrypted by us should also be able to be
        decrypted by the public key.
        '''

        auth_token = oauth_code.AuthorisationToken()
        signed_jwt_token = auth_token.response()
        assert len(signed_jwt_token.split('.')) == 3

        raw_token = jwt.JWT(key=jwk.JWK.from_json(config.Config.JWK_PUBLIC), jwt=signed_jwt_token)
        payload = {'expires_in': config.Config.AUTH_TOKEN_EXPIRATION_TIME}
        assert json.loads(raw_token.claims) == payload
