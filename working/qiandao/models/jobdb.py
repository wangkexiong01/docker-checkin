# -*- coding: utf-8 -*-

import time

from ..extensions import db


class TPLJobs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tpl_id = db.Column(db.Integer)
    owner = db.Column(db.String(128))
    envs = db.Column(db.BLOB)
    ctime = db.Column(db.Integer)
    mtime = db.Column(db.Integer)

    def __init__(self, tpl_id, envs, owner):
        now = time.time()

        self.tpl_id = tpl_id
        self.envs = TPLJobs.encrypt_envs(envs)
        self.owner = owner
        self.ctime = now
        self.mtime = now

    @staticmethod
    def query_available(tpl_id, envs):
        result = TPLJobs.query.filter_by(tpl_id=tpl_id, envs=TPLJobs.encrypt_envs(envs))
        return [i for i in result]

    @staticmethod
    def encrypt_envs(para):
        result = para
        if not isinstance(para, str):
            result = para.__str__()

        # TODO: Add encrypt code here

        return result

    @staticmethod
    def decrypt_envs(para):
        return para
