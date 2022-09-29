def set_attr_from_config(obj, config: dict, attr: str, key: str = None):
    key = key or attr
    orig = getattr(obj, attr)
    setattr(obj, attr, config.get(key, orig))
