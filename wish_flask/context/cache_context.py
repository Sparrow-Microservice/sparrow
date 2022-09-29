from wish_flask.context.base_context import ValueContext

CACHE_KEY = "CACHE_TIME"


class CacheContext(ValueContext):
    stats_key = CACHE_KEY
