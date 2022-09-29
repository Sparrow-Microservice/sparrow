from flask import request, current_app
from sparrow.context.base_context import ValueContext
from sparrow.context.request_attacher import RequestAttacher

LOCALE_KEY = 'LOCALE'


class LocaleContext(ValueContext, RequestAttacher):
    stats_key = LOCALE_KEY
    auto_attach = True
    attach_priority = 0

    @classmethod
    def attach_from_request(cls, r, **kwargs):
        locale = cls.parse_locale(r)
        cls.set(locale)

    @classmethod
    def parse_locale(cls, r, default='en'):
        languages = current_app.config.get('LANGUAGES') if current_app else None
        if languages and r:
            return r.accept_languages.best_match(languages)
        return default

    @classmethod
    def get(cls, default=None):
        return super().get() or cls.parse_locale(request, default=default)
