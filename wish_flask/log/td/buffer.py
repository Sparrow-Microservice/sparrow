import logging
import threading
import time
import msgpack
from past.builtins import xrange
from collections import deque
from collections import namedtuple
from datetime import datetime

from wish_flask.monitor.metrics import METRIC_TD_AGENT

_BLEntry = namedtuple("_BLEntry", ["id", "last_sent", "record"])


class BackLogBuffer(object):
    """
        Stores log messages until they've been acknowledged by the td-agent.

        max_backup: the maximum number of logs to store before dropping them
        wait_time : the minimum amount of time to wait for td-agent to respond
                    before a log can be resent
    """

    def __init__(self, max_backup=100000, wait_time=2, host_type=None):
        self.to_send = deque()
        self.cooloff = deque()
        self.acked = set()

        self.max_backup = max_backup
        self.wait_time = wait_time
        self.host_type = host_type

        self._backlog_lock = threading.Lock()
        self.last_alert = None

    def add(self, m_id, record, sent=False):
        # sent can be used to indicate we should put it in cooloff first
        with self._backlog_lock:
            if (
                len(self.to_send) + len(self.cooloff) - len(self.acked)
                >= self.max_backup
            ):
                # drop the log, we can't use too much memory
                self._log_dropped(record)
            else:
                if sent:
                    self.cooloff.append(_BLEntry(m_id, int(time.time()), record))
                else:
                    self.to_send.append(_BLEntry(m_id, 0, record))

    def ack(self, m_id):
        with self._backlog_lock:
            self.acked.add(m_id)
            # if we have a lot of acks, clean it out to save memory
            if len(self.to_send) + len(self.cooloff) < len(self.acked) * 2:
                self._clean()

    def _clean(self):
        self._clean_buffer(self.to_send, self.acked)
        self._clean_buffer(self.cooloff, self.acked)
        self.acked = set()

    def _clean_buffer(self, buf, acked):
        num = len(buf)
        for _ in xrange(num):
            # cycle the elements so we don't need to create
            # a new deque
            entry = buf.popleft()
            if entry.id in acked:
                continue
            buf.append(entry)

    # set send to true if the messages will be sent
    def get_logs(self, n, send=False):
        """
            Get a deque of n log records that haven't been acknowledged yet
        """
        with self._backlog_lock:
            # shift over messages that are ready to resend
            ts = int(time.time())
            num_cooloff = 0
            while self.cooloff:
                e = self.cooloff[0]
                if ts - e.last_sent < self.wait_time:
                    break
                self.to_send.append(e)
                self.cooloff.popleft()
                num_cooloff += 1
            if num_cooloff > 0:
                METRIC_TD_AGENT.inc(amount=num_cooloff, event='resent')
            # get the oldest n non-acked messages in O(n) time
            outlog = deque()
            tmp = list()
            while self.to_send and len(outlog) < n:
                e = self.to_send.popleft()
                # not guaranteed to be cleaned
                if e.id in self.acked:
                    self.acked.remove(e.id)
                    continue
                outlog.append(e.record)
                if send:
                    self.cooloff.append(_BLEntry(e.id, ts, e.record))
                else:
                    tmp.append(e)

            self.to_send.extendleft(reversed(tmp))

        return outlog

    def _log_dropped(self, record):
        tag, _, _, _ = msgpack.unpackb(record, raw=True)
        if not self.last_alert:
            self.last_alert = datetime.utcnow()
        if (datetime.utcnow() - self.last_alert).total_seconds() > 15:
            self.last_alert = datetime.utcnow()
            logging.error("td-agent handler backed up, dropping log")
        METRIC_TD_AGENT.inc(event='log_drop', host=self.host_type or '', tag=tag)
