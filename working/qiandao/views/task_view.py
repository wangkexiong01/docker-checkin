# -*- coding: utf-8 -*-

from flask import Blueprint

task = Blueprint('task', __name__)


@task.route('/create', methods=['POST'])
def create_job():
    pass
