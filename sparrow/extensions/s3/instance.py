from sparrow.lib.instance_manager import InstanceManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sparrow.lib.s3.abstract_s3 import BaseS3Abstraction

_instance_type = 's3'
_instance_manager = InstanceManager.get_manager(_instance_type)

s3: 'BaseS3Abstraction'


# dynamic instance generation based on import
def __getattr__(name):
    return _instance_manager.get_obj_proxy_from_global(globals(), name, splitter='_')
