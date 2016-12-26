# -*- coding: utf-8 -*-

import threading


class AtomicSet(set):
    def __init__(self, *args, **kwargs):
        self._lock = threading.Lock()
        super(AtomicSet, self).__init__(*args, **kwargs)

    def add(self, elem):
        with self._lock:
            super(AtomicSet, self).add(elem)

    def remove(self, elem):
        with self._lock:
            if super(AtomicSet, self).__contains__(elem):
                super(AtomicSet, self).remove(elem)

    def pop(self):
        with self._lock:
            if self:
                return super(AtomicSet, self).pop()

    def clear(self):
        with self._lock:
            super(AtomicSet, self).clear()
