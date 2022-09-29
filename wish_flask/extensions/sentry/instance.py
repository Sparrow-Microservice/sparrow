from wish_flask.lib.instance_manager import InstanceManager

_instance_type = 'sentry'
_instance_manager = InstanceManager.get_manager(_instance_type)

sentry_switch = _instance_manager.get_obj_proxy()
