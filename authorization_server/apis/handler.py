from flask import Blueprint
from flask_restplus import Api
from authorization_server.apis import errors as api_errors
from authorization_server.apis.namespaces import registration, verification


api_v1 = Blueprint('apis', __name__)
api = Api(api_v1,
          title="Authorisation Server Api",
          version="0.1.0",
          description="An API to register and verify app clients as well as to provide authorising tokens")


@api.errorhandler
def default_error_handler(error):
    error = api_errors.Server500Error(message='Internal Server Error')
    return error.to_response()


@api.errorhandler(api_errors.BadRequest400Error)
@api.errorhandler(api_errors.Conflict409Error)
@api.errorhandler(api_errors.Server500Error)
def handle_error(error):
    return error.to_response()


api.add_namespace(registration.api, '/auth/registration')
api.add_namespace(verification.api, '/auth/verification')

