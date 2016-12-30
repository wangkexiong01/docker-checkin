# -*- coding: utf-8 -*-

from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

__all__ = ['db', 'mail']

db = SQLAlchemy()
mail = Mail()
