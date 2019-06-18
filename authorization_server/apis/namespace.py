import json

from flask_restplus import Namespace


class NameSpace(Namespace):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def response(self, code, description, model=None, **kwargs):

        to_json = kwargs.get('to_json', True)
        body = kwargs.get('body', True)

        if body:
            response = {'message': description}
            message = response if not to_json else json.dumps(response)
        else:
            message = description
        return self.doc(responses={code: (message, model, kwargs)})

    def response_error(self, exception, model=None, **kwargs):
        '''A decorator to specify one of the expected error responses

        :param ApiError exception: An exception instance of errors.ApiError
        :param ModelBase model: an optional response model
        '''

        to_json = kwargs.get('to_json', True)
        message = exception.as_dict() if not to_json else json.dumps(exception.as_dict())
        return self.doc(responses={exception.code: (message, model, kwargs)})
