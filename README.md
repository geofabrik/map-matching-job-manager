# Job Management for Map Matching – API and Frontend

This repository contains a basic job management API (including a frontend) for the map matching API
of the of the [railway routing](https://github.com/geofabrik/railway_routing) project by Geofabrik.
Basic means that it does not have any authentication or rate limiting. Everyone who can access the
API can do anything.

## Setup

### Dependencies

```sh
apt install python3 apache2 libapache2-mod-wsgi-py3 python3-urllib3 python3-requests \
  python3-psycopg2 python3-pyshp postgresql python3-jinja2 python3-markdown
```

### Railway Routing

Build and install the railway routing enginge, import data, start it. This step is explanated in its
own repository. The configuration listed below, assumes that the railway routing API listens on port
8989.

### PostgreSQL
Create a PostgreSQL database, create the necessary table and grant the necessary permissions to user
running the web application and the worker process. The PostgreSQL user has to be created if it does
not exist:

```sh
# Choose the name of the user your web application runs as, this is most likely the user who runs
# the Apache processes.
sudo -u postgres createuser www-data
sudo -u postgres createdb -E utf-8 jobs
```

Log into the database using `sudo -u postgres psql -d jobs` and run following commands:

```sql
CREATE TABLE jobs (
  id serial primary key,
  name text,
  status text,
  input_file text,
  query_params text,
  created_at timestamp without time zone,
  started_at timestamp without time zone,
  finished_at timestamp without time zone,
  download_path text
);
GRANT ALL ON jobs TO "www-data";
```

### Checking out the source code, write a configuration file, create directories and system user accounts

* Clone this repository, e.g. to `/srv/job-manager/`.
* Install Apache and mod_wsgi. Ensure that you use the Python3 version of mod_wsgi.
* Create a user account for the work processing daemon:

```sh
createuser --disabled-password --group robot
```

* Create directories to store input files and output files, e.g. `/var/job-manager/input` and
  `/var/www/jobs/output`. These directories must be writeable for the users which runs the Python
  web application (input directory) and the worker process (output directory):

```sh
mkdir -p /var/job-manager/input/
chown www-data:robot /var/job-manager/input/
chmod 775 /var/job-manager/input/
mkdir -p /var/www/jobs/output
chown robot /var/www/jobs/output/
chmod 755 /var/www/jobs/output/
```

* Create a configuration file called `config.json` by using the sample configuration
  `config-sample.json`. It has to be place in the top level directory of this repository.

### Build frontend

Run `make` to build the frontend and API documentation. Resulting files will be located at
`frontend/`

If you want to beautify the frontend with your logo, place it at `frontend/img/logo.png`.

### Apache

Configure an Apache virtual host (see below):

```Apache
<VirtualHost *:80>
  # adapt this name
  ServerName apitest.mydomain.tld

  ServerAdmin webmaster@localhost
  DocumentRoot /srv/job-manager/frontend/
  Options FollowSymLinks

  # Files which should be served without authentication because they are needed for the landing page,
  # have to be listed before the catch-all WSGIScriptAlias

  LogLevel warn

  ProxyPass /railway_routing/info http://localhost:8989/info
  ProxyPass /railway_routing/match http://localhost:8989/match
  Alias /job-manager/download/ /var/www/jobs/output/

  <Directory /var/www/jobs/output/>
      Require all granted
  </Directory>

  WSGIDaemonProcess with_psycopg2 processes=2 threads=1 python-path=/srv/job-manager/ home=/srv/job-manager/
  WSGIScriptAlias /job    /srv/job-manager/application.py
  WSGIScriptAlias /status /srv/job-manager/application.py
  <Location /job>
      WSGIProcessGroup with_psycopg2
  </Location>
  <Location /status>
      WSGIProcessGroup with_psycopg2
  </Location>
  <Directory /srv/job-manager/ >
      Require all granted
  </Directory>

  <Location />
      Require all granted
  </Location>

  ErrorLog ${APACHE_LOG_DIR}/error.log
  CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

### Worker daemon

Do necessary adaptions to the Systemd unit file of the worker daemon and copy it to the location
where Systemd unit files are located, e.g. `/etc/systemd/system/` on Debian:

```sh
cp job-manager-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl start job-manager-worker
```

### Cleanup cron job

Finished jobs are not deleted from the database and the disk automatically. You have to run a cronjob
to remove old data. That' what [job_cleanup.py](job_cleanup.py) is intended for. Add following entry to
the crontab of user robot (`crontab -e -u robot`) to remove jobs older than 48 hours:

```crontab
# m h dom mon dow user  command
15 2    * * *   robot   /usr/bin/python3 /srv/job-manager/job_cleanup.py -c /srv/job-manager/config.json -m 48
```

## License

© 2018 Geofabrik GmbH

This work is licensed under the terms of [Apache License v2.0](LICENSE.txt)

Work of following third parties is included in this repository:

| name    | license   | source code repository | location in this repository |
|---------|-----------|------------------------|-----------------------------|
| [Datatables](https://www.datatables.net/) | MIT | at [GitHub](https://github.com/DataTables/DataTablesSrc) | [frontend/datatables](frontend/datatables) |
