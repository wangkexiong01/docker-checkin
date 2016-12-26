# -*- coding:utf-8 -*-

import logging.config
import os

import yaml

# Using OS environment settings
# Generally this is where sensitive information stored ...
########################################################
for x in os.environ.keys():
    if x.startswith('APP_'):
        globals()[x.strip('APP_')] = os.environ.get(x)

# Logging
########################################################
log_config = os.path.dirname(os.path.abspath(__file__)) + os.sep + 'logging.yaml'
logging.config.dictConfig(yaml.load(open(log_config, 'r')))
