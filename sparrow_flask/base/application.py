# -*- coding: utf-8 -*-
from flask import Flask
from sparrow_flask.blueprints.general import general_bp


class Sparrow(Flask):

    def __init__(self,
                 *args,
                 **kwargs):
        """WishFlaskApplication

        :param name: The name of the application package.
        :param import_modules: A list of strings or modules.
            All listed modules will be automatically imported for resource collection.
        :param args: flask args
        :param kwargs: flask kwargs
        """
        super(Sparrow, self).__init__(*args, **kwargs)

        self.before_close_funcs = []
        self.before_kill_funcs = []

        self.setups()

    def setups(self):
        self._register_buildin_bps()

    def _register_buildin_bps(self):
        self.register_blueprint(general_bp)

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
