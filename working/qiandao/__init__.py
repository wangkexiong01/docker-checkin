# -*- coding: utf-8 -*-

import json
import os
import re

from flask import Flask, Blueprint, request
from flask.ext.babel import Babel
from flask.ext.themes2 import Themes

import views
from .extensions import db, mail
from .libs.flask_util_js import FlaskUtilJs
from .models import TPLHome


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('%s.settings' % __name__)
    app.config.from_pyfile('config.py', silent=True)

    configure_logging(app)
    configure_extensions(app)

    configure_dispatch(app)
    configure_context_processors(app)

    return app


def configure_logging(app):
    # Fix: If using logging system. This should be set.
    # Otherwise, after app.debug set/resetting. Parent with default formatter will be in working.
    app.logger.propagate = False
    app.logger.handlers = []


def configure_extensions(app):
    configure_i18n(app)
    db.init_app(app)
    mail.init_app(app)
    Themes(app, app_identifier=__name__)
    FlaskUtilJs(app)


def configure_i18n(app):
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        accept_languages = app.config.get('ACCEPT_LANGUAGES', ['en_US', 'zh_CN', 'zh_TW', 'ja_JP'])
        return request.accept_languages.best_match(accept_languages)


def configure_dispatch(app):
    for name, cls in views.__dict__.items():
        if isinstance(cls, Blueprint):
            url_prefix = '/' + name if name != 'root' else '/'
            app.register_blueprint(cls, url_prefix=url_prefix)


def configure_context_processors(app):
    pass


def import_data():
    check_dir = os.path.dirname(os.path.abspath(__file__)) + os.sep + '/uploads'

    tpls = {k.name: k for k in TPLHome.query.all()}
    for f in os.listdir(check_dir):
        if f.endswith('.har') and f[:-4] not in tpls:
            new = TPLHome()
            new.name = f[:-4].decode('utf-8')
            new.originator = 'admin'
            new.is_public = True
            new.tpl = open(check_dir + os.sep + f).read().decode('utf-8')
            result = re.findall('(?<={{)[^}]*(?=}})', json.dumps(json.loads(new.tpl)[0]))
            new.vars = ','.join([y[:y.find('|')].strip() for y in result])

            db.session.add(new)

    db.session.commit()
