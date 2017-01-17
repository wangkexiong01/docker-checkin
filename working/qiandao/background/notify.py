# -*- coding: utf-8 -*-

import datetime
import logging
import time
from threading import Thread

from concurrent.futures import ThreadPoolExecutor
from schedule import Scheduler, CancelJob
from sqlalchemy.orm import sessionmaker

from .checkin import site_helper
from ..libs.mail import MailSMTPPool
from ..models import WebUser

logger = logging.getLogger(__name__)


class DailyReportJob(object):
    def __init__(self, db_engine, smtp_configs):
        self.scheduler = Scheduler()
        self.timer = None

        self.db_engine = db_engine

        self.pool = MailSMTPPool()
        for server, user, password in smtp_configs:
            self.pool.add_resource(server, user, password)

        self.administration = False
        self.monitor = {0: False, 1: False}
        self.waiting = 0
        self.executor = ThreadPoolExecutor(max_workers=2)

    def start(self):
        x = datetime.datetime.now()
        time_str = '%s:%s' % (x.hour, (x.minute / 15 + 1) * 15 % 60)
        self.scheduler.every().day.at(time_str).do(self.start_schedule)

        t = Thread(target=self.run_schedule)
        t.setName('SchedRpt')
        t.setDaemon(True)
        t.start()
        self.timer = t

    def run_schedule(self):
        while True:
            self.scheduler.run_pending()
            time.sleep(1)

    def start_schedule(self):
        logger.info('Schedule Email Report Job every 15 minutes ...')
        self.scheduler.every(15).minutes.do(self.renew_waiting)
        return CancelJob

    def renew_waiting(self):
        if self.pool.total == 0:
            self.administration = True

        if not self.administration:
            self.executor.submit(self.send_report, self.waiting)
            self.waiting = (self.waiting + 1) % 2

    def send_report(self, running):
        self.monitor[running] = False
        self.monitor[(running + 1) % 2] = True

        session_type = sessionmaker(bind=self.db_engine)
        session = session_type()

        current = int(time.time())
        try:
            for user in session.query(WebUser).filter(WebUser.prefer > 0, current >= WebUser.prefer).all():
                if self.monitor[running]:
                    break

                if user.email is not None and user.email != '':
                    logger.debug('Send Report for %s' % user.account)

                    info = u''
                    for site in site_helper:
                        _, _, job_model = site_helper[site]
                        for query in session.query(job_model).filter_by(owner_id=user.id).all():
                            info += query.memo

                    self.pool.send(user.email, info)
                    session.query(WebUser).filter_by(id=user.id).update({'last': int(time.time())})
        finally:
            session.close()
