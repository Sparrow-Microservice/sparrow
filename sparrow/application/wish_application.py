# -*- coding: utf-8 -*-
from flask import Flask


class WishFlaskApplication(Flask):
    def __init__(self,
                 name: str,
                 *args,
                 **kwargs):
        """WishFlaskApplication

        param name: The name of the application package.
        param args: flask args
        param kwargs: flask kwargs
        """
        super(WishFlaskApplication, self).__init__(name, *args, **kwargs)

        self.before_close_funcs = []
        self.before_kill_funcs = []

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
        for func in self.before_kill_funcs:
            func()
