import atexit
import os
from dynaconf import FlaskDynaconf

from sparrow_flask.base import Sparrow
from sparrow_flask.config import server_config
# from wish_flask_resource_manager.resource_extension import ResourceManagerExtension
from flask_smorest import Api


def get_setting_files(config_dir, config_files, buildin_files=None):
    config_files = config_files or []
    config_files = [
        os.path.join(config_dir, f) if not os.path.isabs(f) else f for f in config_files
    ]
    return (buildin_files or []) + config_files


def create_app(
        name,
        application_clz=Sparrow,
        config_dir='config',
        config_files=None,
        **app_kwargs):
    """Create application instance and parse configs

    :param application_clz: WishFlaskApplication or its subclass
    :param config_dir: the dir to find setting files
        default is app.root_path/config
    :param config_files: list of the setting files in config_dir
        default is ['settings.yaml', '.secrets.yaml']
    :param app_kwargs: kwargs to be passed to application_clz
    :return: app instance
    """

    if not issubclass(application_clz, Sparrow):
        raise ValueError('%s is not subclass of %s', application_clz.__name__, Sparrow.__name__)
    app = application_clz(name, **app_kwargs)

    if not config_dir.startswith('/'):
        config_dir = os.path.join(app.root_path, config_dir)
    config_files = config_files or ['settings.yaml', '.secrets.yaml']

    setting_files = get_setting_files(config_dir, config_files,
                                      buildin_files=server_config)
    FlaskDynaconf(app, settings_files=setting_files)
    # Add wish resource manager to app
    # https://github.com/ContextLogic/wish-flask-resource-manager
    # ResourceManagerExtension(app)
    atexit.register(app.close)
    return app


def create_api(app):
    return Api(app)
