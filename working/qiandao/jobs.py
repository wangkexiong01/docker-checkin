# -*- coding: utf-8 -*-

import logging

from .background.checkin import DailyCheckinJob

logger = logging.getLogger(__name__)


def configure_jobs():
    from . import create_app
    from .extensions import db

    app = create_app()

    workers = app.config.get('JOB_THREADS', 100)
    db_engine = db.get_engine(app)

    daemon_job = DailyCheckinJob(db_engine, max_workers=workers)
    daemon_job.start()

    logger.info('Started checkin jobs in thread pool(%s)' % (id(daemon_job)))
