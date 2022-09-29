from flask_babel import Babel
from wish_flask.i18n import buildin_translations
from wish_flask.context.locale_context import LocaleContext


class WishBabel(Babel):
    def init_app(self, app):
        trans_dir = app.config.get('BABEL_TRANSLATION_DIRECTORIES') or 'translations'
        trans_dir += ';' + buildin_translations
        app.config.set('BABEL_TRANSLATION_DIRECTORIES', trans_dir)
        super().init_app(app)
        self.locale_selector_func = self.get_locale

    def get_locale(self):
        return LocaleContext.get(default='en')
