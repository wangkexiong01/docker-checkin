# -*- coding: utf-8 -*-

import logging

from .checkin import DailyCheckinJob

logger = logging.getLogger(__name__)


def configure_jobs(app, db_engine):
    workers = app.config.get('JOB_THREADS', 100)

    daemon_job = DailyCheckinJob(db_engine, max_workers=workers)
    daemon_job.start()

    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['daemon_jobs'] = daemon_job
    logger.debug('app(%s) started checkin jobs in thread pool(%s)' % (id(app), id(daemon_job)))
