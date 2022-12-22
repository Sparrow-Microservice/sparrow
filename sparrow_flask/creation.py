import atexit
import os
from dynaconf import FlaskDynaconf
from sparrow_flask.base import Sparrow
# from wish_flask_resource_manager.resource_extension import ResourceManagerExtension
from flask_smorest import Api


def create_app(env=None):
    """Create application instance and parse configs
    """
    app = Sparrow(__name__)
    config_dir = os.path.join(app.root_path, 'config')
    config_files = ['default.yaml']
    if env is not None:
        config_files.append(env + '.yaml')
    setting_files = [os.path.join(config_dir, f) for f in config_files]
    FlaskDynaconf(app, settings_files=setting_files)

    app.setups()

    # Add wish resource manager to app
    # https://github.com/ContextLogic/wish-flask-resource-manager
    # ResourceManagerExtension(app)
    atexit.register(app.close)
    return app


