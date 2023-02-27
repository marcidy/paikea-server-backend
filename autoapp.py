import os
from dotenv import load_dotenv
load_dotenv(os.environ['PAIKEA_DOTENV'])

import datetime
import time
import logging
from rfc3339 import rfc3339
from logging.handlers import TimedRotatingFileHandler
from flask import (
    Flask,
    current_app,
    request,
    g
)
import paikea.views as views
from paikea.extensions import db, migrate, ma
from paikea.settings import Config, ProdConfig


def start_timer():
    g.start = time.time()


def log_request(response):
    if request.path == '/favicon.ico':
        return response
    elif request.path.startswith('/static'):
        return response

    now = time.time()
    duration = round(now - g.start, 2)
    dt = datetime.datetime.fromtimestamp(now)
    timestamp = rfc3339(dt, utc=True)

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    host = request.host.split(':', 1)[0]
    args = dict(request.args)

    form_data = request.form.to_dict(flat=False)

    log_params = [
        ('method', request.method, 'blue'),
        ('path', request.path, 'blue'),
        ('status', response.status_code, 'yellow'),
        ('duration', duration, 'green'),
        ('time', timestamp, 'magenta'),
        ('ip', ip, 'red'),
        ('host', host, 'red'),
        ('params', args, 'blue'),
        ('data', request.data, 'red'),
        ('json', form_data, 'purple'),
    ]

    request_id = request.headers.get('X-Request-ID')
    if request_id:
        log_params.append(('request_id', request_id, 'yellow'))

    parts = []
    for name, value, color in log_params:
        # part = colors.color("{}={}".format(name, value), fg=color)
        part = "{}={}".format(name, value)
        parts.append(part)
    line = " | ".join(parts)

    current_app.logger.info(line)

    return response


def create_app():
    app = Flask(__name__.split('.')[0], static_url_path='/static')
    app.url_map.strict_slashes = False
    if os.environ['PAIKEA_ENV'] == 'PROD':
        app.config.from_object(ProdConfig)
    else:
        app.config.from_object(Config)

    for bp in views.blueprints:
        app.register_blueprint(bp)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    ma.init_app(app)

    handler = TimedRotatingFileHandler(filename=Config.LOG_FILE,
                                       when="W6", interval=1,
                                       backupCount=52, encoding=None,
                                       delay=False, utc=True, atTime=None)

    formatter = logging.Formatter(Config.LOG_FORMAT)

    handler.setLevel(Config.LOG_LEVEL)
    handler.setFormatter(formatter)

    app.before_request(start_timer)
    app.after_request(log_request)
    app.logger.addHandler(handler)
    app.logger.setLevel(Config.LOG_LEVEL)
    app.logger.info("App initialized")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=8888)
