from wish_flask.lib.instance_manager import InstanceManager
from wish_flask.extensions.metrics.wish_metrics import WishPrometheusMetrics

_instance_type = 'metrics'
_instance_manager = InstanceManager.get_manager(_instance_type)

if WishPrometheusMetrics:
    # Create metrics instance globally as it may be used in decorator
    _instance_manager.set_default_obj(WishPrometheusMetrics.for_app_factory())

# annotations
metrics: WishPrometheusMetrics = _instance_manager.get_obj_proxy(support_none=True)
