# -*- coding: utf-8 -*-

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

__all__ = ['db', 'mail']

db = SQLAlchemy()
mail = Mail()
