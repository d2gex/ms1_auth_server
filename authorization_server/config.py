import os
from pathlib import Path
from dotenv import load_dotenv
from os.path import join

path = Path(__file__).resolve()
ROOT_PATH = str(path.parents[1])
dot_env = load_dotenv(join(ROOT_PATH, '.env'))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = f"mysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@" \
                              f"{os.getenv('DB_HOST')}/{os.getenv('DB')}"


class TestingConfig(Config):
    # Needed for form's unit test validation
    WTF_CSRF_ENABLED = False
