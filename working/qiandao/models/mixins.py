# -*- coding: utf-8 -*-

import time

from ..extensions import db


class UserMixin(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer)
    ctime = db.Column(db.Integer)

    account = db.Column(db.String(128), index=True, unique=True)
    passwd = db.Column(db.String(24))

    cookie = db.Column(db.String(1024))
    cookie_inuse = db.Column(db.Integer)
    cookie_life = db.Column(db.Integer)

    last_success = db.Column(db.Integer)
    last_fail = db.Column(db.Integer)
    day_fails = db.Column(db.Integer)
    cont_fails = db.Column(db.Integer)

    checkin0 = db.Column(db.String(512))
    checkin1 = db.Column(db.String(512))

    memo = db.Column(db.String(512))

    def __init__(self):
        self.ctime = int(time.time())
        self.cookie_inuse = 0
        self.cookie_life = 0
        self.last_success = 0
        self.last_fail = 0
        self.day_fails = 0
        self.cont_fails = 0

    def __repr__(self):
        return 'account = %s;last_success = %s;checkin0 = %s' % (self.account, self.last_success, self.checkin0)
