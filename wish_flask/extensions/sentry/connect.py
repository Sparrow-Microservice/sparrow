from wish_flask.extensions.sentry.instance import _instance_manager
from wish_flask.extensions.connector import Connector

try:
    import sentry_client
    from sentry_sdk.integrations.flask import FlaskIntegration
except:
    sentry_client = None
    FlaskIntegration = None
# import sentry_sdk
from wish_flask.log.meta import LoggingMixin
from collections import namedtuple
import socket

sentry_config = namedtuple("sentry_config",
                           ['project_id', 'env', 'release', 'server_name',
                            "kwargs"], defaults=None)


class SentryConnector(Connector, LoggingMixin):

    @classmethod
    def _get_config(cls, app, config):
        project_id = app.config.get("service_name")
        env = app.env
        release = app.config.get("API_VERSION", "UNKNOWN")
        server_name = socket.gethostname()
        config.pop("enabled")
        kwargs = config.to_dict()
        sc = sentry_config(project_id=project_id,
                           env=env,
                           release=release,
                           server_name=server_name,
                           kwargs=kwargs)
        cls.logger.debug("sentry config: %s", sc)
        return sc

    @classmethod
    def dependency_check(cls):
        if not sentry_client:
            return False
        return True


    @classmethod
    def do_connect(cls, app, config=None):
        config = cls._get_config(app, config)

        sentry_client.init(
            config.project_id,
            config.env,
            config.release,
            config.server_name,
            integrations=[FlaskIntegration()],
            **config.kwargs
        )
        _instance_manager.set_default_obj(sentry_client)


connector = SentryConnector
