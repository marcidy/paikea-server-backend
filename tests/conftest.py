import os
import tempfile
import pytest
from flask import Flask
from paikea import views
from paikea.extensions import db
from paikea.settings import TestConfig
from endpoint_fixtures import create_endpoints, with_messages
from message_fixtures import rockblock_messages
from api_fixtures import create_modems, create_queues, create_routes
import celery
from celery import Celery


@pytest.fixture(scope='session')
def client():
    app = Flask(__name__.split(".")[0], static_url_path='/static')

    config = TestConfig()
    app.url_map.strict_slashes = False

    db_fd, db_filename = tempfile.mkstemp()
    config.SQLALCHEMY_DATABASE_URI = f"sqlite:////{db_filename}"

    app.config.from_object(config)
    for bp in views.blueprints:
        app.register_blueprint(bp)

    with app.test_client() as client:
        with app.app_context():
            db.init_app(app)
            db.create_all()
        yield client

    os.close(db_fd)
    os.unlink(db_filename)


@pytest.fixture(scope='function')
def flask_app():
    app = Flask(__name__.split(".")[0], static_url_path='/static')

    config = TestConfig()
    config.TESTING = True
    app.url_map.strict_slashes = False

    db_fd, db_filename = tempfile.mkstemp()
    config.SQLALCHEMY_DATABASE_URI = f"sqlite:////{db_filename}"

    app.config.from_object(config)
    for bp in views.blueprints:
        app.register_blueprint(bp)

    with app.app_context():
        db.init_app(app)
        db.create_all()

    ctx = app.test_request_context()
    ctx.push()

    yield app

    ctx.pop()
    os.close(db_fd)
    os.unlink(db_filename)


@pytest.fixture(scope='function')
def database(flask_app):

    db.app = flask_app
    with flask_app.app_context():
        db.init_app(flask_app)
        db.create_all()
        yield db


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'amqp://',
        'result_backend': 'rpc://',
    }


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'paikea.tasks',
    ]


@pytest.fixture(scope='session')
def flask_celery_app():
    app = Flask(__name__.split(".")[0], static_url_path='/static')

    config = TestConfig()
    config.TESTING = True
    app.url_map.strict_slashes = False

    db_fd, db_filename = tempfile.mkstemp()
    config.SQLALCHEMY_DATABASE_URI = f"sqlite:////{db_filename}"

    app.config.from_object(config)
    for bp in views.blueprints:
        app.register_blueprint(bp)

    with app.app_context():
        db.init_app(app)
        db.create_all()

    ctx = app.test_request_context()
    ctx.push()

    yield app

    ctx.pop()
    os.close(db_fd)
    os.unlink(db_filename)


@pytest.fixture(scope='session')
def celery_parameters(flask_celery_app):

    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with flask_celery_app.app_context():
                return self.run(*args, **kwargs)

    return {'task_cls': ContextTask}
