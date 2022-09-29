try:
    from wish_mq import MQ
except:
    MQ = None

if MQ:
    from wish_mq import Producer, Worker

    class FlaskMQ(object):
        def __init__(self, app=None, **kwargs):
            self.kwargs = kwargs
            self.app = app
            self.run_args = {}
            if app:
                self.init_app(app)

        def init_app(self, app, **config):
            self.app = app
            self.kwargs.update(config)
            name = self.kwargs.pop('name', None)
            self.run_args = self.kwargs.pop('run_args', {})
            self.kwargs.setdefault('application', app.config.get('service_name'))
            self.kwargs.setdefault('env', app.env)
            super().__init__(**self.kwargs)
            self._set_extention(name)

        def _set_extention(self, name):
            raise NotImplementedError


    class FlaskProducer(FlaskMQ, Producer):
        def _set_extention(self, name):
            if name:
                self.app.extensions.setdefault('mq', {}).setdefault('producer', {})[name] = self


    class FlaskWorker(FlaskMQ, Worker):
        def start(self, queues=None, **run_kwargs):
            return self.Workers.run(queues=queues, **run_kwargs)

        def _set_extention(self, name):
            if name:
                self.app.extensions.setdefault('mq', {}).setdefault('worker', {})[name] = self
else:
    FlaskProducer = None
    FlaskWorker = None
