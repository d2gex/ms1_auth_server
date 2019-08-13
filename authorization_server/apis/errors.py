class ApiError(Exception):
    """Base Error Class"""

    def __init__(self, message=None, envelop=None):
        super().__init__()
        self.envelop = envelop
        self.code = 400
        self.message = message
        # message could be a) the message only; b) the envelop only; c) both the envelop and the message
        if self.envelop and self.message:
            self.message = self.envelop.replace('{description}', self.message)
        elif self.envelop:
            self.message = self.envelop

    def as_dict(self):
        return {
            'error': {
                'code': self.code,
                'message': self.message
            }
        }

    def to_response(self):
        return self.as_dict(), self.code


class BadRequest400Error(ApiError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = 400


class NotAuthorization401(ApiError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = 401


class Forbidden403Error(ApiError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = 403


class NotFound404Error(ApiError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = 404


class Conflict409Error(ApiError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = 409


class Server500Error(ApiError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = 500
