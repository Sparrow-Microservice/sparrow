# -*- coding: utf-8 -*-
from flask import Flask
from sparrow_flask.blueprints.general import general_bp
from sparrow_flask.base.scaffold import Scaffold
from flask_smorest import Api
import marshmallow as ma
import typing as t

from sparrow_flask.base import Blueprint
from flask.scaffold import T_route
from flask.app import ft


class Sparrow(Flask, Scaffold):
    _blp: "Blueprint" = None

    def __init__(self,
                 *args,
                 **kwargs):
        super(Sparrow, self).__init__(*args, **kwargs)

        self.before_close_funcs = []
        self.before_kill_funcs = []

        self.api: Api = Api()
        self._is_register_blp = False
        self._api_ready = False

    def setups(self):
        self._register_buildin_bps()
        self._init_buildin_extensions()

    def _init_buildin_extensions(self):
        self.api.init_app(self)
        self._api_ready = True

    def _register_buildin_bps(self):
        self.register_blueprint(general_bp)
        self.__class__._blp = Blueprint(self.config['service_name'], __name__)

    def register_route(self, blueprint: "Blueprint", **options: t.Any) -> None:
        options.setdefault("_from_blp", True)
        self.api.register_blueprint(blueprint, **options)

    @classmethod
    def arguments(cls, data_clz, *args, **kwargs):
        return cls._blp.arguments(data_clz, *args, **kwargs)

    @classmethod
    def response(
            cls, status_code=200, data_clz=None, *, description=None,
            example=None, examples=None, headers=None, base_schema=ma.Schema
    ):
        return cls._blp.response(status_code, data_clz, description=description, example=example, examples=examples,
                                 headers=headers, base_schema=base_schema)

    def route(self, rule: str, **options: t.Any) -> t.Callable[[T_route], T_route]:
        return self.__class__._blp.route(rule, **options)

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

    def run(
            self,
            host: t.Optional[str] = None,
            port: t.Optional[int] = None,
            debug: t.Optional[bool] = None,
            load_dotenv: bool = True,
            **options: t.Any,
    ) -> None:
        # Need register blueprint before run
        if not self._is_register_blp:
            self.register_route(self.__class__._blp)
            self._is_register_blp = True
        super(Sparrow, self).run(host, port, debug, load_dotenv, **options)
