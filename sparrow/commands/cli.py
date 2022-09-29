import os
import click
import logging

logging.basicConfig(level=logging.INFO)


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from sparrow.utils.os_utils import read_version
    click.echo(read_version())
    ctx.exit()


@click.group()
@click.option('--version',
              is_flag=True,
              callback=print_version,
              expose_value=False,
              is_eager=True,
              help="show the version")
def wish_flask():
    """ sparrow command client

    Github: https://github.com/ContextLogic/wish_flask
    """


@wish_flask.command(help='Create a start-up project.')
@click.argument('project_name', type=str, required=True)
@click.option('--template', type=str, default='seed', help='template name', show_default=True)
@click.option('--port', type=str, default='8888', help='port to listen', show_default=True)
@click.option('--namespace', type=str, show_default=True, default='wishpost',
              prompt="kubernetes namespace to deploy, e.g. wishpost")
@click.option('--project_version', type=str, default='0.0.1', show_default=True,
              prompt="version of new project, e.g. 0.0.1")
def create(project_name, template, port, namespace, project_version):
    from cookiecutter.main import cookiecutter
    from sparrow.template import __file__ as template_file
    from sparrow.utils.os_utils import read_version
    from sparrow.utils.convert_utils import to_snake_case
    template_dir = os.path.dirname(template_file)
    template_path = os.path.join(template_dir, template)
    project_name = project_name.rstrip('/')
    project_dir = os.path.dirname(project_name)
    project_name = os.path.basename(project_name)
    if not project_dir:
        project_dir = '.'
    project_name_snake = to_snake_case(project_name).replace('-', '_')
    project_name_hyphen = project_name_snake.replace('_', '-')
    real_project_name = '%s/%s' % (project_dir, project_name)
    logging.info('Creating project %s ...', real_project_name)
    cookiecutter(
        template_path,
        no_input=True,
        output_dir=project_dir,
        extra_context={
            'project_name': project_name,
            'project_name_snake': project_name_snake,
            'project_name_hyphen': project_name_hyphen,
            'port': port,
            'namespace': namespace,
            'project_version': project_version,
            'version': read_version()
        }
    )
    logging.info('Finish creating project %s!', real_project_name)


@wish_flask.command()
@click.argument('server', type=str, required=True)
@click.option('--bind', type=str, help='The host to bind. e.g. :8080')
@click.option('--timeout', type=int, help="Stop timeout", default=30, show_default=True)
@click.option('--timeout_read', type=int, help="Stop timeout for reading request", default=2, show_default=True)
@click.option('--pool_size', type=int, help="Pool size for greenlets", default=10000, show_default=True)
@click.option('--auto_reload', type=bool, help="Auto reload if py files are changed", default=False, show_default=True)
def gstart(server, bind, timeout, timeout_read, pool_size, auto_reload):
    """Start the server by gevent-wsgi.

    SERVER format: <module>:<app_name>, e.g. examples.example_server:app
    """
    from sparrow.entry.gevent_wsgi import ServerRunner
    ServerRunner(
        server,
        bind=bind,
        stop_timeout=timeout,
        stop_timeout_for_read=timeout_read,
        pool_size=pool_size,
        auto_reload=auto_reload
    ).start_server()


@wish_flask.command()
@click.argument('action', type=click.Choice(['create', 'update', 'compile']), required=True)
@click.option('--scan', type=str, default='.', help='[create, update] The directory to scan',
              show_default=True)
@click.option('--language', type=str, help='[create] Used for creating a language.')
@click.option('--translations', type=str, default='translations',
              help='[create, update, compile] The translations directory',
              show_default=True)
@click.option('--config', type=str, help='[create, update] The babel config file')
def i18n(action, scan, language, translations, config):
    """i18n command for multiple languages.
    """
    from sparrow.i18n.tool import create_translations, update_translations, compile_translations
    if action == 'create':
        assert language, '--language is for specified'
        return create_translations(scan, translations, language, config_file=config)
    elif action == 'update':
        return update_translations(scan, translations, config_file=config)
    elif action == 'compile':
        return compile_translations(translations)


@wish_flask.command()
@click.argument('api_file', type=str, required=True)
@click.argument('package_dir', type=str, required=True)
@click.option('--package_name', type=str,
              help='The client package name. '
                   'So "import <package_name>" after pip install. '
                   'Default to use <package_dir>.'
              )
@click.option('--project_name', type=str,
              help='The client pip project name. '
                   'So "pip install <project_name>==<package_version>". '
                   'Default to use <package_name>.'
              )
@click.option('--package_version', type=str,
              help='The client pip package version. '
                   'So "pip install <project_name>==<package_version>". '
                   'Default to use the version of api: <info.version> in the generated schema.')
@click.option('--git_repo', type=str,
              help='The github repo name. '
                   'Default to use <project_name>. ')
@click.option('--git_owner', type=str, default='ContextLogic',
              help='The owner of this github repo.', show_default=True)
@click.option('--client_type',
              type=click.Choice(['WISHFLASK', 'WISHPOST', 'WISHWMS', 'FLASK', 'TORNADO']),
              default='WISHFLASK', show_default=True,
              help='The client type to generate.')
@click.option('--remove_first', type=bool, default='True', show_default=True,
              help='Remove the generated package before generating.')
def micro_client(api_file, package_dir, package_name,
                 project_name, package_version,
                 git_repo, git_owner, client_type, remove_first):
    """Generate python client from openapi schema file.

    API_FILE: Path of openapi spec file

    PACKAGE_DIR: Directory of generated package
    """
    import os
    package_name = package_name or os.path.basename(package_dir.strip(' /')).replace('-', '_')
    project_name = project_name or package_name.replace('_', '-')
    git_repo = git_repo or project_name

    from sparrow.codegen.openapi import OASGen
    OASGen.generate_client_package(
        yaml_file=api_file,
        client_dir=package_dir,
        package_name=package_name,
        package_version=package_version,
        project_name=project_name,
        git_repo=git_repo,
        git_owner=git_owner,
        client_type=client_type,
        remove_first=remove_first
    )


@wish_flask.command(help='Start a framework portal')
def framework_portal():
    # 2. start a container by a docker-compose file
    from sparrow.framework_portal.command import up
    up()


try:
    from flask_migrate.cli import db
except:
    db = None

if db:
    wish_flask.add_command(db)


def cli():
    wish_flask()


if __name__ == '__main__':
    cli()
