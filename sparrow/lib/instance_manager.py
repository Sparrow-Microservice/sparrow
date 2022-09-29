from functools import partial

from werkzeug.local import LocalProxy

from sparrow.lib.cookbook import BlackHole
from sparrow.log.meta import LoggingMixin

INSTANCE_DEFAULT_KEY = 'default'
OBJ_FULL_NAME_SPLITTER = '__'


class GeneralProxy(LocalProxy):
    """
    Acts as a proxy for objects. Unbound proxy will raise exceptions when accessing its properties.
    """

    @property
    def __class__(self):
        if bool(self):
            return self._get_current_object().__class__
        return type(self)


class NoopProxy(GeneralProxy):
    """
    Acts as a proxy for objects.
    Unbound proxy will not raise exceptions when accessing its properties by creating new BlackHole instances.
    """

    def __getattr__(self, name):
        if not bool(self):
            return lambda *args, **kwargs: BlackHole()
        return super(NoopProxy, self).__getattr__(name)


class InstanceManager(LoggingMixin):
    managers = {}

    def __init__(self, instance_type):
        self.instance_type = instance_type
        self.obj_dict = {}

    @property
    def all_objs(self):
        return self.obj_dict

    @classmethod
    def find_all_proxies(cls, splitter=OBJ_FULL_NAME_SPLITTER):
        proxies = {}
        for m in cls.managers.values():
            proxies[m.instance_type] = m.get_obj_proxy()
            for o in m.all_objs:
                if o != INSTANCE_DEFAULT_KEY:
                    proxies[m.instance_type + splitter + o] = m.get_obj_proxy(name=o)
        return proxies

    @classmethod
    def find_all_objects(cls, splitter=OBJ_FULL_NAME_SPLITTER):
        objs = {}
        for m in cls.managers.values():
            for o in m.all_objs:
                if o == INSTANCE_DEFAULT_KEY:
                    objs[m.instance_type] = m.all_objs[o]
                else:
                    objs[m.instance_type + splitter + o] = m.all_objs[o]
        return objs

    @classmethod
    def get_manager(cls, instance_type, init=True):
        m = cls.managers.get(instance_type)
        if not m and init:
            m = cls(instance_type)
            cls.managers[instance_type] = m
        return m

    @classmethod
    def find_obj_name_by_full_name(cls, full_name, instance_type=None, splitter=None):
        if instance_type and not full_name.startswith(instance_type):
            return None, None
        splitter = splitter or OBJ_FULL_NAME_SPLITTER
        instance_type = instance_type or next((k for k in cls.managers if full_name.startswith(k)),
                                              full_name.split(splitter, 1)[0])
        if full_name == instance_type:
            return instance_type, INSTANCE_DEFAULT_KEY
        full_name = full_name[len(instance_type):]

        if not full_name.startswith(splitter):
            return instance_type, None

        if full_name == splitter:
            return instance_type, INSTANCE_DEFAULT_KEY
        return instance_type, full_name[len(splitter):]

    @classmethod
    def find_obj_proxy(cls,
                       full_name=None,  # <instance_type><splitter><obj_name> e.g. redis_cache
                       instance_type=None,  # e.g. redis
                       obj_name=None,  # e.g. cache
                       support_none=False,
                       splitter=None):  # e.g. "_"
        assert full_name or instance_type, "full_name and instance_type can not be None at the same time"
        if full_name:
            instance_type, parsed_obj_name = cls.find_obj_name_by_full_name(full_name, instance_type, splitter)
            if not parsed_obj_name:
                return None
        else:
            parsed_obj_name = obj_name
        return cls.get_manager(instance_type).get_obj_proxy(parsed_obj_name, support_none=support_none)

    @classmethod
    def find_obj_proxy_from_global(cls,
                                   calling_globals,
                                   full_name,
                                   splitter=None,
                                   instance_type=None,
                                   support_none=False):
        val, found = cls.find_obj_from_global(calling_globals, full_name)
        if found:
            return val
        obj = cls.find_obj_proxy(full_name,
                                 splitter=splitter,
                                 instance_type=instance_type,
                                 support_none=support_none)
        if obj is not None:
            calling_globals[full_name] = obj
            return obj
        raise ImportError('Can not import %s from %s' % (full_name, calling_globals.get('__name__')))

    @classmethod
    def set_manager_default_obj(cls, instance_type, obj):
        cls.get_manager(instance_type).set_default_obj(obj)

    def set_default_obj(self, obj):
        self.set_obj(INSTANCE_DEFAULT_KEY, obj)

    def get_obj_logging_name(self, name):
        logging_name = '(' + name + ')' if name != INSTANCE_DEFAULT_KEY else ''
        return self.instance_type + logging_name

    def set_obj(self, name, obj):
        if name in self.obj_dict:
            self.logger.warn('%s has already been set. Overriding!', self.get_obj_logging_name(name))
        self.obj_dict[name] = obj

    def get_obj(self, name):
        r = self.obj_dict.get(name)
        if not r:
            logging_name = self.get_obj_logging_name(name)
            raise RuntimeError('%s is not inited' % logging_name)
        return r

    def get_obj_proxy(self, name=None, support_none=False):
        name = name or INSTANCE_DEFAULT_KEY
        if support_none:
            return NoopProxy(partial(self.get_obj, name))
        return GeneralProxy(partial(self.get_obj, name))

    def get_obj_proxy_from_global(self,
                                  calling_globals,
                                  full_name,
                                  splitter=None,
                                  support_none=False
                                  ):
        return self.find_obj_proxy_from_global(calling_globals,
                                               full_name,
                                               splitter=splitter,
                                               instance_type=self.instance_type,
                                               support_none=support_none)

    @classmethod
    def find_obj_from_global(cls, calling_globals, full_name):
        if full_name in ['__path__']:
            return None, True
        if full_name in calling_globals:
            return calling_globals[full_name], True
        return None, False
