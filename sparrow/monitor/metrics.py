from sparrow.extensions.metrics.instance import metrics

METRIC_TD_AGENT = metrics.create_counter('td_agent', labelnames=('event', 'host', 'tag'),
                                         defaults={'host': '', 'tag': ''})
METRIC_EXCEPTIONS = metrics.create_counter('exceptions',
                                           labelnames=('exp', 'err_code', 'uri', 'http_code', 'api_exp'),
                                           defaults={'api_exp': ''})
METRIC_PUBSUB = metrics.create_counter('pubsub', labelnames=('type', 'channel', 'result'),
                                       defaults={'result': 'None'})

METRIC_MICRO_CLIENT_REQUEST_TIME = metrics.create_histogram('micro_client_request_times_histgram',
                                                            labelnames=('env', 'url', 'method', 'from', 'to'),
                                                            defaults={'from': 'unknown', 'to': 'unknown'})

METRIC_MICRO_CLIENT_REQUEST_COUNT = metrics.create_counter('micro_client_request_count',
                                                           labelnames=('env', 'url', 'method', 'from', 'to'),
                                                           defaults={'from': 'unknown', 'to': 'unknown'})

METRIC_MICRO_CLIENT_API_ERROR_COUNT = metrics.create_counter('micro_client_api_error_count',
                                                             labelnames=('env', 'url', 'method', 'err_type', 'from', 'to'),
                                                             defaults={'from': 'unknown', 'to': 'unknown'})

