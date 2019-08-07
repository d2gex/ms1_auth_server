import json
import pytest

from os.path import join
from jwcrypto import jwt, jwk
from authorization_server import utils, config, errors
from tests import utils as test_utils
from unittest.mock import patch


@pytest.fixture
def reset_database():
    pass


def test_config_mixin():
    '''Check that ConfigMixin works as follows:

    1) if not a real RSA private key is loaded => throw an exception
    2) Otherwise a JWK object is created so .load_private works as expected
    3) .init() fetch private key as pem and generate public key as pem, creates both public_jwk and private_jwk as JWK
    4) Ensure 'alg' key is in bont public and private JWK
    '''

    try:

        assert config.ConfigMixin.private_key is not None
        assert config.ConfigMixin.public_key is not None
        assert config.ConfigMixin.public_jwk is not None

        # --> Ensure ConfigMixin's parent class attributes are set to None however subclass' attribures are intact
        config.ConfigMixin.private_key = None
        assert config.Config.JWT_PRIVATE_KEY

        config.ConfigMixin.public_key = None
        assert config.Config.JWT_PUBLIC_KEY

        public_jwk = config.ConfigMixin.public_jwk
        config.ConfigMixin.public_jwk = None
        assert config.Config.public_jwk is None
        assert public_jwk

        private_jwk = config.ConfigMixin.private_jwk
        config.ConfigMixin.private_jwk = None
        assert config.ConfigMixin.private_jwk is None
        assert private_jwk

        # (1)
        with pytest.raises(errors.ConfigError):
            config.ConfigMixin.load_private_key(join(test_utils.TEST_PATH, 'keys', 'rs256.pub'))

        # (2)
        jwk_obj = config.ConfigMixin.load_private_key(join(test_utils.TEST_PATH, 'keys', 'rs256.pem'))
        assert isinstance(jwk_obj, jwk.JWK)

        # (3)
        with patch.object(config.os, 'getenv', return_value=join(test_utils.TEST_PATH, 'keys', 'rs256.pem')) as mock_e:
            assert 'rs256.pem' in mock_e()  # ensure the right private key is read
            config.ConfigMixin.init()

        assert config.Config.JWT_PRIVATE_KEY == config.ConfigMixin.private_key
        assert config.Config.JWT_PUBLIC_KEY == config.ConfigMixin.public_key
        assert config.Config.public_jwk == public_jwk
        assert config.Config.private_jwk == private_jwk

        # (4)
        assert 'alg' in json.loads(config.Config.JWK_PUBLIC)
        assert 'alg' in json.loads(config.Config.JWK_PRIVATE)

    finally:
        # Let's ensure whatever happens ConfigMixin remains untouched given that tests are run sequentially
        config.ConfigMixin = utils.init_class(config.ConfigMixin)


def test_public_key_verification():
    '''Ensure that anything that was signed with the private key can be verify by the public key
    '''

    payload = {'user_id': 123}
    # Generated signed jwt token
    jwt_obj = jwt.JWT(header={"alg": "RS256"}, claims={'user_id': 123})
    jwt_obj.make_signed_token(jwk.JWK.from_json(config.Config.JWK_PRIVATE))
    signed_jwt_token = jwt_obj.serialize()

    # Deconstruct the signed jwt token by decrypting it with the public key
    deconstructed_jwt_token = jwt.JWT(key=jwk.JWK.from_json(config.Config.JWK_PUBLIC), jwt=signed_jwt_token)
    assert json.loads(deconstructed_jwt_token.claims) == payload
