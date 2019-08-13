import base64
import binascii
import json
import abc

from datetime import datetime, timedelta
from jwcrypto import jws, jwk, jwt
from sqlalchemy.orm import exc
from authorization_server import config, models
from authorization_server.app import db, bcrypt

CLIENT_INVALID_REQUEST_ERROR = 'invalid_request'
CLIENT_ACCESS_DENIED_ERROR = 'access_denied'
CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR = 'unsupported_response_type'
CLIENT_INVALID_SCOPE_ERROR = 'invalid_scope'
CLIENT_SERVER_ERROR = 'server_error'

RESOURCE_OWNER_ERROR = 1
CLIENT_ERROR = 2


class AuthorisationBase:

    grand_type = 'authorization_code'

    def __init__(self, url_args=None):
        '''
        :param url_args: MultiDict like data structure
        '''

        self.client_id = None
        self.redirect_uri = None
        self.state = None
        self.scope = None
        self.errors = None

        if url_args:
            for key in url_args:
                setattr(self, key, url_args[key])

    def as_dict(self):
        return self.__dict__

    @abc.abstractmethod
    def validate_request(self):
        pass

    @abc.abstractmethod
    def response(self):
        pass


class AuthorisationCode(AuthorisationBase):
    '''Implements the Authorisation Code Grand Type as per oAuth at https://www.oauth.com/oauth2-servers/authorization/
    '''

    def __init__(self, **kwargs):
        self.name = None
        self.description = None
        self.web_url = None
        self.response_type = None
        super().__init__(**kwargs)

    def validate_request(self):
        '''Validate a client authorisation request by returning an error if something unexpected was received.
        The errors have two categories:

        1) Errors that are addressed to the resource owner => 400
        2) Errors that are addressed to the client application => 200
        '''
        self.errors = {
            'addressee': RESOURCE_OWNER_ERROR,
            'code': 400,
            'error': None,
            'error_description': None
        }

        if not self.client_id:
            self.errors['error_description'] = 'The client application provided an invalid identifier'
            return False

        try:
            client = db.session.query(models.Application).filter_by(id=self.client_id).one()
        except exc.NoResultFound:
            self.errors['error_description'] = 'This client application is not registered with us'
            return False

        if self.redirect_uri:
            try:
                decoded_uri = base64.urlsafe_b64decode(self.redirect_uri.encode()).decode()
            except binascii.Error:
                self.errors['error_description'] = f"The client application's 'redirect_uri' argument is invalid"
            else:
                if decoded_uri != client.redirect_uri:
                    self.errors['error_description'] = f"The client application's 'redirect_uri' is not registered with us"
            if self.errors['error_description']:
                return False

        if not self.response_type or self.response_type != self.grand_type:
            self.errors['addressee'] = CLIENT_ERROR
            self.errors['code'] = 302
            self.errors['error'] = CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
            self.errors['error_description'] = f"'response_type' argument '{self.response_type}' is not supported"
            return False

        if self.state is None or not self.state.strip():
            self.errors['addressee'] = CLIENT_ERROR
            self.errors['code'] = 302
            self.errors['error'] = CLIENT_INVALID_REQUEST_ERROR
            self.errors['error_description'] = f"'state' argument '{self.state}' is invalid. A non-empty checksum " \
                                          f"is necessary"
            return False

        self.name = client.name
        self.description = client.description
        self.web_url = client.web_url
        self.redirect_uri = client.redirect_uri

        return True

    def response(self):
        '''Given a valid request, craft an 'authorization code' to be sent back to the client as specified by oAuth
        '''

        # Create a unique id in the database to be associated to this token
        auth_code = models.AuthorisationCode(application_id=self.client_id)
        db.session.add(auth_code)
        db.session.commit()

        exp_date = (datetime.utcnow() + timedelta(seconds=config.Config.AUTH_CODE_EXPIRATION_TIME)).\
            strftime("%d-%m-%Y %H:%M:%S")
        payload = {
            'client_id': self.client_id,
            'redirect_uri': base64.urlsafe_b64encode(self.redirect_uri.encode()).decode(),
            'expiration_date': exp_date,
            'code_id': auth_code.id
        }

        # Create a JWS with given payload
        jws_obj = jws.JWS(json.dumps(payload).encode(config.Config.AUTH_CODE_ENCODING))
        private_key = jwk.JWK.from_json(config.Config.private_jwk)
        jws_obj.add_signature(private_key, None, json.dumps({"alg": config.Config.JWT_ALGORITHM}))

        # return code and state as defined by oAuth
        return {
            'code': jws_obj.serialize(compact=True),
            'state': self.state
        }


class AuthorisationToken(AuthorisationBase):

    def __init__(self, **kwargs):
        self.code = None
        self.client_secret = None
        self.grand_type = None
        self.expiration_date = None
        self.code_id = None
        super().__init__(**kwargs)

    def validate_request(self):
        '''Validate a client authorisation request by returning an error if something unexpected was received. Errors
        are classified as 400, 401 and 403.
        '''

        self.errors = {
            'code': 400,
            'error': None,
            'error_description': None
        }

        # (1) ---> 400 Bad Request Errors
        if self.grand_type != super().grand_type:
            self.errors['error_description'] = "The client application did not provide the expected " \
                                               "'authorization_code' grand_type"
            return False

        if not self.code:
            self.errors['error_description'] = "The client application did not provide a authorisation code"
            return False

        if not self.client_secret:
            self.errors['error_description'] = "The client application did not provide a client_secret"
            return False

        # Ensure code is a valid JWS
        private_jwk = jwk.JWK.from_json(config.Config.JWK_PRIVATE)
        jws_obj = jws.JWS()
        try:
            jws_obj.deserialize(self.code)
        except jws.InvalidJWSObject:
            self.errors['error_description'] = "The client provided a non-valid representation of JWS"
            return False

        # (2) ---> 403 Forbidden Permission Errors
        self.errors['code'] = 403
        # Ensure code has been signed by us
        try:
            jws_obj.verify(private_jwk)
        except jws.InvalidJWSSignature:
            self.errors['error_description'] = 'The client application provided a token that has not been signed in ' \
                                              'this authorisation server'
            return False

        # Ensure payload has the fields expected
        payload = json.loads(jws_obj.payload.decode(config.Config.AUTH_CODE_ENCODING))
        expected_fields = ('client_id', 'redirect_uri', 'expiration_date', 'code_id')
        if not all(keywords in payload for keywords in expected_fields):
            self.errors['error_description'] = f"The client application did not provide all the required fields of " \
                                               f"the payload: '{', '.join(str(x) for x in expected_fields)}'"
            return False

        self.client_id = payload['client_id']
        self.redirect_uri = payload['redirect_uri']
        self.expiration_date = payload['expiration_date']
        self.code_id = payload['code_id']

        # Ensure both that the client provided exists and the existing code was issued by us previously
        try:
            db_auth, db_app = db.session.query(models.AuthorisationCode, models.Application).\
                filter(models.Application.id == models.AuthorisationCode.application_id).\
                filter(models.Application.id == self.client_id).\
                filter(models.AuthorisationCode.id == self.code_id).\
                one()
        # --> very unlikely scenario
        except exc.NoResultFound:
            self.errors['error_description'] = "Either the client does not exist in our records or the " \
                                               "'authorization_code' has not been issued by us"
            return False

        if db_auth.used:
            self.errors['error_description'] = "The client has used this 'authorization_code' already"
            return False

        # Ensure code has not expired
        if datetime.strptime(self.expiration_date, '%d-%m-%Y %H:%M:%S') > datetime.utcnow():
            self.errors['error_description'] = "The client provided an expired 'authorization_code'"
            return False

        # (3) ---> 401 Authentication Error
        # Ensure client_id and client_secret coincide
        if not bcrypt.check_password_hash(db_app.client_secret, self.client_secret):
            self.errors['code'] = 401
            self.errors['error_description'] = "The client provided a 'client_id' and 'client_secret' that don't match"
            return False

        if self.redirect_uri != db_app.redirect_uri:
            self.errors['code'] = 403
            self.errors['error_description'] = "The client provided a 'redirect_uri' that does not match our records"
            return False

        return True

    def response(self):
        '''Given a valid request, craft an 'authorization token' to be sent back to the client as specified by oAuth
        '''

        jwt_obj = jwt.JWT(header={"alg": config.Config.alg},
                          claims={'expires_in': config.Config.AUTH_TOKEN_EXPIRATION_TIME})
        jwt_obj.make_signed_token(jwk.JWK.from_json(config.Config.JWK_PRIVATE))
        signed_jwt_token = jwt_obj.serialize()
        return signed_jwt_token
