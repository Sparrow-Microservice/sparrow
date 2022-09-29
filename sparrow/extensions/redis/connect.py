from sparrow.extensions.connector import Connector
from sparrow.extensions.redis.instance import FlaskRedis, _instance_manager
import copy
from wish_cn_common.metrics.common import init_metrics
import time


class RedisConnector(Connector):
    @classmethod
    def dependency_check(cls):
        if not FlaskRedis:
            return False
        return True

    @classmethod
    def patch_redis(cls, app):
        from redis.client import Redis
        metrics_client = init_metrics(app.config.get('service_name'),
                                      init_switch=False)

        def new_execute_command(f):
            def decorator(*args, **kwargs):
                now = time.time()
                command_name = args[1]
                metrics_client.count("wish_flask_redis_call_count", 1,
                                     **{"command_name": command_name, })
                try:
                    res = f(*args, **kwargs)
                except:
                    metrics_client.count("wish_flask_redis_error_call_count", 1,
                                         **{"command_name": command_name})
                    raise
                finally:
                    metrics_client.timer("wish_flask_redis_times_histgram",
                                         time.time() - now,
                                         **{"command_name": command_name})
                return res

            return decorator

        Redis.execute_command = new_execute_command(Redis.execute_command)

    @classmethod
    def do_connect(cls, app, config=None):
        """
        Any additional querystring arguments and keyword arguments apart from 'url'
        will be passed along to the ConnectionPool class's initializer. The querystring
        arguments ``socket_connect_timeout`` and ``socket_timeout`` if supplied
        are parsed as float values. The arguments ``socket_keepalive`` and
        ``retry_on_timeout`` are parsed to boolean values that accept
        True/False, Yes/No values to indicate state. Invalid types cause a
        ``UserWarning`` to be raised. In the case of conflicting arguments,
        querystring arguments always win.
        """

        default_setting = {
            "socket_timeout": 60,
            "socket_connect_timeout": 60,
            "health_check_interval": 60
        }

        settings = config.get("settings")
        config_default_setting = config.get("default_setting")
        if config_default_setting:
            default_setting.update(config_default_setting)
        if settings:
            """
            do some redis patch
            """
            cls.patch_redis(app)

            for key, setting in settings.items():
                real_setting = copy.deepcopy(default_setting)
                real_setting.update(setting)
                url = real_setting.pop("url")
                prefix = 'REDIS_' + key.upper()
                app.config[prefix + '_URL'] = url
                redis = FlaskRedis(app=app, config_prefix=prefix,
                                   **real_setting)
                app.extensions.setdefault('all_redis', _instance_manager.all_objs)
                _instance_manager.set_obj(key, redis)


connector = RedisConnector
