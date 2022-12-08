import inspect
import logging
from types import ModuleType
from typing import Union, Type, List

from IPython.terminal.embed import InteractiveShellEmbed

from sparrow.base import Sparrow


class VariableCollector(object):
    def __init__(self,
                 package: Union[ModuleType, str],
                 class_types: List[Type] = None,  # None class_types will collect all attrs
                 collect_instance=False,
                 collect_subclasss=False):
        self.package = package
        self.package_name = package if isinstance(package, str) else package.__name__
        self.class_types = class_types
        self.collect_instance = collect_instance
        self.collect_subclass = collect_subclasss
        self.all_var_names = []

    def _collect_attr(self, attr, attr_value, all_vars):
        if self.class_types:
            for clz_type in self.class_types:
                if self.collect_instance and isinstance(attr_value, clz_type):
                    all_vars[attr] = attr_value
                    break
                if self.collect_subclass \
                        and inspect.isclass(attr_value) \
                        and issubclass(attr_value, clz_type) \
                        and attr_value is not clz_type:
                    all_vars[attr] = attr_value
                    break
        else:
            all_vars[attr] = attr_value

    def _collect_module(self, m, all_vars):
        for attr in dir(m):
            if not attr.startswith("__"):
                attr_value = getattr(m, attr)
                self._collect_attr(attr, attr_value, all_vars)

    def collect(self):
        all_vars = {}
        self.all_var_names = list(all_vars.keys())
        return all_vars

    def export_collected_vars(self):
        return self.package_name + ': ' + ', '.join(self.all_var_names)

# ipython shell
def ipshell(app: Sparrow,
            var_collectors: List[VariableCollector] = None,
            log_level=logging.WARN):
    logging.getLogger("parso").setLevel(log_level)
    with app.app_context() as context:
        g = context.g
        ns = locals()

        shell = InteractiveShellEmbed(user_ns=ns)
        shell()
