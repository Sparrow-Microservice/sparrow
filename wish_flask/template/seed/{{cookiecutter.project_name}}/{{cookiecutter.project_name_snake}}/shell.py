from wish_flask.shell import ipshell, VariableCollector
from {{cookiecutter.project_name_snake}}.server import app
try:
    from flask_mongoengine import Document
except:
    Document = object


ipshell(
    app,
    var_collectors=[
        VariableCollector(
            '{{cookiecutter.project_name_snake}}.models',
            class_types=[Document],
            collect_subclasss=True
        )
    ]
)

# Try running this script by:
#    >> FLASK_ENV=dev python {{cookiecutter.project_name_snake}}/shell.py
