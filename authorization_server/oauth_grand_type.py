import base64
import binascii

from sqlalchemy.orm import exc
from authorization_server import models
from authorization_server.app import db

CLIENT_INVALID_REQUEST_ERROR = 'invalid_request'
CLIENT_ACCESS_DENIED_ERROR = 'access_denied'
CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR = 'unsupported_response_type'
CLIENT_INVALID_SCOPE_ERROR = 'invalid_scope'
CLIENT_SERVER_ERROR = 'server_error'

RO_CLIENT_ID_ERROR = 'invalid_client_id'
RO_REDIRECT_URI_ERROR = 'invalid_redirect_ui'

RO_TYPE_ERROR = 'resource_owner'
CLIENT_TYPE_ERROR = 'client'


class AuthorisationCode:
    '''Implements the Authorisation Code Grand Type as per oAuth at https://www.oauth.com/oauth2-servers/authorization/
    '''

    grand_type = 'code'

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def validate_request(self):
        '''Validate a client request starting first by those operations that do not require looking into the database.
        '''
        errors = {
            'type': RO_TYPE_ERROR,
            'error': None,
            'error_description': None
        }

        client_id = getattr(self, 'client_id', None)
        if not client_id:
            errors['error'] = RO_CLIENT_ID_ERROR
            errors['error_description'] = 'The client application provided an invalid identifier'
            return errors

        response_type = getattr(self, 'response_type', None)
        if not response_type or response_type != self.grand_type:
            errors['type'] = CLIENT_TYPE_ERROR
            errors['error'] = CLIENT_UNSUPPORTED_RESPONSE_TYPE_ERROR
            errors['error_description'] = f"'response_type' argument '{response_type}' is not supported"
            return errors

        state = getattr(self, 'state', None)
        if state is None or not state.strip():
            errors['type'] = CLIENT_TYPE_ERROR
            errors['error'] = CLIENT_INVALID_REQUEST_ERROR
            errors['error_description'] = f"'state' argument '{state}' is invalid. A non-empty checksum is necessary"
            return errors

        try:
            client = db.session.query(models.Application).filter_by(id=client_id).one()
        except exc.NoResultFound:
            errors['type'] = RO_TYPE_ERROR
            errors['error'] = RO_CLIENT_ID_ERROR
            errors['error_description'] = 'This client application is not registered with us'
            return errors

        redirect_uri = getattr(self, 'redirect_uri', None)
        if redirect_uri:
            errors['type'] = CLIENT_TYPE_ERROR
            errors['error'] = CLIENT_INVALID_REQUEST_ERROR
            try:
                decoded_uri = base64.urlsafe_b64decode(redirect_uri.encode()).decode()
            except binascii.Error:
                errors['error_description'] = f"'redirect_uri' argument '{redirect_uri}' is not a base64URL encoded"
            else:
                if decoded_uri != client.redirect_uri:
                    errors['error_description'] = f"'redirect_uri' argument '{redirect_uri}' does not match the one " \
                                                  f"registered or it is not base64URL encoded"
            if errors['error_description']:
                return errors

        return True

    def response(self):
        # TO-DO
        raise NotImplementedError
