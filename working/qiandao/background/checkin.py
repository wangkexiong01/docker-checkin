# -*- coding: utf-8 -*-

import Queue
import logging
import random
import threading
import time
from datetime import datetime
from string import Template
from threading import Thread

import pytz
from concurrent.futures import ThreadPoolExecutor
from schedule import Scheduler
from sqlalchemy.orm import sessionmaker

from ..libs.secret_request import XiamiRequest, BanyungongRequest, ZimuzuRequest, PacktRequest
from ..models import XiamiUser, BanyungongUser, ZimuzuUser, PacktUser, WebUser

logger = logging.getLogger(__name__)

site_helper = {
    'packtpub': (0, PacktRequest, PacktUser),
    'xiami': (8, XiamiRequest, XiamiUser),
    'zimuzu': (8, ZimuzuRequest, ZimuzuUser),
    'banyungong': (8, BanyungongRequest, BanyungongUser),
}

memo_success = Template(u'''最近签到成功: $success
今日签到记录: $today_checkin
昨日签到记录: $yesterday_checkin
''')
memo_failed = Template(u'''上次失败: $fail
昨日签到记录: $yesterday_checkin
''')


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

        self.administration = {}
        self.status = {}
        for site in site_helper:
            self.administration[site] = True
            self.status[site] = False

        self.db_engine = db_engine

        # Period Schedule
        self.timer = None
        self.scheduler = Scheduler()

        # Query necessary accounts for checkin jobs (Flow Control)
        self.commander = ThreadPoolExecutor(max_workers=2 * len(site_helper) + 2)
        # ThreadPool for checkin jobs running
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # Exclude the thread for handle_process_queue and handle_result_queue
        self.batch = max_workers / len(site_helper)

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
        self.commander.submit(self.handle_process_queue)
        self.commander.submit(self.handle_result_queue)

        logger.debug('Trigger First Retry ...')
        for site in site_helper:
            if not self.check_administration(site):
                self.commander.submit(self.produce, site, action='RETRY')
                self.administration[site] = False

    def renew_waiting(self):
        silence = random.randrange(5 * 60, 10 * 60)

        for site in site_helper:
            if not self.administration[site]:
                if (datetime.utcnow().hour + site_helper[site][0]) % 24 == 0:
                    logger.debug(
                        '[%s] Delay %s seconds to close session for toady and start new session ...' % (site, silence))
                    self.commander.submit(self.produce, site, action='NORMAL', delay=silence)
                else:
                    self.commander.submit(self.produce, site, action='RETRY')
            else:
                logger.debug('[%s] Under administration, skip loading data ...')

    def produce(self, site, action='Normal', delay=0):
        action = action.upper()

        if action == 'NORMAL':
            self.status[site] = False  # Close another thread for today

            # Waiting for last piece of thread doing this job closed
            # Waiting for site to change another day's section
            time.sleep(delay)
        elif self.status[site]:
            logger.debug('[%s] Another thread is working with retried accounts ...' % site)
            return

        session_type = sessionmaker(bind=self.db_engine)
        session = session_type()

        offset = 0
        try:
            self.status[site] = True
            while self.status[site]:
                timezone, _, job_model = site_helper[site]

                if action == 'NORMAL':
                    prepare = session.query(job_model).limit(self.batch).offset(offset).all()
                elif action == 'RETRY':
                    current = int(time.time())
                    today_begin4checkin = (((current + timezone * 3600) / (24 * 3600)) * 24 * 3600) - timezone * 3600
                    prepare = session.query(job_model).filter(job_model.last_success < today_begin4checkin).limit(
                        self.batch).offset(offset).all()

                total = len(prepare)

                if total > 0:
                    logger.info('[%s] Batch read %s accounts ...' % (site, total))
                    for user in prepare:
                        self.process_queue.put((site, user.account, user.cookie, user.passwd, action == 'NORMAL'))

                if total < self.batch:
                    self.status[site] = False
                else:
                    offset += self.batch

                if offset != 0:
                    time.sleep(2)
        finally:
            session.close()
            self.status[site] = False
            logger.debug('[%s] Finish scanning records ...' % site)

    def checkin(self, site, account, cookie, password, day_trigger):
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
                'day_trigger': day_trigger,
            })

            request.clear_cookie()
        except Exception, e:
            logger.error(e)
            logger.info('[%s] Error happened while processing user: %s, skip to next...' % (site, account))

    def check_administration(self, site):
        # TODO: Need to get this from DB
        if self.db_engine and site:
            return False

    def handle_process_queue(self):
        threading.currentThread().name = 'JobQ'
        while True:
            result = self.process_queue.get()
            if result is not None:
                site, account, cookie, password, day_trigger = result
                self.executor.submit(self.checkin, site, account, cookie, password, day_trigger)

    def handle_result_queue(self):
        threading.currentThread().name = 'ResultQ'
        session_class = sessionmaker(bind=self.db_engine)
        session = session_class()

        while True:
            try:
                result = self.result_queue.get()
                if result is not None:
                    site = result['site']
                    timezone, _, job_model = site_helper[site]

                    account = result['account']
                    dump = result['dump']
                    expired = result['expired']
                    days = result['checkin']
                    day_trigger = result['day_trigger']
                    logger.debug('Receive result from %s with %s ...' % (site, account))

                    query = session.query(job_model).filter_by(account=account).first()
                    if query is not None:
                        user_info = session.query(WebUser).filter_by(id=query.owner_id).first()
                        user_tz = 'UTC'
                        if user_info is not None:
                            user_tz = user_info.timezone

                        update_fields = dict()

                        update_fields['checkin0'] = days
                        if day_trigger and query.checkin0:
                            update_fields['checkin1'] = query.checkin0

                        if days is not None:
                            if expired:
                                update_fields['cookie_life'] = query.cookie_inuse
                                update_fields['cookie_inuse'] = 1
                            else:
                                update_fields['cookie_inuse'] = query.cookie_inuse + 1
                                if query.cookie_inuse + 1 > query.cookie_life:
                                    update_fields['cookie_life'] = query.cookie_inuse + 1

                            update_fields['cookie'] = dump
                            update_fields['last_success'] = int(time.time())
                            update_fields['last_fail'] = 0
                            update_fields['day_fails'] = 0
                            update_fields['cont_fails'] = 0

                            update_fields['memo'] = memo_success.safe_substitute(dict(
                                success=datetime.fromtimestamp(update_fields['last_success'],
                                                                        pytz.timezone(user_tz)).isoformat(),
                                today_checkin=update_fields['checkin0'],
                                yesterday_checkin=update_fields['checkin1'] if 'checkin1' in update_fields else '',
                            ))
                        else:
                            if day_trigger:
                                if query.cont_fails > 0:
                                    update_fields['day_fails'] = query.day_fails + 1
                                    update_fields['cont_fails'] = 1

                            update_fields['last_fail'] = int(time.time())
                            update_fields['cont_fails'] = query.cont_fails + 1

                            update_fields['memo'] = memo_failed.safe_substitute(dict(
                                fail=datetime.fromtimestamp(update_fields['last_fail'],
                                                                     pytz.timezone(user_tz)).isoformat(),
                                yesterday_checkin=update_fields['checkin1'] if 'checkin1' in update_fields else '',
                            ))

                        session.query(job_model).filter_by(account=account).update(update_fields)
                        session.commit()
                        logger.debug('[%s] %s update DB record ...' % (site, account))
            except Queue.Empty:
                pass
            except Exception, e:
                logger.error(e)
