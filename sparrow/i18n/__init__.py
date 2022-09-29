import os
CURDIR = os.path.dirname(__file__)
buildin_translations = os.path.join(CURDIR, 'translations')

from flask_babel import _
from flask_babel import lazy_gettext as _l
