from wish_flask.lib.instance_manager import InstanceManager

try:
    from wish_cache_manager.cache_manager_facade import CacheManagerFacade
    from wish_cache_manager.apm.instrumentation_utils import \
        build_instrumentation_set
except:
    CacheManagerFacade = None
    build_instrumentation_set = None
try:
    from wish_flask.extensions.apm.instrumentation_utils import \
        register_instrumentation
except:
    register_instrumentation = None

_instance_type = 'cache_manager'
_instance_manager = InstanceManager.get_manager(_instance_type)

cache_manager: 'CacheManagerFacade'

if build_instrumentation_set and register_instrumentation:
    cache_instrumentation_set = build_instrumentation_set()
    for instrumentation in cache_instrumentation_set:
        register_instrumentation(instrumentation)


def __getattr__(name):
    val, is_find = _instance_manager.find_obj_from_global(globals(), name)
    if is_find:
        return val
    _, obj_name = _instance_manager.find_obj_name_by_full_name(name,
                                                               _instance_type,
                                                               splitter='_')

    if obj_name is None:
        raise RuntimeError(
            "invalid cache manager instance name! "
            "Please pay attention to your instance name: %s" % name)

    if CacheManagerFacade is None:
        raise RuntimeError(
            'Please execute `pip install "wish_flask[cache-manager]"`'
            'if you want to use it!')

    obj = _instance_manager.get_obj_proxy(obj_name)
    if bool(obj):
        return obj

    _instance_manager.set_obj(obj_name, CacheManagerFacade())
    val = _instance_manager.get_obj_proxy(name=obj_name)
    globals()[name] = val
    return val
