import pytest
import shutil

from authorization_server import config
from authorization_server.app import create_app
from tests import utils as test_utils


class TestConfig(config.Config):

    # Needed for form's unit test validation
    WTF_CSRF_ENABLED = False

    # Needed for flask_beaker_session extension
    SESSION_TESTING = True
    SESSION_DATA_DIR = './.sessions'


@pytest.fixture(scope='session', autouse=True)
@test_utils.reset_database(tear='down')
def reset_test_suite():
    '''Reset the test suite by resetting the underlying database and deleting the '.sessions' folder
    '''
    try:
        yield
    finally:
        try:
            shutil.rmtree(TestConfig.SESSION_DATA_DIR)
        except Exception:
            pass


@pytest.fixture(scope='session', autouse=True)
def app_context():
    app = create_app(config_class=TestConfig)
    with app.app_context():
        yield


@pytest.fixture(autouse=True)
@test_utils.reset_database(tear='up')
def reset_database():
    '''Reset the database before any test is run
    '''
    yield


@pytest.fixture
def frontend_app():
    app = create_app(config_class=TestConfig)
    frontend = app.test_client(use_cookies=True)
    return frontend
