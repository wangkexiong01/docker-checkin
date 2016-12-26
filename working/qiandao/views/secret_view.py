# -*- coding: utf-8 -*-

from flask import Blueprint, request, flash
from flask import current_app as app
from flask.ext.babel import lazy_gettext as __

from ..extensions import db
from ..forms import LoginForm
from ..helper import render
from ..libs import XiamiLogin, BanyungongLogin, ZimuzuLogin, PacktLogin
from ..models import XiamiUser, BanyungongUser, ZimuzuUser, PacktUser

secret = Blueprint('secret', __name__)


@secret.route('/', methods=('GET', 'POST'))
def account_check():
    form = LoginForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            account = form.account.data
            password = form.password.data
            remember = form.remember.data

            work = {
                (XiamiLogin, XiamiUser): form.xiamitype.data,
                (BanyungongLogin, BanyungongUser): form.banyungongtype.data,
                (ZimuzuLogin, ZimuzuUser): form.zimuzutype.data,
                (PacktLogin, PacktUser): form.packtype.data,
            }

            for (job_klass, model_klass), jobstatus in work.items():
                if jobstatus is True:
                    login_request = job_klass(app.logger)
                    user_klass = model_klass

                    result = login_request.login(account, password)
                    cookie = login_request.dump_cookie()

                    if result is None:  # Successful
                        user = user_klass.query.filter_by(account=account).first()
                        if user is None:
                            user = user_klass()
                            user.account = account
                            user.cookie = cookie

                            if remember:
                                user.passwd = password

                            db.session.add(user)
                        else:
                            user.cookie = cookie

                            if remember:
                                user.passwd = password

                        db.session.commit()
                        msg = '%s %s added for daily checkin' % (login_request.tag, account)
                        flash(msg)
                        app.logger.info(msg)
                    else:
                        msg = __("Error: %(originator)s: %(result)s", originator=login_request.tag, result=result)
                        flash(msg)
                        app.logger.info(msg)

    return render('secret/login.html', form=form)
