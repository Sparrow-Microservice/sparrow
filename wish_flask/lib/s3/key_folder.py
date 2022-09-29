from wish_flask.lib.py_enum import PyEnumMixin


class KeyFolder(str):

    @classmethod
    def get_key_with_folder(cls, key, folder_name):
        return "%s/%s" % (folder_name, key)

    def key(self, key_name):
        return self.get_key_with_folder(key_name, self)


class KeyFolderEnum(PyEnumMixin):

    def __init_subclass__(cls, **kwargs):
        cls._build_cache()

    @classmethod
    def attr_check(cls, attr, attr_value):
        if isinstance(attr_value, str):
            v = KeyFolder(attr_value)
            setattr(cls, attr, v)
            return v
        return attr_value
