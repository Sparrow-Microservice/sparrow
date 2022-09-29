from wish_flask.extensions.connector import Connector
from wish_flask.extensions.mq.flask_mq import FlaskProducer, FlaskWorker
from wish_flask.extensions.mq.producer_instance import _instance_manager as producer_manager
from wish_flask.extensions.mq.worker_instance import _instance_manager as worker_manager


class MqConnector(Connector):

    @classmethod
    def dependency_check(cls):
        if not FlaskProducer:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        settings = config.get('settings')
        if settings:
            for key, setting in settings.items():
                common_settings = setting.get('common', {})
                producer_settings = setting.get('producer')
                if producer_settings is not None:
                    producer_settings.update(common_settings)
                    producer = FlaskProducer(name=key, **producer_settings)
                    producer_manager.set_obj(key, producer)
                worker_settings = setting.get('worker')
                if worker_settings:
                    worker_settings.update(common_settings)
                    worker = FlaskWorker(name=key, **worker_settings)
                    worker_manager.set_obj(key, worker)


connector = MqConnector
