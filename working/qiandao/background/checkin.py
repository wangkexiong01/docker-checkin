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

site_helper = {
    'packtpub': (0, PacktRequest, PacktUser),
    'xiami': (8, XiamiRequest, XiamiUser),
    'zimuzu': (8, ZimuzuRequest, ZimuzuUser),
    'banyungong': (9, BanyungongRequest, BanyungongUser),
}


def singleton(klass):
    instances = {}

    def get_instance(*args, **kwargs):
        if klass not in instances:
            return instances.setdefault(klass, klass(*args, **kwargs))
        else:
            return instances[klass]

    get_instance.klass = klass
    return get_instance


@singleton
class DailyCheckinJob(object):
    check_point = '00:00'

    def __init__(self, db_engine, max_workers=100):
        # Mark if background jobs already running
        self.working = False
        # Only after 1st round of running, start period schedule
        self.administration = True
        # Mark if there is already running jobs for the site
        self.supervisor = {}
        for site in site_helper:
            self.supervisor[site] = False

        # Using Flask db_engine to make DB session
        self.db_engine = db_engine

        # Period Schedule
        self.timer = None
        self.scheduler = Scheduler()

        # Query necessary accounts for checkin jobs (Flow Control)
        self.commander = ThreadPoolExecutor(max_workers=len(site_helper) * 2 + 2)
        # ThreadPool for checkin jobs running
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # Exclude the thread for handle_process_queue and handle_result_queue
        self.batch = (max_workers - 2) / len(site_helper)

        self.process_queue = Queue.Queue()
        self.result_queue = Queue.Queue()

    def start(self):
        if self.working:
            logger.debug('The checkin background jobs already started...')
            return

        minute = self.check_point
        logger.debug('Schedule very hour at %s...' % minute)
        self.scheduler.every().hour.at(minute).do(self.renew_waiting)

        t = Thread(target=self.run_schedule)
        t.setName('Schedule')
        t.setDaemon(True)
        t.start()
        self.timer = t

        t = Thread(target=self.run_trigger)
        t.setName('FirstRun')
        t.setDaemon(True)
        t.start()

        logger.info('Started checkin jobs ...')
        self.working = True

    def run_schedule(self):
        while True:
            self.scheduler.run_pending()
            time.sleep(1)

    def run_trigger(self):
        self.executor.submit(self.handle_process_queue)
        self.executor.submit(self.handle_result_queue)

        for site in site_helper:
            if not self.supervisor[site]:
                self.commander.submit(self.produce, site, action='Retry')
                logger.debug('[%s] Trigger those accounts not checkin today ...' % site)

        self.administration = False

    def renew_waiting(self):
        if not self.administration:
            for site in site_helper:
                if (datetime.utcnow().hour + site_helper[site][0]) % 24 == 0:
                    self.commander.submit(self.produce, site)  # Submit new thread for tomorrow
                else:
                    if not self.supervisor[site]:
                        self.commander.submit(self.produce, site, action='Retry')
        else:
            logger.debug('Under administration ...')

    def produce(self, site, action='Normal'):
        if action.upper() == 'NORMAL':
            self.supervisor[site] = False  # Close another thread for today

            # Waiting for last piece of thread doing this job closed
            # Waiting for site to change another day's section
            silence = random.randrange(5 * 60, 10 * 60)
            logger.debug('[%s] Delay %s seconds to close session for toady and start new session ...' % (site, silence))
            time.sleep(silence)
        elif self.supervisor[site]:
            logger.debug('[%s] Another thread is working with retried accounts ...' % site)
            return

        session_type = sessionmaker(bind=self.db_engine)
        session = session_type()

        offset = 0
        try:
            self.supervisor[site] = True
            while self.supervisor[site]:
                timezone, _, job_model = site_helper[site]

                if action.upper() == 'NORMAL':
                    prepare = session.query(job_model).limit(self.batch).offset(offset).all()
                elif action.upper() == 'RETRY':
                    current = int(time.time())
                    today_begin4checkin = ((current + timezone * 3600 / (24 * 3600)) * 24 * 3600) - timezone * 3600
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

        _, job_class, _ = site_helper[site]
        request = job_class()
        try:
            if cookie is not None:
                logger.debug('[%s] Using cookie for %s' % (site, account))
                days = request.checkin(cookie)

                if days is None and 'error' not in request.result:
                    expired = True

            if request.result is None or expired is True:
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
            logger.error('[%s] Error happened while processing user: %s, skip to next...' % (site, account))

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
                    _, _, job_model = site_helper[site]

                    account = result['account']
                    dump = result['dump']
                    expired = result['expired']
                    days = result['checkin']
                    logger.debug('Receive result from %s with %s ...' % (site, account))

                    update_fields = {}
                    if days is not None:
                        update_fields['cookie'] = dump
                        update_fields['cookie_inuse'] = job_model.cookie_inuse + 1
                        update_fields['last_success'] = int(time.time())
                        update_fields['last_fail'] = 0
                        update_fields['day_fails'] = 0
                        update_fields['cont_fails'] = 0
                    else:
                        update_fields['last_fail'] = int(time.time())
                        update_fields['cont_fails'] = job_model.cont_fails + 1

                    update_fields['checkin2'] = job_model.checkin1
                    update_fields['checkin1'] = job_model.checkin0
                    update_fields['checkin0'] = days

                    if expired:
                        update_fields['cookie_life'] = job_model.cookie_inuse
                        update_fields['cookie_inuse'] = 0

                    session.query(job_model).filter_by(account=account).update(update_fields)
                    session.commit()
                    logger.debug('[%s] %s update DB record ...' % (site, account))
            except Queue.Empty:
                pass
            except Exception, e:
                logger.error(e)
