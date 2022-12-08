import atexit
import os
from sparrow.base import Sparrow


def create_app():
    """Create application instance and parse configs
    """
    env = os.getenv('FLASK_ENV') or 'default'
    app = Sparrow(__name__)
    # Do init
    app.setup(env)

    # Do init extensions
    # Add wish resource manager to app
    # https://github.com/ContextLogic/wish-flask-resource-manager
    # from wish_flask_resource_manager.resource_extension import ResourceManagerExtension
    # ResourceManagerExtension(app)

    # Register blueprints
    from sparrow.blueprints.hello import hello_blp
    from sparrow.blueprints.general import general_bp
    app.register_blueprints(
        [hello_blp, general_bp]
    )

    return app


