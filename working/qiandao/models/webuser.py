# -*- coding: utf-8 -*-

import datetime
import time

import pytz

from ..extensions import db


class WebUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ctime = db.Column(db.Integer)

    account = db.Column(db.String(128), index=True, unique=True)
    passwd = db.Column(db.String(24))

    email = db.Column(db.String(64))
    timezone = db.Column(db.String(32))

    prefer = db.Column(db.Integer)
    last = db.Column(db.Integer)

    def __init__(self):
        self.ctime = int(time.time())
        self.timezone = 'Asia/Shanghai'
        self.prefer = 0
        self.last = 0
