from abc import ABC

try:
    from wish_cache_manager.cache_cli.abstract_cache import AbstractCacheClient
except:
    AbstractCacheClient = None

if AbstractCacheClient:
    from wish_cache_manager.cache_helper import CacheDoLoadHelper, \
        CacheDoSaveHelper, \
        CacheEvictHelper, CacheEvictAllHelper, CacheMGetHelper, CacheMSetHelper, \
        CachePipelineHelper, CachePipelineExecuteHelper
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from redis import StrictRedis
        from redis.client import Pipeline


    class StrictRedisCache(AbstractCacheClient, ABC):

        def conn(self) -> 'StrictRedis':
            return super(StrictRedisCache, self).conn()

        redis: 'StrictRedis' = property(conn)
        actor = 'redis'

        def check_available(self):
            return bool(self.redis)

        @CacheDoLoadHelper.exception_help
        def do_load(self, key, **kwargs):
            return self.redis.get(key)

        @CacheDoSaveHelper.exception_help
        def do_save(self, key, data, ttl=None, **kwargs):
            ttl = ttl if ttl is not None else self.ttl
            return self.redis.set(key, data, ex=ttl or None)

        @CacheMGetHelper.exception_help
        def mget(self, keys, **kwargs):
            return self.redis.mget(keys)

        @CacheMSetHelper.exception_help
        def mset(self, mapping):
            return self.redis.mset(mapping)

        @CachePipelineHelper.exception_help
        def pipeline(self, *args, **kwargs):
            return self.redis.pipeline(*args, **kwargs)

        @CachePipelineExecuteHelper.exception_help
        def pipeline_execute(self, pipeline: 'Pipeline', **kwargs):
            return pipeline.execute()

        @CacheEvictHelper.exception_help
        def do_evict(self, keys, **kwargs):
            return self.redis.delete(*keys) > 0

        @CacheEvictAllHelper.exception_help
        def do_evict_all_cache(self, pattern, **kwargs):
            size = 0
            chunk = 100
            keys = []
            for key in self.redis.scan_iter(match=pattern, count=chunk):
                keys.append(key)
                if len(keys) >= chunk:
                    size += self.redis.delete(*keys)
                    keys = []
            if keys:
                size += self.redis.delete(*keys)
            return size
else:
    StrictRedisCache = None
