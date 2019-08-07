import pytest

from authorization_server import utils
from unittest.mock import patch, MagicMock


@pytest.fixture
def reset_database():
    pass


def test_init_class():

    @utils.init_class
    class Stub:

        x = None

        @classmethod
        def init(cls):
            cls.x = 10

    assert Stub.x == 10


def test_login_required():
    '''Ensure the decorator works as follows:

    1)  if LOGIN_DISABLED is actually set to true => the decorated function is called
    2)  if LOGIN_DISABLED is set to False and user is authenticated => the decorated function is called
    3)  Otherwise redirect user to provided route with the given query_string parameters, including those in
        request.args if request_args=True
    4) Same as 3) but only the additional query_string parameters are passed when request_args=False
    '''

    fake_view_called = 'yes'
    additional_arguments = {'another_argument': 'something'}
    route = 'blueprint.route'

    # (1)
    with patch.object(utils.current_app.config, 'get', return_value=True):
        with patch.object(utils, 'current_user') as mock_current_user:
            @utils.login_required(route, request_args=True, **additional_arguments)
            def fake_view():
                return fake_view_called

            ret = fake_view()
            assert ret == fake_view_called
            mock_current_user.assert_not_called()

    # (2)
    with patch.object(utils.current_app.config, 'get', return_value=False):
        with patch.object(utils, 'current_user') as mock_current_user:
            with patch.object(utils, 'redirect') as mock_redirect:
                @utils.login_required(route, request_args=True, **additional_arguments)
                def fake_view():
                    return fake_view_called

                mock_current_user.is_authenticated = True
                ret = fake_view()
                assert ret == fake_view_called
                mock_redirect.assert_not_called()

    #
    with patch.object(utils.current_app.config, 'get', return_value=False):
        with patch.object(utils, 'current_user') as mock_current_user:
            with patch.object(utils, 'request') as mock_request:
                with patch.object(utils, 'redirect') as mock_redirect:
                    with patch.object(utils, 'url_for') as mock_url_for:
                        @utils.login_required(route, request_args=True, **additional_arguments)
                        def fake_view():
                            return fake_view_called

                        mock_request.args = {'arg1': 'value1', 'arg2': 'value2'}
                        mock_current_user.is_authenticated = False
                        # (3)
                        ret = fake_view()
                        assert isinstance(ret, MagicMock)  # Now a new instance of mock_redirect is returned
                        query_strings = mock_request.args
                        query_strings.update(additional_arguments)
                        mock_redirect.assert_called_once()
                        mock_url_for.assert_called_once_with(route, **query_strings)

                        # (4)
                        mock_redirect.reset_mock()
                        mock_url_for.reset_mock()

                        @utils.login_required(route, request_args=False, **additional_arguments)
                        def fake_view_2():
                            return fake_view_called

                        ret = fake_view_2()
                        assert isinstance(ret, MagicMock)  # Now a new instance of mock_redirect is returned
                        query_strings = additional_arguments
                        mock_redirect.assert_called_once()
                        mock_url_for.assert_called_once_with(route, **query_strings)
