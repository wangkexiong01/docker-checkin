# -*- coding: utf-8 -*-

import logging

from .daily_checkinjob import DailyCheckinJob

logger = logging.getLogger(__name__)


def configure_jobs(app, db_engine):
    workers = app.config.get('JOB_THREADS', 100)

    daemon_job = DailyCheckinJob(db_engine, max_workers=workers)
    daemon_job.start()

    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['daemon_jobs'] = daemon_job
