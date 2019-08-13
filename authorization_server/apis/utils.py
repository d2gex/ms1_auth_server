import string
import re

from secrets import choice

RESPONSE_201 = "A new object has been created. Uri: {description}"
RESPONSE_201_REGISTRATION_POST = {'id': 'Unique Client ID'}
RESPONSE_201_VERIFICATION_POST = {'id': 'Unique Client ID', 'client_secret': "Client's secret password"}
RESPONSE_201_TOKEN_POST = {'token': 'JWT Access Token', 'token_type': "Type of token issued. Only 'bearer' supported"}
RESPONSE_400 = "Invalid received data: {description}"
RESPONSE_401 = "Unauthorised Access to resource: Please see error description: {description}"
RESPONSE_403 = "Forbidden Access to resource: Please see error description: {description}"
RESPONSE_404 = "The required object has not been found. Please see error description: {description}"
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


def is_url_valid(url):
    '''Check whether an url is valid using Django Validation rules:
    https://codereview.stackexchange.com/questions/19663/http-url-validating. However we don't want to scrape
    ftp-like urls
    '''

    url_regex = re.compile(
        r'^(?:https)://'  # https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return url_regex.match(url) is not None
