from wish_flask.lib.instance_manager import InstanceManager

try:
    from elasticsearch import Elasticsearch
except:
    Elasticsearch = None

_instance_type = 'elastic_search'
_instance_manager = InstanceManager.get_manager(_instance_type)

elastic_search: 'Elasticsearch'


def __getattr__(name):
    return _instance_manager.get_obj_proxy_from_global(globals(), name,
                                                       splitter='_')
