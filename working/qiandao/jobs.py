# -*- coding: utf-8 -*-

import logging
import time
from threading import Thread

from .background.checkin import DailyCheckinJob

logger = logging.getLogger(__name__)


def configure_jobs():
    from . import create_app
    from .extensions import db

    app = create_app()

    workers = app.config.get('JOB_THREADS', 100)
    db_engine = db.get_engine(app)

    def delay_start(job):
        time.sleep(60)
        job.start()

    daemon_job = DailyCheckinJob(db_engine, max_workers=workers)
    t = Thread(target=delay_start, args=(daemon_job,))
    t.setName('DelayJob')
    t.setDaemon(True)
    t.start()

