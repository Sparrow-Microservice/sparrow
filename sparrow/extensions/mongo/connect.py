from sparrow.extensions.connector import Connector
from sparrow.extensions.mongo.instance import _instance_manager, MongoEngine
from sparrow.extensions.mongo.monitor import CommandLogger

from sparrow.extensions.mongo.reload_handler import ReloadHandler
from watchdog_gevent import Observer
from sparrow.config import get_mongodb_secrets_file

class MongoConnector(Connector):

    @classmethod
    def dependency_check(cls):
        if not MongoEngine:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        if config.get('MONGODB_SETTINGS'):
            if not MongoEngine:
                raise RuntimeError('Package flask_mongoengine is not installed')
            if CommandLogger:
                CommandLogger.register()

            mongodb_settings = config.get('MONGODB_SETTINGS')

            if 'host' in mongodb_settings and 'db' in mongodb_settings:
                m = MongoEngine(app, config=config)
            else:
                # Change to list
                settings = []
                for alias, config in mongodb_settings.items():
                    new_config = config
                    new_config['alias'] = alias
                    settings.append(new_config)
                m = MongoEngine(app, config=config)
            # MongoEngine already set app.extensions["mongoengine"][m]={"app": app, "conn": connections}
            _instance_manager.set_default_obj(m)
            reload_handler = ReloadHandler(app)
            observer = Observer()
            observer.schedule(event_handler=reload_handler, path=get_mongodb_secrets_file(), recursive=True)
            observer.start()


connector = MongoConnector
