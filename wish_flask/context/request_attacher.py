import six


class RequestAttachRegister(object):

    registry = {}
    priorities = []

    @classmethod
    def do_register(cls, clz, priority=10):
        cls.registry.setdefault(priority, []).append(clz)
        if priority not in cls.priorities:
            cls.priorities.append(priority)
            cls.priorities.sort()

    @classmethod
    def do_auto_attach(cls, request):
        for p in cls.priorities:
            for c in cls.registry[p]:
                c.attach_from_request(request)


class AttacherMeta(type):
    def __init__(cls, name, bases, attrs):
        super(AttacherMeta, cls).__init__(name, bases, attrs)
        if getattr(cls, 'auto_attach', None):
            priority = getattr(cls, 'attach_priority', 10)
            RequestAttachRegister.do_register(cls, priority=priority)


class RequestAttacher(six.with_metaclass(AttacherMeta)):
    auto_attach = False
    attach_priority = 10

    @classmethod
    def attach_from_request(cls, request, **kwargs):
        raise NotImplementedError
