# -*- coding: utf-8 -*-

from flask import Blueprint
from flask.ext.babel import gettext as _

import logging

logger = logging.getLogger(__name__)

root = Blueprint('root', __name__)


@root.route('/')
def hello():
    logger.debug('test')
    return _('Hello World!')
