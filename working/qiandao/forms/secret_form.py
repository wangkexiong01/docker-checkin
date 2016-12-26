# -*- coding: utf-8 -*-

from flask.ext.babel import lazy_gettext as __

from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, StopValidation


class AccountTypeRequired(object):
    field_flags = ('required',)

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if form.xiamitype.data is False and form.banyungongtype.data is False \
                and form.zimuzutype.data is False and form.packtype.data is False:
            if self.message is None:
                message = __(u'Plz select at least one type')
            else:
                message = self.message

            field.errors[:] = []
            raise StopValidation(message)


class LoginForm(Form):
    account = StringField(__(u'Account'), validators=[DataRequired(__(u'This field is required'))])
    password = PasswordField(__(u'Password'), validators=[DataRequired(__(u'This field is required'))])
    remember = BooleanField(__(u'I can save password in DB'))
    xiamitype = BooleanField(u'Xiami')
    banyungongtype = BooleanField(u'Banyungong')
    packtype = BooleanField(u'PacktPub')
    zimuzutype = BooleanField(u'Zimuzu', validators=[AccountTypeRequired()])
    submit = SubmitField(__(u'Add My Account'))
