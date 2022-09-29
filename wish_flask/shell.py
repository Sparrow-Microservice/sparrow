import inspect
import logging
from types import ModuleType
from typing import Union, Type, List

from IPython.terminal.embed import InteractiveShellEmbed

from wish_flask.application.wish_application import WishFlaskApplication
from wish_flask.lib.instance_manager import InstanceManager
from wish_flask.utils.import_utils import import_submodules


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
        modules = import_submodules(self.package)
        for m in modules.values():
            self._collect_module(m, all_vars)
        self.all_var_names = list(all_vars.keys())
        return all_vars

    def export_collected_vars(self):
        return self.package_name + ': ' + ', '.join(self.all_var_names)


class IpShellVarHelper(object):

    @classmethod
    def get_all_managed_instances(cls):
        return InstanceManager.find_all_objects(splitter='_')

    @classmethod
    def get_all_collected_vars(cls, var_collectors):
        all_vars = {}
        if var_collectors:
            for c in var_collectors:
                all_vars.update(c.collect())
        return all_vars

    @classmethod
    def get_mongo_tools(cls):
        from wish_flask.extensions.mongo.shell_utils import pp, d
        tools = [pp, d]
        return {t.__name__: t for t in tools}


class IpShellBannerHelper(object):
    @classmethod
    def get_collected_var_banner(cls, var_collectors):
        banners = ['All extra collected vars:']
        if var_collectors:
            for c in var_collectors:
                banners.append(c.export_collected_vars())
        if len(banners) > 1:
            return '\n  '.join(banners)
        return ''

    @classmethod
    def get_managed_instance_banner(cls):
        objs = IpShellVarHelper.get_all_managed_instances()
        objs = list(objs.keys())
        if objs:
            banners = ['All app loaded vars:', ', '.join(objs)]
            return '\n  '.join(banners)
        return ''

    @classmethod
    def get_mongo_tools_banner(cls):
        objs = IpShellVarHelper.get_mongo_tools()
        if objs:
            banners = ['All mongo tools:', ', '.join(objs.keys())]
            return '\n  '.join(banners)
        return ''

    @classmethod
    def get_banner(cls, var_collectors, app):
        banners = [
            '***Welcome to %s shell***\n' % app.config.get('service_name', 'Wish Flask'),
            IpShellBannerHelper.get_managed_instance_banner(),
            IpShellBannerHelper.get_collected_var_banner(var_collectors),
            IpShellBannerHelper.get_mongo_tools_banner(),
            '\nPlease type %who to get all pre-loaded variables.',
            '       type <name>? to get description of target.',
            'Please refer to https://ipython.readthedocs.io/en/stable/interactive/tutorial.html '
            'for IPython tutorial.\n',
            'Running env: ' + app.env
        ]
        return '\n'.join(banners)


# ipython shell
def ipshell(app: WishFlaskApplication,
            var_collectors: List[VariableCollector] = None,
            log_level=logging.WARN):
    logging.getLogger("parso").setLevel(log_level)
    with app.app_context() as context:
        g = context.g
        ns = locals()
        ns.update(IpShellVarHelper.get_all_managed_instances())
        ns.update(IpShellVarHelper.get_all_collected_vars(var_collectors))
        ns.update(IpShellVarHelper.get_mongo_tools())
        banner = IpShellBannerHelper.get_banner(var_collectors, app)

        shell = InteractiveShellEmbed(user_ns=ns, banner2=banner)
        shell()
