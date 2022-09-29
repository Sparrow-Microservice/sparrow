from sparrow.extensions.connector import Connector
from sparrow.extensions.metrics.instance import _instance_manager, metrics
from sparrow.extensions.metrics.wish_metrics import WishPrometheusMetrics


class MetricsConnector(Connector):
    @classmethod
    def dependency_check(cls):
        if not WishPrometheusMetrics:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        metrics.init_app(app, config=config)
        app.extensions.setdefault('metrics', _instance_manager.all_objs)


connector = MetricsConnector
