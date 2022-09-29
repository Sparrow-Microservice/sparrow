#!/bin/sh

# Entrypoint for api server
exec /production/{{cookiecutter.project_name}}/persistent/virtualenv/bin/gevent-wsgi {{cookiecutter.project_name_snake}}.server:app
