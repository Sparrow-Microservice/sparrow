from sparrow.extensions.connector import Connector
from sparrow.log.meta import LoggingMixin
from sparrow.extensions.elastic_search.instance import _instance_manager

try:
    from elasticsearch import Elasticsearch
except:
    Elasticsearch = None


class ElasticSearchConnector(Connector, LoggingMixin):
    @classmethod
    def dependency_check(cls):
        if Elasticsearch is None:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        cls.logger.debug("init elastic search client")
        enabled = config.get("enabled")
        settings = config.get("settings")
        if enabled and settings:
            for key, setting in settings.items():
                host = setting['host']
                es = Elasticsearch(hosts=host)
                _instance_manager.set_obj(key, es)


connector = ElasticSearchConnector
