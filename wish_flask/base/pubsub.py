import traceback
import typing as t

from wish_flask.utils.attr_utils import set_attr_from_config

if t.TYPE_CHECKING:
    from redis.client import PubSub
    from wish_flask.application.wish_application import WishFlaskApplication

from threading import Thread
import time
from wish_flask.base.resource import BaseResource
from wish_flask.log.meta import LoggingMixin
from wish_flask.extensions.redis.instance import redis as default_redis
from wish_flask.monitor.metrics import METRIC_PUBSUB


class BasePubSub(BaseResource, LoggingMixin):
    # The channel to subscribe and publish
    channel = None

    # The redis instance to use
    redis = default_redis

    # True to subscribe the channel
    to_sub = True

    def __init__(self):
        super().__init__()
        self._channel_name = None
        self._pubsub_manager = None
        self._enabled = True

    def init_app(self, app: 'WishFlaskApplication'):
        assert self.channel, 'channel is None for %s' % self.__class__.__name__
        super().init_app(app)
        config = app.config.get('pubsub') or {}
        self._enabled = config.get('enabled', True)
        service_name = app.config.get('service_name', '')
        namespace = config.get('namespace', service_name)
        self._channel_name = (namespace + '_' + self.channel) if namespace else self.channel
        self._pubsub_manager = app.pubsub_manager
        if config.get('to_sub') is False:
            self.to_sub = False
        self.subscribe()

    def subscribe(self):
        if self.to_sub and self._enabled:
            METRIC_PUBSUB.inc(type='subscribe', channel=self.channel)
            self._pubsub_manager.subscribe(self.redis, self._channel_name, self._sub)

    def pub(self, msg: str):
        """To publish a msg
        """
        if not self._enabled:
            return
        if not isinstance(msg, str):
            return
        result = 'success'
        try:
            self.redis.publish(self._channel_name, msg)
        except:
            result = 'fail'
        finally:
            METRIC_PUBSUB.inc(type='pub', channel=self.channel, result=result)

    def _sub(self, msg_info):
        self.logger.debug('Pubsub processing channel %s: %s', self.channel, msg_info)
        msg = msg_info.get('data', '') if msg_info else ''
        result = 'success'
        try:
            if isinstance(msg, bytes):
                try:
                    msg = msg.decode()
                except:
                    pass
            self.sub(msg)
        except Exception:
            result = 'fail'
            self.logger.error(
                'Pubsub handling error for channel %s. Msg: %s\n'
                '%s',
                self.channel,
                msg,
                traceback.format_exc()
            )
        finally:
            METRIC_PUBSUB.inc(type='sub', channel=self.channel, result=result)

    def sub(self, msg: t.Union[str, bytes]):
        """To process a msg which published to the associated channel.
        """
        raise NotImplementedError


class PubSubManager(LoggingMixin):

    def __init__(self, check_interval=5, check_timeout=0):
        self.subscribers = {}
        self.work_threads = {}
        self.check_interval = check_interval
        self.check_timeout = check_timeout

    def init_app(self, app):
        config = app.config.get('pubsub') or {}
        set_attr_from_config(self, config, 'check_interval')
        set_attr_from_config(self, config, 'check_timeout')

    def _get_subscriber(self, redis):
        s = self.subscribers.get(redis)
        if not s:
            s = redis.pubsub(ignore_subscribe_messages=True)
            self.subscribers[redis] = s
        return s

    def subscribe(self, redis, channel_name, callback):
        s = self._get_subscriber(redis)
        s.subscribe(**{channel_name: callback})

    def _process(self, subscriber: 'PubSub'):
        while True:
            response = True
            # self.logger.debug('Pubsub processing: %s', subscriber)
            while response:
                try:
                    response = subscriber.parse_response(block=False, timeout=self.check_timeout)
                except Exception as e:
                    self.logger.error('Pubsub fetching error: %s', str(e))
                    response = False
                if response:
                    subscriber.handle_message(response)
            if self.check_interval > 0:
                time.sleep(self.check_interval)

    def consume(self):
        for s in self.subscribers.values():
            worker = Thread(target=self._process, args=(s,), daemon=True)
            self.work_threads[s] = worker
            worker.start()
