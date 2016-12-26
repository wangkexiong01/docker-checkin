# -*- coding: utf-8 -*-

import json

from flask import Blueprint, request, redirect, url_for

from ..extensions import db
from ..forms import HarForm, CreateTaskForm
from ..helper import render
from ..models import TPLHome, TPLJobs

tpl = Blueprint('tpl', __name__)


@tpl.route('/', methods=('GET', 'POST'))
def har_upload():
    form = HarForm()
    templates = TPLHome.query_available('wkx')

    if request.method == 'POST':
        if form.validate_on_submit():
            content = form.har_file.data
            a = content

    return render('tpl/upload.html', form=form, tpls=templates)


@tpl.route('/<int:tpl_id>/job/', methods=['GET', 'POST'])
def create_job(tpl_id):
    form = CreateTaskForm()

    if request.method == 'GET':
        templates = TPLHome.query_available('wkx')
        variables = ''
        option_id = None

        for template in templates:
            if template.id == tpl_id:
                variables = template.get_vars()
                option_id = tpl_id
                break

        if variables is '' and templates.first() is not None:
            template = templates.first()
            option_id = template.id
            variables = template.get_vars()

        form.tpl.choices = [(template.id, template.name) for template in templates]
        form.tpl.default = option_id if option_id is not None else 0
        form.process()

        return render('tpl/task_new.html', form=form, vars=variables)
    elif request.method == 'POST':
        template = TPLHome.query.filter_by(id=tpl_id).first()
        variables = template.get_vars()
        parameters = {}

        for variable in variables:
            para = 'input-' + variable
            if para in request.values.keys():
                parameters[variable] = request.values[para]

        envs = json.dumps(parameters)

        if not TPLJobs.query_available(tpl_id, envs):
            job = TPLJobs(tpl_id, envs, 'wkx')
            db.session.add(job)
            db.session.commit()

        return redirect(url_for('tpl.har_upload'))


@tpl.route('/<int:tpl_id>/vars/', methods=['GET'])
def tpl_vars(tpl_id):
    template = TPLHome.query.filter_by(id=tpl_id).first()

    if template is None:
        variables = 'foo, bar'
    else:
        variables = template.vars

    variables = variables.split(',')

    return render('tpl/_task_new_vars.html', vars=variables)
