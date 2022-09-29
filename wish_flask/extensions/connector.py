from wish_flask.utils.import_utils import import_string


class Connector(object):
    @classmethod
    def connect(cls, app, ext, config=None):
        if config.get('enabled'):
            if not cls.dependency_check():
                raise RuntimeError(
                    'Please check whether the package and dependencies are installed: '
                    '%s' % ext)
            cls.do_connect(app, config=config)

    @classmethod
    def dependency_check(cls):
        raise NotImplementedError("Please implement dependency_check for %s", cls.__name__)

    @classmethod
    def do_connect(cls, app, config=None):
        raise NotImplementedError('Please implement do_connect for %s', cls.__name__)

    @classmethod
    def connect_all(cls, app, config=None):
        config = config or app.config
        extensions = config.get('extensions', {})
        for ext in extensions:
            target_connector = cls.__module__.rsplit('.', 1)[0] + '.' + ext + '.connect.connector'
            target_connector = import_string(target_connector)
            target_connector.connect(app, ext, config=extensions[ext])
