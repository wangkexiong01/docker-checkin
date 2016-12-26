# -*- coding: utf-8 -*-

import logging
import sys
import threading
import time

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


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
class Timer(object):
    def __init__(self, param=10, start=True):
        if isinstance(param, int) and param > 1:
            workers = param
        elif isinstance(param, ThreadPoolExecutor):
            workers = param._max_workers
        else:
            workers = 10

        self.workers = workers
        self.executor = None
        self.tick_thread = None

        self.index = None
        self.ttable = dict()
        self.ttable_lock = threading.Lock()
        self.running = False
        self.precision = 1000

        if start:
            self.start()

    def start(self):
        if not self.running:
            self.running = True
            self.executor = ThreadPoolExecutor(max_workers=self.workers)
            self.tick_thread = threading.Thread(target=self.run)
            self.tick_thread.setDaemon(True)
            self.tick_thread.start()

        logger.info('Timer is running ......')

    def stop(self):
        if self.running:
            self.running = False

            self.executor.shutdown()
            self.tick_thread = None
            self.executor = None

    def allocate(self, expire, callback=None):
        if expire <= 0 or self.running is False:
            return None

        with self.ttable_lock:
            if self.index is None:
                self.index = 0
            else:
                while True:
                    self.index = (self.index + 1) % sys.maxint
                    if self.index not in self.ttable:
                        break

            self.ttable[self.index] = {
                'delta': 0,
                'expire': int(expire * self.precision),
                'callback': callback,
            }

            logger.info('Allocate Timer ID: %s' % self.index)
            return self.index

    def cancel(self, timer_id, callback=None):
        with self.ttable_lock:
            if timer_id in self.ttable:
                if callback is not None:
                    self.executor.submit(callback)

                self.release_timer(timer_id)
                logger.info('Cancel Timer ID: %s' % timer_id)
                return True
            else:
                logger.info('Already Timeout for ID: %s' % timer_id)
                return False

    def run(self):
        delta = 1

        while self.running:
            timestamp = int(time.time() * self.precision)

            time.sleep(1.0 / self.precision)
            expire = []

            with self.ttable_lock:
                for each in self.ttable:
                    if each in self.ttable:
                        if self.check(self.ttable[each], delta, each):
                            expire.append(each)

                for timer_id in expire:
                    self.release_timer(timer_id)

            delta = int(time.time() * self.precision) - timestamp

        logger.info('Timer is stopped ......')

    def release_timer(self, timer_id):
        logger.debug('......Timer Remove ID: %s' % timer_id)
        self.ttable.pop(timer_id)

    def check(self, timer_data, delta, timer_id):
        timer_data['delta'] += delta

        if timer_data['delta'] >= timer_data['expire']:
            logger.debug('......Timer Timeout for ID: %s' % timer_id)
            if timer_data['callback'] is not None:
                self.executor.submit(timer_data['callback'])

            return True

        return False
