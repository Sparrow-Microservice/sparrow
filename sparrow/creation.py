import atexit
import os
from dynaconf import FlaskDynaconf

from sparrow.application.wish_application import WishFlaskApplication
from sparrow.base.api import WishApi
from sparrow.config import server_config, get_secrets_files
from sparrow.log.configurator import LoggingConfigurator
from sparrow.base.request import EasyRequest


def get_setting_files(config_dir, config_files, buildin_files=None):
    config_files = config_files or []
    config_files = [
        os.path.join(config_dir, f) if not os.path.isabs(f) else f for f in config_files
    ]
    return (buildin_files or []) + config_files


def create_app(name,
               application_clz=WishFlaskApplication,
               config_dir='config',
               config_files=None,
               **app_kwargs):
    """Create application instance and parse configs

    :param name: the name of the application package
    :param application_clz: WishFlaskApplication or its subclass
    :param config_dir: the dir to find setting files
        default is app.root_path/config
    :param config_files: list of the setting files in config_dir
        default is ['settings.yaml', '.secrets.yaml']
    :param app_kwargs: kwargs to be passed to application_clz
    :return: app instance
    """

    if not issubclass(application_clz, WishFlaskApplication):
        raise ValueError('%s is not subclass of %s', application_clz.__name__, WishFlaskApplication.__name__)
    app = application_clz(name, **app_kwargs)

    if not config_dir.startswith('/'):
        config_dir = os.path.join(app.root_path, config_dir)
    config_files = config_files or ['settings.yaml', '.secrets.yaml']

    setting_files = get_setting_files(config_dir, config_files,
                                      buildin_files=server_config)
    FlaskDynaconf(app, settings_files=setting_files + get_secrets_files())
    LoggingConfigurator.configure(app.config.logging)

    """
    If you try to access current_app, or anything that uses it, 
    outside an application context, you’ll get this error message:

    RuntimeError: Working outside of application context.
    This typically means that you attempted to use functionality that
    needed to interface with the current application object in some way.
    To solve this, set up an application context with app.app_context().
    
    If you see that error while configuring your application, 
    such as when initializing an extension, you can push a context manually 
    since you have direct access to the app. Use app_context() in a with block, 
    and everything that runs in the block will have access to current_app.
    """
    with app.app_context():
        app.init()

    """
    Try to register service to consul when in stage
    """
    if os.getenv("NEED_REGISTER") == "True":
        try:
            EasyRequest.request("POST", "http://wish-framework-portal:8000/api/service/register", body={
                "service_name": app.config["service_name"],
                "port": app.config["listener_port"],
            })
        except Exception as e:
            print("register to consul failed, err:{}".format(str(e)))
    atexit.register(app.close)
    return app


def create_api(app):
    return WishApi(app)
