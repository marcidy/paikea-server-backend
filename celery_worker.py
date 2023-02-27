#!/usr/bin/env python
# docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# PAIKEA_DOTENV=.env celery -A celery_worker.celery worker
import os
from autoapp import create_app
from paikea.extensions import make_celery


app = create_app()
app.app_context().push()
celery = make_celery(app)
