import string
from secrets import choice

RESPONSE_201 = "A new object has been created. Uri: {description}"
RESPONSE_201_REGISTRATION_POST = {'id': 'Unique Client ID'}
RESPONSE_201_VERIFICATION_POST = {'id': 'Unique Client ID', 'password': 'Accessing Password'}
RESPONSE_400 = "Invalid received data: {description}"
RESPONSE_409 = "An error while processing the request occurred. Please see error description: {description}"
RESPONSE_500 = "Internal Server Error. Please see error description: {description}"


def make_response(code, method=None, message=None):
    '''Build a response as a tuple (message, code) where the message is wrapped up with an envelop that is evaluated
    at runtime from these modules' CONSTANTS

    :param code: response code
    :param method: a suffix to add to the variable name
    :param message: response message
    :return: tuple response
    '''

    envelop = eval('RESPONSE_' + str(code) + ('' if not method else ('_' + method)))
    if message:
        envelop = envelop.replace('{description}', message)
    return {'message': envelop}, code


def generate_password(length):
    '''Generate a random alphanumeric password with a least one lowercase character, one uppercase and 3 digits
    '''
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and sum(c.isdigit() for c in password) >= 3):
            break
    return password
