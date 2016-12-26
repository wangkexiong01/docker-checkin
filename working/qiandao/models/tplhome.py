# -*- coding: utf-8 -*-

from sqlalchemy import sql

from ..extensions import db


class TPLHome(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    originator = db.Column(db.String(128))
    is_public = db.Column(db.Boolean)
    tpl = db.Column(db.Text)
    vars = db.Column(db.Text)

    @staticmethod
    def query_available(user_id):
        return TPLHome.query.filter(sql.or_(TPLHome.originator == 'admin', TPLHome.originator == user_id))

    def get_vars(self):
        if self.vars != '':
            return self.vars.split(',')
        else:
            return []
