import json

from flask import request
from sqlalchemy.orm import exc
from flask_restplus import Resource, fields
from authorization_server import models
from authorization_server.app import db, bcrypt
from authorization_server.apis.namespace import NameSpace
from authorization_server.apis import utils, errors as api_errors


api = NameSpace('verification', description="Resource used by clients to verify their registration with the "
                                            "Authorisation server")

verification_dto = api.model('Verification', {
    'id': fields.String(max_length=40, required=True, description='Unique client_id representing the client'),
    'reg_token': fields.String(max_length=40, required=True, description='One-off token to verify the registration')
})


@api.route('/')
class Verification(Resource):

    @api.expect(verification_dto)
    @api.response_error(api_errors.BadRequest400Error(message=utils.RESPONSE_400))
    @api.response_error(api_errors.Conflict409Error(message=utils.RESPONSE_409))
    @api.response(201, json.dumps(utils.RESPONSE_201_VERIFICATION_POST), body=False)
    def post(self):
        '''Register a new application client
        '''

        if not isinstance(api.payload, dict):
            raise api_errors.BadRequest400Error(
                message='Incorrect type of object received. Instead a json object is expected',
                envelop=utils.RESPONSE_400)

        # Do we have all expected fields?
        expected_fields = verification_dto.keys()
        for key in expected_fields:
            if key not in api.payload:
                raise api_errors.BadRequest400Error(message=f"Required key '{key}' not found",
                                                    envelop=utils.RESPONSE_400)

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
                                              envelop=utils.RESPONSE_409)
        else:
            password = utils.generate_password(10)
            db_data.password = bcrypt.generate_password_hash(password).decode('utf-8')
            db_data.token = None
            db.session.add(db_data)
            db.session.commit()

            response = dict(utils.RESPONSE_201_VERIFICATION_POST)
            response['id'] = db_data.id
            response['password'] = password
            return response, 201
