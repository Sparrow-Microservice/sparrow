from wish_flask.extensions.connector import Connector
from wish_flask.extensions.s3.instance import _instance_manager
from wish_flask.lib.s3.s3_factory import S3Factory, S3Type

try:
    import boto3
except:
    boto3 = None


class S3Connector(Connector):
    @classmethod
    def dependency_check(cls):
        if not boto3:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        settings = config.get('settings')
        if settings:
            for k in settings:  # "default" is special
                setting = settings[k]
                if setting.get('s3_type') != S3Type.MOCK and not boto3:
                    raise RuntimeError('Package boto3 is not installed')
                s3 = S3Factory.make_s3(**setting)
                s3.init_app(app)
                app.extensions.setdefault('s3', _instance_manager.all_objs)
                _instance_manager.set_obj(k, s3)


connector = S3Connector
