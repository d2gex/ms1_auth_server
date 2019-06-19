import json
import pytest
import jwt

from os.path import join
from jwcrypto import jwk, jwt as jwtc
from authorization_server import utils, config, errors
from tests import utils as test_utils
from unittest.mock import patch


def test_config_mixin():
    '''Check that ConfigMixin works as follows:

    1) if not a real RSA private key is loaded => throw an exception
    2) Otherwise a JWK object is created so .load_private works as expected
    3) .init() fetch private key, public key and creates jwk_set as expected
    '''

    try:

        assert config.ConfigMixin.private_key is not None
        assert config.ConfigMixin.public_key is not None
        assert config.ConfigMixin.jwk_set is not None

        # --> Ensure ConfigMixin's parent class attributes are set to None
        config.ConfigMixin.private_key = None
        config.ConfigMixin.public_key = None
        jwk_set = config.ConfigMixin.jwk_set
        config.ConfigMixin.jwk_set = None

        # --> However Config subclass's copied attributes should remain intact
        assert config.Config.JWT_PRIVATE_KEY
        assert config.Config.JWT_PUBLIC_KEY
        assert config.Config.jwk_set is None
        assert jwk_set

        # (1)
        with pytest.raises(errors.ConfigError):
            config.ConfigMixin.load_private_key(join(test_utils.TEST_PATH, 'keys', 'rs256.pub'))

        # (2)
        key_wallet = config.ConfigMixin.load_private_key(join(test_utils.TEST_PATH, 'keys', 'rs256.pem'))
        assert isinstance(key_wallet, jwk.JWK)

        # (3)
        with patch.object(config.os, 'getenv', return_value=join(test_utils.TEST_PATH, 'keys', 'rs256.pem')) as mock_e:
            assert 'rs256.pem' in mock_e()  # ensure the right private key is read
            config.ConfigMixin.init()

        assert config.Config.JWT_PRIVATE_KEY == config.ConfigMixin.private_key
        assert config.Config.JWT_PUBLIC_KEY == config.ConfigMixin.public_key
        assert config.Config.jwk_set.export(private_keys=False) == jwk_set.export(private_keys=False)

    finally:
        # Let's ensure whatever happens ConfigMixin remains untouched given that tests are run sequentially
        config.ConfigMixin = utils.init_class(config.ConfigMixin)


def test_publickey_decryption():
    '''This test aims to ensure that no bugs have been introduced when using JWK via jwcrypto. This means that
    any encrypted token with jwk.private_key should be able to be decrypted with jwk.public_key
    '''

    payload = {'user_id': 123}
    encrypted_token = jwt.encode(payload, config.Config.JWT_PRIVATE_KEY, algorithm='RS256').decode('utf-8')
    assert payload == jwt.decode(encrypted_token, config.Config.JWT_PUBLIC_KEY, algorithms=['RS256'])


def test_public_key_reconstruction():
    '''This test aims to ensure that a public key can be reconstructed and use properly from its RFC 7517 representation
    as follows:

    1) Reconstruction method 1 and usage: Fetch public key from Config.JWKS, convert it to PEM and use it to
    decrypt token.
    2) Reconstruction method 2 and usage: Create a jwcrypto token using the signed token and jwkSet containing the
    public key and compare payloads.
    '''

    # (1)
    # ---> Get the public key as a Python dictionary
    all_pub_keys_dict = json.loads(config.Config.JWKS.export(private_keys=False))
    pub_key_dict = all_pub_keys_dict['keys'][0]
    print(pub_key_dict['kid'])
    assert all(keyword in pub_key_dict for keyword in ('kid', 'n'))

    # Sign token adding in the header what public key will be required to decrypt it
    payload = {'user_id': 123}
    signed_token = jwt.encode(payload,
                              config.Config.JWT_PRIVATE_KEY,
                              headers={'kid': pub_key_dict['kid']},
                              algorithm='RS256').decode('utf-8')

    # Convert dict-like public key to JWK object and get the public key as a string
    jwk_obj = jwk.JWK(**pub_key_dict)
    public_key = jwk_obj.export_to_pem().decode()
    assert public_key == config.Config.public_key

    # The decryption from both Config.JWT_PUBLIC_KEY and new restored public key should be the same
    assert payload == jwt.decode(signed_token, config.Config.JWT_PUBLIC_KEY, algorithms=['RS256'])
    assert payload == jwt.decode(signed_token, public_key, algorithms=['RS256'])

    # (2)
    jw_token = jwtc.JWT(key=config.Config.JWKS, jwt=signed_token)
    assert json.loads(jw_token.claims) == payload
