# -*- coding: utf-8 -*-
from flask import Flask
from sparrow_flask.blueprints.general import general_bp
from flask_smorest import Api

import typing as t

if t.TYPE_CHECKING:  # pragma: no cover
    from flask import Blueprint


class Sparrow(Flask):

    def __init__(self,
                 *args,
                 **kwargs):
        super(Sparrow, self).__init__(*args, **kwargs)

        self.before_close_funcs = []
        self.before_kill_funcs = []

        self.api: Api = Api()

    def setups(self):
        self._register_buildin_bps()
        self._init_buildin_extensions()

    def _init_buildin_extensions(self):
        self.api.init_app(self)

    def _register_buildin_bps(self):
        self.register_blueprint(general_bp)

    def register_api(self, blueprint: "Blueprint", **options: t.Any) -> None:
        self.api.register_blueprint(blueprint, **options)

    def before_close(self, f):
        """Registers a function to run before the application is close gracefully.
        """
        self.before_close_funcs.append(f)
        return f

    def before_kill(self, f):
        """ Registers a function to run before the application is killed.
        """
        self.before_kill_funcs.append(f)
        return f

    def close(self):
        """ close Wish flask application
        """
        self.logger.info("Wish flask application is closing.")
        try:
            for func in self.before_close_funcs:
                func()
        except Exception as e:
            self.logger.warning(
                "Wish flask application close gracefully failed, err: %s. Next step will run all kill function.",
                str(e))
            self.kill()

    def kill(self):
        """ kill wish flask application
        """
        for func in self.before_kill_funcs:
            func()
