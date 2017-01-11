# -*- coding: utf-8 -*-

from mixins import UserMixin
from ..extensions import db


class BanyungongUser(UserMixin):
    pass


class XiamiUser(UserMixin):
    xiaid = db.Column(db.String(24))


class ZimuzuUser(UserMixin):
    pass


class PacktUser(UserMixin):
    pass
