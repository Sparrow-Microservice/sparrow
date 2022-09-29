from sparrow.extensions.cache_manager.instance import _instance_manager
from sparrow.extensions.redis.instance import \
    _instance_manager as redis_instance_manager

from sparrow.extensions.connector import Connector
from sparrow.log.meta import LoggingMixin
from sparrow.extensions.cache_manager.strict_redis_cache_cli import \
    StrictRedisCache

try:
    from wish_cache_manager.cache_cli.local_cache import LocalCache
    from wish_cache_manager.cache_manager_facade import CacheManagerFacade
    from wish_cache_manager import cache_helper
    from wish_cache_manager.cache_helper import CacheHelper
except Exception:
    LocalCache = None
    CacheManagerFacade = None
    cache_helper = None
    CacheHelper = None
import logging

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis import StrictRedis

redis_cache_manager: 'StrictRedis'

from collections import namedtuple

cache_manager_connect_config = namedtuple("cache_manager_connect_config",
                                          ['namespace', 'local_cache_ttl',
                                           'redis_cache_ttl', 'redis_name',
                                           'setting'], defaults=None)


class CacheManagerConnector(Connector, LoggingMixin):
    empty_redis_instance = set()

    @classmethod
    def instance_check(cls):
        instance_dict = _instance_manager.all_objs
        no_init_instance_list = []

        for key, instance in instance_dict.items():
            instance: CacheManagerFacade
            if key not in cls.empty_redis_instance and not instance.check_cache_cli_available():
                no_init_instance_list.append(key)

        if len(no_init_instance_list):
            raise RuntimeError(
                "Some cache manager's redis client is unavailable, "
                "maybe you use wrong cache manager or forget init it. "
                "Please check your code and config: %s" % no_init_instance_list)

    @classmethod
    def _cache_helper_log_config(cls):
        CacheHelper.to_td_log = False
        cache_helper.cache_logger = logging.getLogger("td.cache_logger")

    @classmethod
    def _get_config(cls, app, setting):
        namespace = setting.pop("namespace", None)
        local_cache_ttl = setting.pop("local_cache_ttl", None)
        redis_cache_ttl = setting.pop("redis_cache_ttl", None)
        if "redis" not in setting:
            redis_name = ""
        else:
            redis_name = setting.pop("redis")
        if "env" not in setting:
            setting["env"] = app.env
        if namespace is None:
            namespace = app.config.get("service_name") + ":"
        cls.logger.debug("namespace: %s", namespace)
        cls.logger.debug("local_cache_ttl: %s", local_cache_ttl)
        cls.logger.debug("redis_cache_ttl: %s", redis_cache_ttl)
        cls.logger.debug("redis_name: %s", redis_name)
        cls.logger.debug("setting:%s", setting)
        return cache_manager_connect_config(namespace, local_cache_ttl,
                                            redis_cache_ttl, redis_name,
                                            setting)

    @classmethod
    def _configure(cls, key, app, setting):
        config = cls._get_config(app, setting)
        if config.redis_name == '':
            cls.empty_redis_instance.add(key)
        redis = redis_instance_manager.get_obj_proxy(config.redis_name)
        local_cache = LocalCache(ttl=config.local_cache_ttl)
        redis_cache = StrictRedisCache(redis, ttl=config.redis_cache_ttl)
        instance = _instance_manager.get_obj_proxy(key)
        if instance:
            instance: CacheManagerFacade
            instance.set_namespace(config.namespace)
            instance.set_cache_cli(redis_cache)
            instance.set_local_cache_cli(local_cache)
            instance.set_default_config(config.setting)

        else:
            _instance_manager.set_obj(
                key,
                CacheManagerFacade(
                    namespace=config.namespace,
                    cache_cli=redis_cache,
                    local_cache_cli=local_cache,
                    **config.setting
                )
            )

    @classmethod
    def dependency_check(cls):
        if not CacheManagerFacade:
            return False
        return True

    @classmethod
    def do_connect(cls, app, config=None):
        cls._cache_helper_log_config()
        settings = config.get("settings", {})
        for k in settings:
            setting = settings[k]
            cls._configure(k, app, setting)


connector = CacheManagerConnector
