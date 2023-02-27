=======
# Introduction
The back-end processes API requests and warehouses information in a database as specified in autoapp.py.

# Requiremnets
The backend uses celery to fire off background tasks to ensure a 200ms OK response to the RockBlock API requests.  A broker is required.  RabbitMQ is tested and works "out of the box".  This can be tested using a rabbitmq docker container:

```bash
$ docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

See the paikea/settings.py for the `CELERY_BROKER_URL` if it requires changing.

# Configuration
```Bash
$ python3 -m venv venv
$ source venv/bin/activate
```

# Installation
```Bash
$ pip install -r requirements.txt
```

# Required Environment Variables

The backend uses a dot env file to store critical environment variables like credentials, credential dependent strings, and deployment customizations.  The application uses the `python-dotenv` package to read the file specified in the `PAIKEA_DOTENV` system environment variable to load these when the application starts.

| Varaible | Description | Example |
|:--------:|-------------|:-------:|
| PAIKEA_DOTENV | Path to a the dot env file to load | .env |

This environmnt variable must be passed to the all the services and the file to which it refers must exist.

## `.env` Contents
The path specified in the PAIKEA_DOTENV environment variable contrains the following:

| Varaible | Description | Example |
|:--------:|-------------|:-------:|
| FLASK_APP |  Flask application to load | ./autoapp |
| PAIKEA_ENV | Selects which settings to load | PROD |
| PAIKEA_DB_PASS | Database password for database URI | "test1234test" |
| PAIKEA_DB_URI | DB connection string | mysql+mysqldb://user:test1234test@localhost/db_name?unix_socket=/var/run/mysqld/mysqld.sock |
| PAIKEA_FIRMWARE_REPO | git repository to pull micropython modules for a firmware update | git@github.com:orgainzation/paikea-firmware.git |
| PAIKEA_FIRMWARE_BASE | directory on backend server to serve as base directory during pulling and serving firmware |  /srv/paikea/firmware |

## API credentials
The backend connects to the RockBlock API and requires credentials.  These must be provided the celery workers specifically for the `send` methods in the models. Pass these in as environment varialbes to the services which run the workers.  There are two distict accounts, one for RockBlock and one for Rock Core. RockCore is no longer used.

| Environment variable | Description | Example |
|:--------------------:|-------------|:-------:|
| ROCKBLOCK_USER       | RockBlock login | user@email.net |
| ROCKBLOCK_PASS       | RockBlock password | p@ssw0rd! |
| ROCKCORE_USER        | Rock Core login | another.user@email.net |
| ROCKCORE_PASS        | Rock Core password | 12345 |

# Services
The backend requires the broker (e.g. RabbitMQ) to be running, the celery workers to be stared, and the backend to be running.  For a user to interact with the devices over the front-end, the device server must be running but this is covered in a seperate repository.

The services are not intended to be directly accessible and require a reverse proxy such as nginx.  Do not expose the services directly to the internet.

# Front-end
The server front end is templated out from the `/templates` directory.  It's mostly driven by the javascript in `static/js/*`.

The front end has a single reference to the websocket server which hosts the devices connections.  In `device.js` change the line
```javascript
    connect () {
        let self = this;
        let ws_addr = '';

        if ( window.location.host.indexOf('localhost') == 0 ) {
            ws_addr = 'ws://localhost:7770/' + this.iam;
        } else {
            ws_addr = 'wss://fqdn:port:7778/' + this.iam;
        }

```
to use the same fully qualified domain name and port which accesses the device server's external page port.  This port should reverse proxy to the internal page port on the device server.

e.g.
```javascript
    connect () {
        let self = this;
        let ws_addr = '';

        if ( window.location.host.indexOf('localhost') == 0 ) {
            ws_addr = 'ws://localhost:7770/' + this.iam;
        } else {
            ws_addr = 'wss://devices.myhost.net:7778/' + this.iam;
        }
```

# Firmware repository configuration
The user executing the services requires read access to the git repository holding the firmware.

## Example service files

### App Backend
```bash
[Unit]
Description=Paikea backend
After=network.target

[Service]
Type=simple
User=paikea
WorkingDirectory=/home/paikea/backend
EnvironmentFile=/home/paikea/vars.env
PassEnvironment=ROCKBLOCK_USER ROCKBLOCK_PASS ROCKCORE_USER ROCKCORE_PASS
Environment="PAIKEA_DOTENV=/home/paikea/backend/.env"
ExecStart=/home/paikea/venv/bin/flask run -h 127.0.0.1 -p 8888
Restart=on-abort

[Install]
WantedBy=multi-user.target

```

In this case, the credential variables are stored in a an enviroment file which is read only by root.  These enviroment variables are passed to the process running the app backend via `PassEnvironment`.  The service file also sets the `PAIKEA_DOTENV` variable.

### Celery workers
In this example, celery workers are launched via `supervisord` using config in `/etc/supervisord/conf.d/celeryd.conf`.

```bash
; ==================================
;  celery worker supervisor
; ==================================

[program:celery]
command=/home/paikea/venv/bin/celery -A celery_worker.celery worker --loglevel=INFO
directory=/home/paikea/backend

environment=ROCKBLOCK_USER="user@email.net",ROCKBLOCK_PASS="p@ssw0rd!",ROCKCORE_USER="another.user@email.net",ROCKCORE_PASS="12345",PAIKEA_DOTENV=/home/paikea/backend/.env,PAIKEA_DB_PASS=test1234test
user=paikea
numprocs=1
stdout_logfile=/home/paikea/backend/logs/celery/worker.log
stderr_logfile=/home/paikea/backend/logs/celery/worker.log
autostart=true
autorestart=true
startsecs=10

; Need to wait for currently executing tasks to finish at shutdown.
; Increase this if you have very long running tasks.
stopwaitsecs = 600

; Causes supervisor to send the termination signal (SIGTERM) to the whole process group.
stopasgroup=true

; Set Celery priority higher than default (999)
; so, if rabbitmq is supervised, it will start first.
priority=1000

```

Note how the credentials as passed directly in this file so each launched worker processes has the environment variables set.  This file is also read-only by root.

## Example NGINX config
```bash
server {
    listen 443 ssl;
    server_name server.hostname.com;
    ssl_certificate /etc/letsencrypt/live/server.hostname.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/server.hostname.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/server.hostname.com/fullchain.pem;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache none;
    ssl_session_timeout 5m;
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_ecdh_curve auto;
    ssl_buffer_size 16k;
    sub_filter 'server_hostname' '$hostname';
    sub_filter 'server_address' '$server_addr:$server_port';
    sub_filter 'server_url' '$request_uri';
    sub_filter 'remote_addr' '$remote_addr:$remote_port';
    sub_filter 'server_data' '$time_local';
    sub_filter 'client_browser' '$http_user_agent';
    sub_filter 'request_id' '$request_id';
    sub_filter 'nginx_version' '$nginx_version';
    sub_filter 'document_root' '$document_root';
    sub_filter 'proxied_for_ip' '$http_x_forwarded_for';
    sub_filter_once off;

    location / {
        proxy_pass http://localhost:8888;


    }

    location /connection/hc {
        add_header Content-Type "text/plain";
        return 200 OK;

    }
    location /docs {
        root   /srv/paikea_docs/_build/html;
        index  index.html;

    }

    access_log  /var/log/nginx/paikea_access.log  main;

}
```
