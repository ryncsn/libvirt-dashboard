import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DEBUG = False
    TESTING = False

    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    POLARION_ENABLED = False
    POLARION_URL = 'https://localhost/'
    POLARION_PROJECT = 'TEST-PROJECT'
    POLARION_USER = 'TEST-USER'
    POLARION_PASSWORD = 'TEST-PASSWORD'
    POLARION_PLANS = {
        "PRODUCT-VERSION": "QUERY",
    }

    CELERY_BROKER = 'amqp://guest:guest@localhost:5672//'
    CELERY_RESULT_BACKEND = 'db+sqlite:////tmp/test.db'
    CELERY_IGNORE_RESULT = False


class ProductionConfig(Config):
    pass


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


ActiveConfig = DevelopmentConfig

try:
    from .config import ActiveConfig
except ImportError:
    print("Instance setting not found.")
