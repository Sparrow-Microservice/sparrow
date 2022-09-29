from wish_cn_common.metrics.common import init_metrics
from sparrow.log.meta import LoggingMixin
from flask import current_app

try:
    from pymongo import monitoring


    class CommandLogger(monitoring.CommandListener, LoggingMixin):

        def __init__(self):
            app = current_app
            self.metrics_client = init_metrics(app.config.get("service_name"),
                                               init_switch=False)

        @classmethod
        def register(cls):
            monitoring.register(cls())

        def started(self, event):
            self.metrics_client.count("wish_flask_mongo_call_count", 1,
                                      **{"command_name": event.command_name,
                                         "database_name": event.database_name})
            self.logger.debug("Command {0.command_name} with request id "
                              "{0.request_id} started on server "
                              "{0.connection_id}".format(event))

        def succeeded(self, event):
            self.metrics_client.timer("wish_flask_mongo_times_histgram",
                                      event.duration_micros / 1e6,
                                      **{"command_name": event.command_name})
            self.logger.debug("Command {0.command_name} with request id "
                              "{0.request_id} on server {0.connection_id} "
                              "succeeded in {0.duration_micros} "
                              "microseconds".format(event))

        def failed(self, event):
            self.metrics_client.count("wish_flask_mongo_error_call_count", 1,
                                      **{"command_name": event.command_name})

            self.metrics_client.timer("wish_flask_mongo_times_histgram",
                                      event.duration_micros / 1e6,
                                      **{"command_name": event.command_name})
            self.logger.debug("Command {0.command_name} with request id "
                              "{0.request_id} on server {0.connection_id} "
                              "failed in {0.duration_micros} "
                              "microseconds".format(event))

except:
    CommandLogger = None
