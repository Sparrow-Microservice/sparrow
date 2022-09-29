import os

from watchdog.events import FileSystemEventHandler
import time
from dynaconf import Dynaconf
from sparrow.log.meta import LoggingMixin
from mongoengine.connection import register_connection, DEFAULT_CONNECTION_NAME, _connections, _dbs, get_connection


class ReloadHandler(FileSystemEventHandler, LoggingMixin):

    def __init__(self, app, *args, **kwargs):
        self.app = app
        super(ReloadHandler, self).__init__(*args, **kwargs)

    def _check_setting_valid(self, settings):
        env = os.getenv('FLASK_ENV')
        setting = settings.get(env, {}).get('extensions', {}).get('mongo', {}).get('MONGODB_SETTINGS', {})
        return setting != {}

    def disconnect(self, alias=DEFAULT_CONNECTION_NAME):
        """Close the connection with a given alias."""
        from mongoengine import Document
        from mongoengine.base.common import _get_documents_by_db

        if alias in _connections:
            get_connection(alias=alias).close()
            del _connections[alias]

        if alias in _dbs:
            # Detach all cached collections in Documents
            for doc_cls in _get_documents_by_db(alias, DEFAULT_CONNECTION_NAME):
                if issubclass(doc_cls, Document):  # Skip EmbeddedDocument
                    doc_cls._disconnect()

            del _dbs[alias]

        # if alias in _connection_settings:
        #     del _connection_settings[alias]

    def _reload_config(self, mongo_setting):
        register_connection(**mongo_setting)
        self.disconnect(mongo_setting['alias'])

    def on_modified(self, event):
        current_app = self.app
        self.logger.info("mongodb secret file on modified, time: %s", int(time.time()))
        # print("on_modified", event.src_path, int(time.time()))
        settings = Dynaconf(settings_files=[event.src_path])
        env = os.getenv('FLASK_ENV')
        if not self._check_setting_valid(settings):
            self.logger.error("mongodb secret file format is invalid, please check this file!, settings: %s", settings)
            return

        mongo_settings = settings.get(env).get('extensions').get('mongo').get('MONGODB_SETTINGS')
        app_mongo_settings = current_app.config.get('extensions').get('mongo').get('MONGODB_SETTINGS')

        if 'host' in app_mongo_settings and 'db' in app_mongo_settings:
            # only have one mongodb setting
            # check its password and username is equal
            if app_mongo_settings['username'] == mongo_settings['username'] and app_mongo_settings['password'] == mongo_settings['password']:
                self.logger.info("Mongo's username and password is equal. Don't need to reload!")
                return
            current_app.config['extensions']['mongo']['MONGODB_SETTINGS']['username'] = mongo_settings['username']
            current_app.config['extensions']['mongo']['MONGODB_SETTINGS']['password'] = mongo_settings['password']
            mongo_settings.update(app_mongo_settings)
            if 'alias' not in mongo_settings:
                mongo_settings['alias'] = 'default'
            self._reload_config(mongo_settings)
        else:
            # have multi mongodb settings
            for alias, setting in mongo_settings.items():
                if app_mongo_settings[alias]['username'] == setting['username'] and app_mongo_settings[alias]['password'] == setting['password']:
                    continue
                current_app.config['extensions']['mongo']['MONGODB_SETTINGS'][alias]['username'] = setting['username']
                current_app.config['extensions']['mongo']['MONGODB_SETTINGS'][alias]['password'] = setting['password']
                setting.update(app_mongo_settings[alias])
                if 'alias' not in setting:
                    setting['alias'] = alias
                self._reload_config(setting)
        self.logger.info("reload mongo screct success!")

