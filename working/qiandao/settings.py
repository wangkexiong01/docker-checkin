# -*- coding: utf-8 -*-

"""
Default configurations
"""

from .helper import gen_randomkey

# Debug
DEBUG = False

# Logger
# If this one appear in logging config file,
#    handlers will be remove by flask and generate a new one.
LOGGER_NAME = 'flask_default'

# WTF Secret
SECRET_KEY = gen_randomkey(24)
CSRF_SESSION_KEY = gen_randomkey(24)

# Theme
THEME = 'default'

# Mail
MAIL_SERVER = ''
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_DEBUG = False
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
