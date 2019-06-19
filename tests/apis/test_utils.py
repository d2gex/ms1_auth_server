import pytest

from authorization_server.apis import utils


def test_make_response():
    '''
    1) RESPONSE_<<CODE>> attribute is picked up
    2) RESPONSE_<<CODE>>_<<METHOD>> attribute is picked up
    3) Referencing to a CODE whose associated attribute does not exist => throw a NameError
    '''

    attributes = ['RESPONSE_700', 'RESPONSE_800_POST']
    ms_body = 'This a test string representing a non-existing NUMBER error {description}'
    setattr(utils, attributes[0], ms_body.replace('NUMBER', '700'))
    setattr(utils, attributes[1], ms_body.replace('NUMBER', '800'))

    try:
        assert all([keyword in utils.make_response(700, message='Custom Description')]
                   for keyword in ('non-existing 700', 'Custom Description'))

        assert all([keyword in utils.make_response(800, method='POST', message='Custom Description')]
                   for keyword in ('non-existing 700', 'Custom Description'))

        with pytest.raises(NameError):
            utils.make_response(900)

    finally:
        list([delattr(utils, x) for x in attributes])
        assert not all([getattr(utils, x, None) for x in attributes])


def test_generate_password():
    '''Ensure all generated passwords has at least one lowercase, 1 uppercase and 3 digits
    '''
    for _ in range(30):
        password = utils.generate_password(10)
        assert len(password) == 10
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert sum(c.isdigit() for c in password) >= 3
