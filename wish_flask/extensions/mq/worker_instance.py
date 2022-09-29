from wish_flask.lib.instance_manager import InstanceManager

from wish_flask.extensions.mq.flask_mq import FlaskWorker

_instance_type = 'worker'
_instance_manager = InstanceManager.get_manager(_instance_type)


# annotations
worker: 'FlaskWorker'


# dynamic instance generation based on import
def __getattr__(name):
    return _instance_manager.get_obj_proxy_from_global(globals(), name, splitter='_')
