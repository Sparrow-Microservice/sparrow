from collections import defaultdict


def autodict(levels=1, final=dict):
    """
    Create a defaultdict levels deep with the final type specified by final,
    i.e., levels refers to the number of defaultdicts you need.

    """
    if levels < 2:
        return defaultdict(final)
    else:
        return defaultdict(lambda: autodict(levels - 1, final))


class BlackHole(object):
    """
        Nullify all operations on the object

        e.g.
          x = BlackHole('a', 5, b=6)
          x.update_one(set__blah='x').first()
    """

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return BlackHole()

    def __getattr__(self, attr):
        return BlackHole()

    def __setattr__(self, attr, value):
        return


class ReadOnly(object):
    """
        Apply this to an object to make it read-only
        (none of its attributes can be modified)
    """

    def __init__(self, obj):
        self.__dict__['_obj'] = obj

    def __getattr__(self, attr):
        return getattr(self._obj, attr)

    def __setattr__(self, attr, value):
        raise RuntimeError("%s is read-only, cannot setattr '%s' to %s" %
                           (self._obj, attr, value))


def make_read_only(obj):
    return ReadOnly(obj)


class MethodNoop(object):
    """
        Invoking methods of an instance of this class
        will always return None.

        Attributes aren't so nice.
    """

    def __getattr__(self, attr):
        return lambda *args, **kwargs: None


class MethodYesMan(object):
    """
        Invoking methods of an instance of this class
        will always return True.

        Attributes aren't so nice.
    """

    def __getattr__(self, attr):
        return lambda *args, **kwargs: True
