import json

from sqlalchemy.orm import exc
from flask import request
from flask_restplus import Resource, fields
from authorization_server import models
from authorization_server.app import db, bcrypt
from authorization_server.apis.namespace import NameSpace
from authorization_server.apis import utils as api_utils, errors as api_errors

api = NameSpace('client', description="Resources used by clients to register, verify and get JWT Token with the "
                                      "Authorisation server")

registration_dto = api.model('Registration', {
    'name': fields.String(max_length=50, required=True, description='Name identifying the client application'),
    'description': fields.String(max_length=255, required=True, description='Description of the clientapplication'),
    'email': fields.String(max_length=50, required=True, description='Email of the client application'),
    'redirect_uri': fields.String(max_length=255,
                                  required=True,
                                  description="Client application's url to where the resource owner will be redirected "
                                              "to after authorisation code is issued"),
    'web_url': fields.String(max_length=255, required=True, description='Main url of the client application. '
                                                                        'Typically https://www.appclient.com')
})

verification_dto = api.model('Verification', {
    'id': fields.String(max_length=40, required=True, description='Unique client_id representing the client'),
    'reg_token': fields.String(max_length=40, required=True, description='One-off token to verify the registration')
})


@api.route('/registration')
class Registration(Resource):

    @api.expect(registration_dto)
    @api.response_error(api_errors.BadRequest400Error(message=api_utils.RESPONSE_400))
    @api.response_error(api_errors.Conflict409Error(message=api_utils.RESPONSE_409))
    @api.response(201, json.dumps(api_utils.RESPONSE_201_REGISTRATION_POST), body=False)
    def post(self):
        '''Register a new client application
        '''

        if not isinstance(api.payload, dict):
            raise api_errors.BadRequest400Error(
                message='Incorrect type of object received. Instead a json object is expected',
                envelop=api_utils.RESPONSE_400)

        # Do we have all expected fields?
        expected_fields = registration_dto.keys()
        for key in expected_fields:
            if key not in api.payload:
                raise api_errors.BadRequest400Error(message=f"Required key '{key}' not found",
                                                    envelop=api_utils.RESPONSE_400)

        # Ensure that both the received redirect_uri and web_url are valid and start by https
        if not all(map(api_utils.is_url_valid, (api.payload['web_url'], api.payload['redirect_uri']))):
            raise api_errors.Conflict409Error(message=f"Either the 'redirect_uri' or 'web_url' is not a valid url. "
                                                      f"A valid url must start by 'https://'",
                                              envelop=api_utils.RESPONSE_409)

        # has the client already registered?
        if db.session.query(models.Application).filter_by(email=api.payload['email']).first():
            raise api_errors.Conflict409Error(message=f"Email '{api.payload['email']}' has already been registered",
                                              envelop=api_utils.RESPONSE_409)

        # Let's register the client
        data = api.payload
        data['id'] = models.Application.generate_id()
        db.session.add(models.Application(**data))
        db.session.commit()

        response = dict(api_utils.RESPONSE_201_REGISTRATION_POST)
        response['id'] = data['id']
        return response, 201


@api.route('/verification')
class Verification(Resource):

    @api.expect(verification_dto)
    @api.response_error(api_errors.BadRequest400Error(message=api_utils.RESPONSE_400))
    @api.response_error(api_errors.Conflict409Error(message=api_utils.RESPONSE_409))
    @api.response(201, json.dumps(api_utils.RESPONSE_201_VERIFICATION_POST), body=False)
    def post(self):
        '''Verify a client application registration given a one-off token provided a registration time
        '''

        if not isinstance(api.payload, dict):
            raise api_errors.BadRequest400Error(
                message='Incorrect type of object received. Instead a json object is expected',
                envelop=api_utils.RESPONSE_400)

        # Do we have all expected fields?
        expected_fields = verification_dto.keys()
        for key in expected_fields:
            if key not in api.payload:
                raise api_errors.BadRequest400Error(message=f"Required key '{key}' not found",
                                                    envelop=api_utils.RESPONSE_400)

        # Client should exist, should not have verified before and the token should match the one stored in the db
        try:
            db_data = db.session.\
                query(models.Application).\
                filter_by(id=api.payload['id'], reg_token=api.payload['reg_token'], is_allowed=True).\
                one()
        except exc.NoResultFound:
            raise api_errors.Conflict409Error(message=f"Client '{api.payload['id']}' may not yet have registered "
                                                      f"or token is invalid. Please register first at "
                                                      f"{request.url.replace('verification', 'registration')}",
                                              envelop=api_utils.RESPONSE_409)
        else:
            client_secret = api_utils.generate_password(10)
            db_data.client_secret = bcrypt.generate_password_hash(client_secret).decode('utf-8')
            db_data.token = None
            db.session.add(db_data)
            db.session.commit()

            response = dict(api_utils.RESPONSE_201_VERIFICATION_POST)
            response['id'] = db_data.id
            response['client_secret'] = client_secret
            return response, 201
