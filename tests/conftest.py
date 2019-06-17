import pytest

from authorization_server import config
from authorization_server.app import create_app


@pytest.fixture
def frontend_app():
    app = create_app(config_class=config.TestingConfig)
    frontend = app.test_client(use_cookies=True)
    return frontend
