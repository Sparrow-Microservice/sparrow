#!/bin/sh

# Entrypoint for worker
exec /production/{{cookiecutter.project_name}}/persistent/virtualenv/bin/python /production/{{cookiecutter.project_name}}/current/{{cookiecutter.project_name}}/{{cookiecutter.project_name_snake}}/worker.py