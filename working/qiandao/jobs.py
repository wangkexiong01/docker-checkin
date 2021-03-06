# -*- coding: utf-8 -*-

import logging
import time
from threading import Thread

from .background.checkin import DailyCheckinJob
from .background.notify import DailyReportJob

logger = logging.getLogger(__name__)


def configure_jobs():
    from . import create_app
    from .extensions import db

    app = create_app()

    workers = app.config.get('JOB_THREADS', 100)
    db_engine = db.get_engine(app)

    smtp_configs = list()
    for key in app.config.keys():
        if key.startswith('SMTP_SERVER'):
            suffix = key[11:]
            server = app.config[key]

            if ('SMTP_USERNAME' + suffix) not in app.config:
                continue
            user = app.config['SMTP_USERNAME' + suffix]

            if ('SMTP_PASSWORD' + suffix) not in app.config:
                continue
            password = app.config['SMTP_PASSWORD' + suffix]

            if (server, user, password) not in smtp_configs:
                smtp_configs.append((server, user, password))

    def delay_start(jobs):
        time.sleep(60)
        for each in jobs:
            each.start()

    daemon_job = DailyCheckinJob(db_engine, max_workers=workers)
    report_job = DailyReportJob(db_engine, smtp_configs)

    t = Thread(target=delay_start, args=([daemon_job, report_job],))
    t.setName('DelayJob')
    t.setDaemon(True)
    t.start()
