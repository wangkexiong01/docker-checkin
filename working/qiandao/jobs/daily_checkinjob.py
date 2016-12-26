# -*- coding: utf-8 -*-

import Queue
import logging
import random
import time
from datetime import datetime
from threading import Thread

from concurrent.futures import ThreadPoolExecutor
from schedule import Scheduler
from sqlalchemy.orm import sessionmaker

from ..libs.secret_request import XiamiRequest, BanyungongRequest, ZimuzuRequest, PacktRequest
from ..models import XiamiUser, BanyungongUser, ZimuzuUser, PacktUser

logger = logging.getLogger(__name__)

secret_helper = {
    'packtpub': (0, PacktRequest, PacktUser),  # Server in British
    'xiami': (8, XiamiRequest, XiamiUser),  # Server for China
    'banyungong': (8, BanyungongRequest, BanyungongUser),
    'zimuzu': (8, ZimuzuRequest, ZimuzuUser),
}


class DailyCheckinJob(object):
    def __init__(self, db_engine, max_workers=100):
        self.db_engine = db_engine
        self.administration = True

        self.timer = None
        self.scheduler = Scheduler()

        self.commander = ThreadPoolExecutor(max_workers=len(secret_helper) * 2 + 2)
        self.supervisor = {}
        for site in secret_helper:
            self.supervisor[site] = False
        self.process_queue = Queue.Queue()

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.batch = (max_workers - 2) / len(secret_helper)
        self.result_queue = Queue.Queue()

    def start(self):
        minute = '00:15'
        logger.debug('Hourly trigger at %s' % minute)
        self.scheduler.every().hour.at(minute).do(self.renew_waiting)

        t = Thread(target=self.run_schedule)
        t.setName('PeriodSchedule')
        t.setDaemon(True)
        t.start()
        self.timer = t

        t = Thread(target=self.run_wait)
        t.setName('JobAdmin')
        t.setDaemon(True)
        t.start()

    def run_schedule(self):
        while True:
            self.scheduler.run_pending()
            time.sleep(1)

    def run_wait(self):
        time.sleep(60)

        self.executor.submit(self.handle_process_queue)
        self.executor.submit(self.handle_result_queue)

        for site in secret_helper:
            if not self.supervisor[site]:
                self.commander.submit(self.produce, site, action='Retry')
                logger.debug('[%s] Retry accounts not running today ...' % site)

        self.administration = False

    def renew_waiting(self):
        if not self.administration:
            for site in secret_helper:
                if (datetime.utcnow().hour + secret_helper[site][0]) % 24 == 23:
                    self.supervisor[site] = False  # Close thread for today
                    self.commander.submit(self.produce, site)  # Submit new thread for tomorrow
                    logger.debug('[%s] A new day transaction is coming ...' % site)
                else:
                    if not self.supervisor[site]:
                        self.commander.submit(self.produce, site, action='Retry')
                        logger.debug('[%s] Retry accounts that is not OK in previous round ...' % site)
        else:
            logger.debug('Under administration ...')

    def produce(self, site, action='Normal'):
        if action.upper() == 'NORMAL':
            # Waiting for last piece of thread doing this job closed
            # Waiting for site change another day's checkin section
            silence = random.randrange(5 * 60, 10 * 60)
            silence = 0
            logger.debug('Generally delay %s seconds for %s jobs starting ...' % (silence, site))
            time.sleep(silence)
        elif self.supervisor[site]:
            logger.debug('Another thread is working with %s accounts ...' % site)
            return

        session_type = sessionmaker(bind=self.db_engine)
        session = session_type()

        offset = 0
        try:
            self.supervisor[site] = True
            while self.supervisor[site]:
                timezone, _, job_model = secret_helper[site]

                if action.upper() == 'NORMAL':
                    prepare = session.query(job_model).limit(self.batch).offset(offset).all()
                elif action.upper() == 'RETRY':
                    today_begin4checkin = ((int(time.time()) / (24 * 3600)) * 24 * 3600) - timezone * 3600
                    prepare = session.query(job_model).filter(job_model.last_success < today_begin4checkin).limit(
                        self.batch).offset(offset).all()

                total = len(prepare)

                if total > 0:
                    logger.info('[%s] Batch read %s accounts ...' % (site, total))
                    for user in prepare:
                        self.process_queue.put((site, user.account, user.cookie, user.passwd))

                    time.sleep(5)

                if total < self.batch:
                    self.supervisor[site] = False
                else:
                    offset += self.batch
        finally:
            session.close()
            self.supervisor[site] = False
            logger.debug('[%s] Finish scanning records ...' % site)

    def checkin(self, site, account, cookie, password):
        days = None  # Clean result for each request
        expired = False

        _, job_class, _ = secret_helper[site]
        request = job_class()
        try:
            if cookie is not None:
                logger.debug('[%s] Using cookie for %s' % (site, account))
                request.load_cookie(cookie)
                days = request.checkin(cookie)

            if days is None:
                if request._data:
                    expired = True

                if password is not None:  # Try if password stored
                    logger.debug('[%s] Using password for %s' % (site, account))
                    resp = request.login(account, password)
                    if resp is None:
                        logger.debug('[%s] Login with password for %s' % (site, account))
                        days = request.checkin()

            if days is not None:
                cookie = request.dump_cookie()

            self.result_queue.put({
                'site': site,
                'account': account,
                'checkin': days,
                'expired': expired,
                'dump': cookie,
            })

            request.clear_cookie()
        except Exception, e:
            logger.error(e)
            logger.error('Error happened while processing %s user: %s, skip to next...' % (site, account))

    def handle_process_queue(self):
        while True:
            result = self.process_queue.get()
            if result is not None:
                site, account, cookie, password = result
                self.executor.submit(self.checkin, site, account, cookie, password)

    def handle_result_queue(self):
        session_class = sessionmaker(bind=self.db_engine)
        session = session_class()

        while True:
            try:
                result = self.result_queue.get()
                if result is not None:
                    site = result['site']
                    _, _, job_model = secret_helper[site]

                    account = result['account']
                    dump = result['dump']
                    expired = result['expired']
                    days = result['checkin']

                    update_fields = {}
                    if days is not None:
                        update_fields['checkin2'] = job_model.checkin1
                        update_fields['checkin1'] = job_model.checkin0
                        update_fields['checkin0'] = days
                        update_fields['cookie'] = dump
                        update_fields['cookie_inuse'] = job_model.cookie_inuse + 1
                        update_fields['last_success'] = int(time.time())
                        update_fields['day_fails'] = 0
                        update_fields['cont_fails'] = 0
                    else:
                        update_fields['last_fail'] = int(time.time())
                        update_fields['cont_fails'] = job_model.cont_fails + 1

                    if expired:
                        update_fields['cookie_life'] = job_model.cookie_inuse
                        update_fields['cookie_inuse'] = 0

                    session.query(job_model).filter_by(account=account).update(update_fields)
                    session.commit()
                    logger.info('[%s] %s update  DB record ...' % (site, account))
            except Queue.Empty:
                pass
            except Exception, e:
                logger.error(e)
