# -*- coding: utf-8 -*-

import string
from random import choice
import datetime

from flask import current_app
from flask.ext.themes2 import render_theme_template
from flask_mail import Message

from .extensions import mail


def get_theme():
    return current_app.config.get('THEME', 'default')


def render(template, **context):
    return render_theme_template(get_theme(), template, **context)


def gen_randomkey(length):
    """Generate random key, given a number of characters"""
    chars = string.letters + string.digits + string.punctuation
    return ''.join([choice(chars) for _ in xrange(int(str(length)))])


def send_mail(rcpt, text, header=None):
    from_address = current_app.config.get('MAIL_USERNAME')

    if '@' in from_address and '@' in rcpt:
        msg_title = header
        if header is None:
            today = datetime.datetime.today()
            msg_title = 'checkin %02d/%02d report' % (today.month, today.day)

        try:
            msg = Message(msg_title, sender=('Reporter', from_address), charset='utf-8')
            msg.add_recipient(rcpt)
            msg.body = text
            mail.send(msg)
        except Exception, e:
            current_app.logger.error('Error happened while sending EMAIL: %s' % e)
    else:
        current_app.logger.info('Mail notification disabled...')
        current_app.logger.info('from/to EMAIL address: %s/%s' % (from_address, rcpt))
