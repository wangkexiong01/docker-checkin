# -*- coding: utf-8 -*-

from flask.ext.babel import lazy_gettext as __
from flask_wtf import Form
from flask_wtf.file import FileField
from wtforms import SubmitField


class HarForm(Form):
    har_file = FileField(__(u'Upload'))
    submit = SubmitField(__(u'Submit'))
