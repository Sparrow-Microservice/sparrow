from sparrow.lib.instance_manager import InstanceManager
from sparrow.utils.convert_utils import to_snake_case
from typing import TypeVar, Type


class ResourceRegister(object):
    registry = {}
    priorities = []

    @classmethod
    def do_register(cls, resource, priority=10):
        cls.registry.setdefault(priority, []).append(resource)
        if priority not in cls.priorities:
            cls.priorities.append(priority)
            cls.priorities.sort()

    @classmethod
    def get_registered_resources(cls):
        resources = []
        for p in cls.priorities:
            resources += cls.registry[p]
        return resources

    @classmethod
    def do_init_all(cls, app=None):
        instances = []
        for c in cls.get_registered_resources():
            ins = c
            if isinstance(ins, type):
                ins = c()
                instances.append(ins)
            if app and hasattr(c, 'init_app'):
                ins.init_app(app)
        for ins in instances:
            ins.post_init()

    @classmethod
    def close(cls):
        for c in cls.get_registered_resources():
            ins = c.singleton()
            ins.before_close()


class BaseResource(object):
    #: Do auto init after import if True
    auto_init = False

    #: The auto_init priority. The lower the value, the higher the priority.
    init_priority = 10

    #: The name of the singleton instance after init.
    #: You can get the instance by InstanceManager.find_obj_proxy(instance_type=singleton_name)
    singleton_name = None

    def __init__(self):
        self.app = None
        if self.singleton_name:
            InstanceManager.get_manager(self.singleton_name).set_default_obj(self)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.auto_init:
            ResourceRegister.do_register(cls, priority=cls.init_priority)
            if not cls.singleton_name:
                cls.singleton_name = to_snake_case(cls.__name__)

    def init_app(self, app):
        self.app = app
        setattr(app, self.singleton_name, self)  # Attach to app directly

    T = TypeVar('T')

    @classmethod
    def singleton(cls: Type[T]) -> T:
        if not cls.auto_init:
            raise Exception("Only auto init can use this function!")

        return InstanceManager.get_manager(cls.singleton_name).get_obj_proxy()

    def post_init(self):
        """
        It will be executed after all resources are inited.
        """
        pass

    def before_close(self):
        """
        It will be executed before destroying it.
        """
        pass