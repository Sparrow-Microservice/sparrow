from dynaconf import FlaskDynaconf

# from sparrow.base_app import BaseSparrow
from sparrow.config import get_builtin_config
from sparrow.application.wish_application import WishFlaskApplication


def get_setting_files(config_files):
    config_files = config_files or []
    return get_builtin_config() + config_files


def create_app(config_files=None, app_class=WishFlaskApplication):
    """
    Create application instance and parse configs
    :param config_files: list of the setting files.
                        default is ['./config/settings.yaml', './config/.secrets.yaml']
    :param app_class: BaseSparrow or its subclass
    :return: app instance
    """
    app = app_class(__name__)

    setting_files = get_setting_files(config_files)

    # Use dynaconf to load configs
    # https://dynaconf.readthedocs.io/en/latest/guides/flask.html
    # todo: 这里引入了一个新的库，dynaconf，用来管理配置文件，不知道这样写好不好
    FlaskDynaconf(app, settings_files=setting_files)

    return app
