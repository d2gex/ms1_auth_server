import base64
import binascii
import json
import abc

from datetime import datetime, timedelta
from jwcrypto import jws, jwk
from sqlalchemy.orm import exc
from authorization_server import config, models
from authorization_server.app import db

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

    def __init__(self, url_args=None):
        self.name = None
        self.description = None
        self.web_url = None
        self.response_type = None
        super().__init__(url_args)

    def validate_request(self):
        '''Validate a client authorisation request by returning an error if something unexpected was received.
        The errors have two categories:
        1) Errors that are addressed to the resource owner => 400
        2) Errors that are addressed to the client application => 200
        '''
        errors = {
            'addressee': RESOURCE_OWNER_ERROR,
            'code': 400,
            'error': None,
            'error_description': None
        }

        if not self.client_id:
            errors['error_description'] = 'The client application provided an invalid identifier'
            self.errors = errors
            return False

        try:
            client = db.session.query(models.Application).filter_by(id=self.client_id).one()
        except exc.NoResultFound:
            errors['error_description'] = 'This client application is not registered with us'
            self.errors = errors
            return False

        if self.redirect_uri:
            try:
                decoded_uri = base64.urlsafe_b64decode(self.redirect_uri.encode()).decode()
            except binascii.Error:
                errors['error_description'] = f"The client application's 'redirect_uri' argument is invalid"
            else:
                if decoded_uri != client.redirect_uri:
                    errors['error_description'] = f"The client application's 'redirect_uri' is not registered with us"
            if errors['error_description']:
                self.errors = errors
                return False

        if not self.response_type or self.response_type != self.grand_type:
            errors['addressee'] = CLIENT_ERROR
            errors['code'] = 302
            errors['error'] = CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
            errors['error_description'] = f"'response_type' argument '{self.response_type}' is not supported"
            self.errors = errors
            return False

        if self.state is None or not self.state.strip():
            errors['addressee'] = CLIENT_ERROR
            errors['code'] = 302
            errors['error'] = CLIENT_INVALID_REQUEST_ERROR
            errors['error_description'] = f"'state' argument '{self.state}' is invalid. A non-empty checksum " \
                                          f"is necessary"
            self.errors = errors
            return False

        self.name = client.name
        self.description = client.description
        self.web_url = client.web_url
        self.redirect_uri = client.redirect_uri

        return True

    def response(self):
        '''Craft a response to be sent back to the client as specified by oAuth
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
