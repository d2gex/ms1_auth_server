import os
import json

from pathlib import Path
from dotenv import load_dotenv
from jwcrypto import jwk
from os.path import join
from authorization_server import utils, errors

path = Path(__file__).resolve()
ROOT_PATH = str(path.parents[1])
dot_env = load_dotenv(join(ROOT_PATH, '.env'))


@utils.init_class
class ConfigMixin:

    private_key = None  # private key as PEM
    public_key = None  # public key as PEM
    jwk_set = None  # public key as as JWKSet

    @classmethod
    def load_private_key(cls, filename):
        with open(filename, 'rb') as fh:
            jws_obj = jwk.JWK.from_pem(fh.read())
        if not jws_obj.has_private:
            raise errors.ConfigError(f"The filename '{filename}' does not contain a private key")
        return jws_obj

    @classmethod
    def init(cls):
        jwk_obj = cls.load_private_key(os.getenv('JWT_RSA_PRIVATE_PATH'))
        cls.private_key = jwk_obj.export_to_pem(private_key=True, password=None).decode()

        # Very important! To avoid accidents, ensure jwk_set is a JWKSet data structure with only public keys!!!!!
        pub_key_dict = json.loads(jwk_obj.export_public())
        cls.jwk_set = jwk.JWKSet.from_json(json.dumps({'keys': [pub_key_dict]}))

        cls.public_key = jwk_obj.export_to_pem().decode()


class Config(ConfigMixin):
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = f"mysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@" \
                              f"{os.getenv('DB_HOST')}/{os.getenv('DB')}"

    JWT_PRIVATE_KEY = ConfigMixin.private_key
    JWT_PUBLIC_KEY = ConfigMixin.public_key
    JWKS = ConfigMixin.jwk_set


class TestingConfig(Config):
    # Needed for form's unit test validation
    WTF_CSRF_ENABLED = False
