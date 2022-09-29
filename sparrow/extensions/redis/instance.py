from sparrow.lib.instance_manager import InstanceManager

try:
    from flask_redis import FlaskRedis
    from redis import StrictRedis
except:
    FlaskRedis = None

_instance_type = 'redis'
_instance_manager = InstanceManager.get_manager(_instance_type)

# annotations
redis: 'StrictRedis'


# dynamic instance generation based on import
def __getattr__(name):
    return _instance_manager.get_obj_proxy_from_global(globals(), name, splitter='_')
