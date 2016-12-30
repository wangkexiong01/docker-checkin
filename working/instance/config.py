# -*- coding:utf-8 -*-

import os

PRJ_ROOT = os.path.dirname(os.path.abspath(__file__))

# DB
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/../database/qiandao.db' % PRJ_ROOT
SQLALCHEMY_TRACK_MODIFICATIONS = True

# Using OS environment settings
# Generally this is where sensitive information stored ...
########################################################
for x in os.environ.keys():
    if x.startswith('APP_'):
        globals()[x.strip('APP_')] = os.environ.get(x)
