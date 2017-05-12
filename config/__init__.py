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
    POLARION_PLAN_QUERY = {}
    POLARION_PLANS = {}
    POLARION_DEFAULT_PLANNED_IN = None

    CELERY_BROKER = 'amqp://guest:guest@localhost:5672//'
    CELERY_RESULT_BACKEND = 'db+sqlite:////tmp/test.db'
    CELERY_IGNORE_RESULT = False

    BUS_HOST = "127.0.0.1"
    BUS_PORT = 61613
    BUS_USER = ""
    BUS_PASSWORD = ""
    BUS_TIMEOUT = 60
    BUS_DISTINATION = ''

    JOB_TRIGGER_URL = 'http://exapmle.com/job-trigger'
    JOB_NAMES_URL = 'htpp://example.com/get-job-names'


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
