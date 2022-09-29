import logging
from logging.config import dictConfig

from sparrow.log.meta import LoggingMixin


class LoggingConfigurator(LoggingMixin):

    @classmethod
    def basic_config(cls, level=None):
        root_logger = logging.getLogger()
        if len(root_logger.handlers) == 0:
            logging.basicConfig(level=level or 'INFO')

    @classmethod
    def configure(cls, settings):
        if settings:  # trigger Dynaconf to setup
            level = settings.get('root', {}).get('level')
            cls.basic_config(level)
            cls.logger.debug("Logging config: %s", settings)
            dictConfig(settings)
