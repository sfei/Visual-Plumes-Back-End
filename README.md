# Visual Plumes Backend - Django Web Server

## Code Repositories for Visual Plumes:

- https://github.com/sfei/Visual-Plumes-Back-End
- https://github.com/sfei/Visual-Plumes-Front-End
- https://github.com/sfei/Visual-Plumes-Models

## Introduction

The Visual Plumes backend runs on a Django web server and is designed to facilitate data exchange between the front-end UI and the model library.

It consists of the following endpoints:

- run_analysis - Accepts POST data consisting of stringified JSON and CSV data for time series files then initiates objects and data structures for feeding into the UM3 model library.
- download_zip_archive - Accepts a model run id (python timestamp generated during computation) and forwards the associated zip archive. Zip archives are generated as part of the model run process.

Visual Plumes We Server has been run and tested against:

- Python v3.10.12
- Django v4.2.4

Visual Plumes does not use a database, you can ignore database related configurations.

## Install Dependencies

Using pip, or pip3 depending on the server's Python environment, install Python dependencies:

```
pip install -r /path/to/requirements.txt
```

While dependencies can be installed at the system level consider using a [virtual environment](#Python-Virtual-Environment).

## Update visualplumes/settings.py

Regardless of running in Development or Production mode you'll need to copy `visualplumes/settings-template.py` to `visualplumes/settings.py` and make the following adjustments:

### Add a new secret key

Generate a new secret key using the terminal:

```
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Replace the text in brackets in the following line:

```
SECRET_KEY = 'django-insecure-[insert secret key]'
```

### Update ALLOWED_HOSTS

Add URLs for allowed server host names, e.g. visualplumes.sfei.org:

```
ALLOWED_HOSTS = ['']
```

### Add URLs to CORS_ALLOWED_ORIGINS

Add port and URL information to CORS_ALLOWED_ORIGINS

```
CORS_ALLOWED_ORIGINS = [
    "http://localhost:[port]",
    "http://[custom url]:[port]"
]
```

### Update CSRF_TRUSTED_ORIGINS

Update post and URL information for CSRF_TRUSTED_ORIGINS:

```
CSRF_TRUSTED_ORIGINS = ['http://localhost:[port]','http://[custom url]:[port]']
```

## Running in Development Mode

### Start the Visual Plumes Server

Django development mode can be run by issuing the following command within the root directory, containing the file manage.py:
`python3 manage.py runserver 0.0.0.0:3000`

Or more generally:
`python3 manage.py runserver 0.0.0.0:[port]`

This will start a server process on the localhost listening on port 3000 or whatever desired port. Assuming there are no blocks on your network, the server should be accessible either locally or another computer.

## Running Production

The best resource for configuring Django to run in production mode is the Django documentation, we've also included some helpful tips in the sections below.

### Django Documentation

The best resource for running django in production is the [official Django 4.2 documentation](https://docs.djangoproject.com/en/4.2/howto/deployment/). The deployment documentation contains instructions for deploying on various platforms as well as settings information.

### Deployment Checklist

Use Django's deployment checklist to ensure proper settings have been configured in settings.py:
`python3 manage.py check --deploy`

### Python Virtual Environment

While not a requirement, python virtual environments allow django applications to run independent of the locally installed python environment. See [Python's virtual environment instructions](https://docs.python.org/3/library/venv.html) for creating and activating virtual environments. Consider installing Django dependencies within a virtual environment.

### Example Apache Config Script

The following is an example virtual host directive if configuring to run using Apache with the wsgi mod enabled and over https (SSL). Block brackets denote custom values to be added by the user / system administrator. The "443" virtual host configures sites running over https (SSL).

```
<VirtualHost *:443>
  ServerName [server url]
  ServerAdmin [email]

  DocumentRoot [/path/to/project/directory]

  SSLEngine on
  SSLCertificateFile      "[/path/to/ssl/files]/server.crt"
  SSLCertificateKeyFile   "[/path/to/ssl/files]/server.key"
  SSLCertificateChainFile "[/path/to/ssl/files]/ca-bundle.crt"

  ErrorLog [/path/to/apache2/website/logs]/error.log
  CustomLog [/path/to/apache2/website/logs]/access.log combined

  WSGIDaemonProcess [process group] python-path=[/path/to/webserver/directory]:[/path/to/virtual/environment]/lib/python3.10/site-packages
  WSGIProcessGroup [process group]
  WSGIScriptAlias / [/path/to/webserver/directory]/visualplumes/wsgi.py process-group=[process group]

</VirtualHost>

```
