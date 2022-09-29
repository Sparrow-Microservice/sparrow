from wish_flask.lib.instance_manager import InstanceManager

try:
    from flask_mongoengine import MongoEngine
except:
    MongoEngine = None

_instance_type = 'mongoengine'
_instance_manager = InstanceManager.get_manager(_instance_type)

# annotations
mongoengine: 'MongoEngine' = _instance_manager.get_obj_proxy()
