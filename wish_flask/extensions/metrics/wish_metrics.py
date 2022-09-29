try:
    from prometheus_flask_exporter import PrometheusMetrics
except:
    PrometheusMetrics = None


if PrometheusMetrics:
    from prometheus_client import Counter, Histogram, Gauge, Summary, Info, Enum

    ALL_METRIC_TYPES = [Counter, Histogram, Gauge, Summary, Info, Enum]
    METRICS_MAPPING = {t.__name__.lower(): t for t in ALL_METRIC_TYPES}

    class MetricsRegistry(object):
        metrics_dict = {}

        @classmethod
        def key(cls, name, namespace='', subsystem='', unit=''):
            return name, namespace, subsystem, unit

        @classmethod
        def register(cls, metric, orig_name, namespace='', subsystem='', unit=''):
            # Simple register without considering namespace and subsystem
            cls.metrics_dict[cls.key(orig_name, namespace, subsystem, unit)] = metric

        @classmethod
        def get(cls, name, namespace='', subsystem='', unit=''):
            return cls.metrics_dict.get(cls.key(name, namespace, subsystem, unit))

    class WishMetric(object):

        def __init__(self, metric, defaults: dict = None):
            self.metric = metric
            self.defaults = defaults or {}

        def _labeled_metric(self, labelvalues, labelkwargs):
            # TODO Disable metrics if not inited
            metric = self.metric
            if labelvalues or labelkwargs or self.defaults:
                label_dict = self.defaults.copy()
                label_dict.update(labelkwargs)
                metric = metric.labels(*labelvalues, **label_dict)
            return metric

        # Counter, Gauge
        def inc(self, amount=1, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).inc(amount=amount)

        # Gauge
        def dec(self, amount=1, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).dec(amount=amount)

        # Gauge
        def set(self, value, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).set(value)

        # Gauge, Summary, Histogram
        def time(self, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).time()

        # Summary, Histogram
        def observe(self, amount, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).observe(amount)

        # Info
        def info(self, val, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).info(val)

        # Enum
        def state(self, state, *labelvalues, **labelkwargs):
            return self._labeled_metric(labelvalues, labelkwargs).state(state)


    class WishPrometheusMetrics(PrometheusMetrics):
        def __init__(self, *args, **kwargs):
            self.metrics_dict = {}
            super(WishPrometheusMetrics, self).__init__(*args, **kwargs)

        def init_app(self, app, config=None):
            app.metrics = self
            super(WishPrometheusMetrics, self).init_app(app)

        # Check prometheus_client.metrics for params details
        def create_metric(self, metric_type, name, documentation='', labelnames=(),
                          namespace='', subsystem='', unit='', **kwargs):
            for m in METRICS_MAPPING:
                if m.startswith(metric_type):
                    defaults: dict = kwargs.pop('defaults', None)
                    metric = METRICS_MAPPING[m](name, documentation,
                                                labelnames=labelnames,
                                                registry=kwargs.pop('registry', None) or self.registry,
                                                namespace=namespace,
                                                subsystem=subsystem,
                                                unit=unit,
                                                **kwargs)
                    metric = WishMetric(metric, defaults=defaults)
                    MetricsRegistry.register(metric, name,
                                             namespace=namespace,
                                             subsystem=subsystem,
                                             unit=unit)
                    return metric
            return None

        def create_counter(self, name, documentation='', labelnames=(), **kwargs):
            return self.create_metric('c', name, documentation, labelnames=labelnames, **kwargs)

        def create_gauge(self, name, documentation='', labelnames=(), **kwargs):
            return self.create_metric('g', name, documentation, labelnames=labelnames, **kwargs)

        def create_summary(self, name, documentation='', labelnames=(), **kwargs):
            return self.create_metric('s', name, documentation, labelnames=labelnames, **kwargs)

        def create_histogram(self, name, documentation='', labelnames=(), buckets=None, **kwargs):
            return self.create_metric('h', name, documentation, labelnames=labelnames,
                                      buckets=buckets or Histogram.DEFAULT_BUCKETS,
                                      **kwargs)

        def create_info(self, name, documentation='', labelnames=(), **kwargs):
            return self.create_metric('i', name, documentation, labelnames=labelnames, **kwargs)

        def create_enum(self, name, documentation='', labelnames=(), states=None, **kwargs):
            return self.create_metric('e', name, documentation, labelnames=labelnames, states=states, **kwargs)

        c = create_counter
        g = create_gauge
        s = create_summary
        h = create_histogram
        i = create_info
        e = create_enum

        def get_metric(self, name, namespace='', subsystem='', unit='',
                       metric_type=None, create_for_none=False, **kwargs):
            metric = MetricsRegistry.get(name, namespace, subsystem, unit)
            if not metric and create_for_none and metric_type:
                metric = self.create_metric(metric_type, name,
                                            namespace=namespace,
                                            subsystem=subsystem,
                                            unit=unit,
                                            **kwargs)
            return metric

else:
    WishPrometheusMetrics = None
