import json

from flask_restplus import Resource, fields
from authorization_server import models
from authorization_server.app import db
from authorization_server.apis.namespace import NameSpace
from authorization_server.apis import utils, errors


api = NameSpace('registration', description="Resource used by clients to register with the Authorisation server")

registration_dto = api.model('Registration', {
    'name': fields.String(max_length=50, required=True, description='Name identifying the application client'),
    'description': fields.String(max_length=255, required=True, description='Description of the application client'),
    'email': fields.String(max_length=50, required=True, description='Email of the application client')
})


@api.route('/')
class Registration(Resource):

    @api.expect(registration_dto)
    @api.response_error(errors.BadRequest400Error(message=utils.RESPONSE_400))
    @api.response_error(errors.Conflict409Error(message=utils.RESPONSE_409))
    @api.response(201, json.dumps(utils.RESPONSE_201_REGISTRATION_POST), body=False)
    def post(self):
        '''Register a new application client
        '''

        if not isinstance(api.payload, dict):
            raise errors.BadRequest400Error(
                message='Incorrect type of object received. Instead a json object is expected',
                envelop=utils.RESPONSE_400)

        # Do we have all expected fields?
        expected_fields = registration_dto.keys()
        for key in expected_fields:
            if key not in api.payload:
                raise errors.BadRequest400Error(message=f"Required key '{key}' not found",
                                                envelop=utils.RESPONSE_400)

        # has the client already registered?
        if db.session.query(models.Application).filter_by(email=api.payload['email']).first():
            raise errors.Conflict409Error(message=f"Email '{api.payload['email']}' has already been registered",
                                          envelop=utils.RESPONSE_409)

        # Let's register the client
        data = api.payload
        data['id'] = models.Application.generate_id()
        db.session.add(models.Application(**data))
        db.session.commit()

        response = dict(utils.RESPONSE_201_REGISTRATION_POST)
        response['client_id'] = data['id']
        return response, 201
