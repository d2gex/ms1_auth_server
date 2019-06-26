import base64
import binascii
import json

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


class AuthorisationCode:
    '''Implements the Authorisation Code Grand Type as per oAuth at https://www.oauth.com/oauth2-servers/authorization/
    '''

    grand_type = 'code'

    def __init__(self, **kwargs):
        '''
        :param kwargs: possible arguments are client_id, redirect_uri, response_type, state and scope
        '''
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.id = None
        self.name = None
        self.description = None
        self.web_url = None

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

        client_id = getattr(self, 'client_id', None)
        if not client_id:
            errors['error_description'] = 'The client application provided an invalid identifier'
            return errors

        try:
            client = db.session.query(models.Application).filter_by(id=client_id).one()
        except exc.NoResultFound:
            errors['error_description'] = 'This client application is not registered with us'
            return errors

        redirect_uri = getattr(self, 'redirect_uri', None)
        if redirect_uri:
            try:
                decoded_uri = base64.urlsafe_b64decode(redirect_uri.encode()).decode()
            except binascii.Error:
                errors['error_description'] = f"The client application's 'redirect_uri' argument is invalid"
            else:
                if decoded_uri != client.redirect_uri:
                    errors['error_description'] = f"The client application's 'redirect_uri' is not registered with us"
            if errors['error_description']:
                return errors

        response_type = getattr(self, 'response_type', None)
        if not response_type or response_type != self.grand_type:
            errors['addressee'] = CLIENT_ERROR
            errors['code'] = 200
            errors['error'] = CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
            errors['error_description'] = f"'response_type' argument '{response_type}' is not supported"
            return errors

        state = getattr(self, 'state', None)
        if state is None or not state.strip():
            errors['addressee'] = CLIENT_ERROR
            errors['code'] = 200
            errors['error'] = CLIENT_INVALID_REQUEST_ERROR
            errors['error_description'] = f"'state' argument '{state}' is invalid. A non-empty checksum is necessary"
            return errors

        self.id = client_id
        self.name = client.name
        self.description = client.description
        self.web_url = client.web_url
        self.redirect_uri = client.redirect_uri

        return True

    def response(self, client_id):
        '''Craft a response to be sent back to the client as specified by oAuth
        '''

        # Create a unique id in the database to be associated to this token
        auth_code = models.AuthorisationCode(application_id=client_id)
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
