# -*- coding: utf-8 -*-

from flask.ext.babel import lazy_gettext as __

from flask_wtf import Form
from wtforms import SelectField, SubmitField

# Some fields need to know
name = __(u'username')


class CreateTaskForm(Form):
    tpl = SelectField(u'Templates')
    submit = SubmitField(__(u'Submit'))
