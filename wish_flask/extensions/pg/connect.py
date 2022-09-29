from wish_flask.extensions.connector import Connector
from wish_flask.extensions.pg.instance import _instance_manager, pg, SQLAlchemy
from wish_flask.utils.gevent_utils import is_gevent_patched, patch_psycopg2


class PgConnector(Connector):
    @classmethod
    def dependency_check(cls):
        if not SQLAlchemy:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        sql_settings = config.get('settings', {})
        for k in sql_settings:
            if k.startswith('SQLALCHEMY_'):
                app.config[k] = sql_settings[k]
        pg.init_app(app)
        pg.app = app
        app.extensions.setdefault('pg', _instance_manager.all_objs)
        cls.patch_psycopg2()
        cls.init_migrate(app, pg)

    @classmethod
    def init_migrate(cls, app, pg):
        try:
            from flask_migrate import Migrate
        except:
            Migrate = None
        if Migrate:
            Migrate(app, pg)

    @classmethod
    def patch_psycopg2(cls):
        if is_gevent_patched():
            patch_psycopg2()


connector = PgConnector
