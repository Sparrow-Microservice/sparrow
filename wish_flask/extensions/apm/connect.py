from wish_flask.extensions.connector import Connector
try:
    from elasticapm.contrib.flask import ElasticAPM
except:
    ElasticAPM = None
from wish_flask.log.meta import LoggingMixin
import random


class ApmConnector(Connector, LoggingMixin):
    @classmethod
    def dependency_check(cls):
        if ElasticAPM is None:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        enabled = config.get("enabled")
        enable_rate = config.get("enable_rate")
        params = config.get("params")
        params["SERVICE_NAME"] = app.config.get("service_name")

        if "ENVIRONMENT" not in params:
            params["ENVIRONMENT"] = app.env
        cls.logger.debug("environment is %s", params["ENVIRONMENT"])

        flag = enabled and enable_rate > random.random()
        cls.logger.debug("flag is %s", flag)
        if flag:
            if ElasticAPM is None:
                raise RuntimeError("ElasticAPM does not install")
            app.config['ELASTIC_APM'] = params
            apm = ElasticAPM(app)


connector = ApmConnector
