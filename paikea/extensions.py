"""
Instanciations of Flask extensions
"""
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from celery import Celery


convention = {
  "ix": 'ix_%(column_0_label)s',
  "uq": "uq_%(table_name)s_%(column_0_name)s",
  "ck": "ck_%(table_name)s_%(column_0_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}

db = SQLAlchemy()
db.metadata.naming_convention = convention
migrate = Migrate(compare_type=True)

ma = Marshmallow()


def make_celery(app):
    """ Create a celery instance from the app"""
    celery = Celery('paikea.tasks',
                    include=['paikea.tasks'])
    celery.config_from_object('celeryconfig')

    class ContextTask(celery.Task):
        """ Use an app context to run celery tasks that require app access.

            :return: celery instance
        """
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
