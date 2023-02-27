import os
import logging


class Config:
    APP_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    CACHE_TYPE = 'simple'
    JWT_AUTH_USERNAME_KEY = 'email'
    JWT_AUTH_HEADEWRS_PREFIX = 'Token'
    CORS_ORIGIN_WHITELIST = []
    JWT_HEADER_TYPE = 'Token'
    LOG_FILE = 'logs/logs.log'
    LOG_FORMAT = "%(asctime)s | %(pathname)s:%(lineno)d |" \
        "%(funcName)s | %(levelname)s | %(message)s "
    CSRF_ENABLED = True
    LOG_LEVEL = logging.INFO
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///database/database.sql"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CELERY_BROKER_URL = 'amqp://localhost:5672/'
    FIRMWARE_BASE = os.path.join(PROJECT_ROOT, "../firmware")
    FIRMWARE_REPO = ""


class TestConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('PAIKEA_DB_URI')
    FIRMWARE_REPO = os.environ.get('PAIKEA_FIRMWARE_REPO')
    FIRMWARE_BASE = os.environ.get('PAIKEA_FIRMWARE_BASE')
