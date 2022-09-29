import base64
import errno
import logging
import os.path
import re
import socket
import threading
import time
import uuid
import msgpack
import six
from functools import reduce
from collections import deque
from copy import deepcopy
from datetime import datetime
from logging.handlers import WatchedFileHandler

try:
    # Mongo ObjectId
    from bson import ObjectId
except:
    ObjectId = None

from sparrow.context.request_id_context import RequestTracingIdContext, RequestIdContext
from sparrow.context.session_context import SessionSignContext
from sparrow.context.user_id_context import UserIdContext
from sparrow.log.td.buffer import BackLogBuffer
from sparrow.log.td.error import TreasureDataDiskError
from sparrow.log.td.error import DynamicTableTreasureDataHandlerError
from sparrow.log.td.utils import merge_prefix
from sparrow.log.td.utils import json_encode
from sparrow.monitor.metrics import METRIC_TD_AGENT


class TreasureDataHandler(logging.Handler):

    """
    Logging Handler for Treasure Data Service.

    Requires all records to be valid JSON.

    Double logs everything to disk and also transmits the message
    to the specified td-agent which will forward the data to the
    treasuredata cloud.
    """

    # pylint: disable=unused-argument
    def __init__(
        self,
        host="localhost",
        port=8888,
        database="contextlogic",
        table="default",
        sync=False,  # Seems not used currently
        backup_dir=None,
        max_backlog=10000,  # thresholds to bump if high brubeck.stats_d.td_agent.log_drops values
        flush_size=10,
        agent_timeout=30,
        io_timeout=0.5,
        td_log_ack_to_console=False
    ):

        self.host = host
        self.port = port
        self.database = database
        self.table = table
        self.backup_dir = backup_dir
        self.flush_size = flush_size
        self.td_log_ack_to_console = td_log_ack_to_console

        self.host_type = socket.gethostname()
        if self.host_type:
            # strip instance_id if in hostname
            s_host = self.host_type.split("-")
            if len(s_host) > 2 and re.match(r'^[0-9a-fA-F]+$', s_host[-2]) and re.match(r'^[0-9a-zA-Z]+$', s_host[-1]):
                # for pod name
                self.host_type = "-".join(s_host[:-2])
            elif len(s_host) > 1 and re.match("[a-z|0-9]{8,17}", s_host[-1]):
                self.host_type = "-".join(s_host[:-1])
            else:
                self.host_type = self.host_type.rstrip("0123456789")

        self.max_backlog = max_backlog

        self.backlog = BackLogBuffer(
            max_backup=self.max_backlog,
            wait_time=agent_timeout,
            host_type=self.host_type,
        )
        self.io_handler = _TDAgentIOHandler(
            host,
            port,
            self._ack_callback,
            flush_callback=self._flush_callback,
            io_timeout=io_timeout,
        )

        if backup_dir:
            self.backup_handler = WatchedFileHandler(filename=self.build_filename())
        else:
            self.backup_handler = None

        self._closed = False
        logging.Handler.__init__(self)

    def _get_table(self, record_name):
        return self.table

    def build_filename(self):
        path = os.path.join(
            self.backup_dir, "treasuredata", self.database, self.table
        )
        if not os.path.exists(path):
            os.makedirs(path)

        return "%s/backup.log" % path

    @staticmethod
    def _sanitize_message(msg):
        """
            accepts a list of dicts...expected to be run after
            _flatten_message()

            Currently will change an ObjectId to a str,
            other transformations can go here
        """
        assert isinstance(msg, list), "Must pass me a list of dicts"
        sanitized_msgs = []
        for _dict in msg:
            assert isinstance(_dict, dict), "Must pass me a list of dicts"
            _d = dict(_dict)  # copy to avoid changing original
            for key, value in six.iteritems(_dict):
                if ObjectId and isinstance(value, ObjectId):
                    _d[key] = str(value)
                elif isinstance(value, datetime):
                    _d[key] = str(value)
            sanitized_msgs.append(_d)
        return sanitized_msgs

    @staticmethod
    def _flatten_message(msg):
        """
          recursively flatten values of complex type into separate log entries
          with a reference back to the parent entry
          If a log entry has extra data, _has_extra will be set to 1.
          The _extra_for field of the extra entry will contain the _id of the
          parent log entry, and _extra_name will contain the key name of extra.

          return a list of flattened dictionaries

          eg:
            {   '_id':'12345',
                'dict_key':{'key':'value'},
                'list_key':['l1', 'l2'],
                'list_of_dict_key':[
                    {'d1k1':'d1v1','d1k2':'d1v2'},
                    {'d2k1':'d2v1','d2k2':'d2v2'},
                ],
            }

          Will be flattened to:
          [ {'_id':'12345', '_has_extra':1},
            {'_id':<>, '_extra_for':'12345', '_extra_name':'dict_key',
             '_extra_type':'dict', 'key':'value'},
            {'_id':<>, '_extra_for':'12345', '_extra_name':'list_key',
             '_extra_type':'list', '_extra_list_index':0, 'list_key':'l1'},
            {'_id':<>, '_extra_for':'12345', '_extra_name':'list_key',
             '_extra_type':'list', '_extra_list_index':1, 'list_key':'l2'},
            {'_id':<>, '_extra_for':'12345', '_extra_name':'list_of_dict_key',
             '_extra_type':'list', '_extra_list_index':0,
             'd1k1':'d1v1', 'd1k2':'d1v2'},
            {'_id':<>, '_extra_for':'12345', '_extra_name':'list_of_dict_key',
             '_extra_type':'list', '_extra_list_index':1,
             'd2k1':'d2v1', 'd2k2':'d2v2'}
          ]
        """

        msg = deepcopy(msg)  # copy so we don't modify msg

        if "_id" not in msg:
            msg["_id"] = uuid.uuid4().hex

        flattened_msgs = []
        queue = [msg]
        complex_types = (dict, list, tuple)

        # recursively flatten complex types with bfs
        while queue:
            msg = queue.pop(0)

            # throw away empty complex types
            # pylint: disable=deprecated-lambda
            list(map(
                lambda item: msg.pop(item[0]),
                list(filter(
                    lambda item: isinstance(item[1], complex_types) and not item[1],
                    six.iteritems(msg),
                )),
            ))

            # get list of keys for complex_types
            keys_with_complex_value = list(map(
                lambda item: item[0],
                (item for item in six.iteritems(msg) if isinstance(item[1], complex_types)),
            ))

            def _prepare_extra_entry(results, key):
                complex_value = msg.pop(key)

                if isinstance(complex_value, dict):
                    complex_value["_id"] = uuid.uuid4().hex
                    complex_value["_extra_for"] = msg["_id"]
                    complex_value["_extra_name"] = key
                    complex_value["_extra_type"] = "dict"
                    results.append(complex_value)
                else:
                    for i, list_value in enumerate(complex_value):
                        extra_msg = {
                            "_id": uuid.uuid4().hex,
                            "_extra_for": msg["_id"],
                            "_extra_name": key,
                            "_extra_type": "list",
                            "_extra_list_index": i,
                        }

                        if isinstance(list_value, dict):
                            extra_msg.update(list_value)
                        else:
                            extra_msg[key] = list_value
                        results.append(extra_msg)

                return results

            # remove dict values and push them into the queue
            extra_msgs = reduce(_prepare_extra_entry, keys_with_complex_value, [])
            if extra_msgs:
                msg["_has_extra"] = 1
            else:
                msg["_has_extra"] = 0
            queue.extend(extra_msgs)
            flattened_msgs.append(msg)

        return flattened_msgs

    @classmethod
    def _prepare_contexts(cls, msg_dict):
        def add_context(key, value):
            if value and not msg_dict.get(key):
                msg_dict[key] = value

        add_context('c_request_id', RequestIdContext.get())
        add_context('c_request_tracing_id', RequestTracingIdContext.get())
        add_context('c_session_sign', SessionSignContext.get())
        add_context('c_user_id', UserIdContext.get())

    def emit(self, record):
        try:
            if record.levelno < self.level:
                return

            # TreasureData does not support complex types,
            # only int/double/string, so here we flatten any dictionaries
            # into multiple log entries
            if isinstance(record.msg, dict):
                self._prepare_contexts(record.msg)
                flattened_msgs = self._flatten_message(record.msg)
                msgs = self._sanitize_message(flattened_msgs)
            elif ObjectId and isinstance(record.msg, ObjectId):
                msgs = [{"log_message": str(record.msg)}]
            else:
                msgs = [{"log_message": record.getMessage()}]

            # copy record so it doesn't affect other handlers
            modified_record = logging.makeLogRecord(record.__dict__)

            td_table = self._get_table(record.name)
            for msg in msgs:
                msg["__table__"] = td_table
                msg["__project__"] = self.database
                # pylint: disable=consider-iterating-dictionary
                for k in list(msg.keys()):
                    if msg[k] is None:
                        msg.pop(k, None)

            if self.backup_handler:
                try:
                    for msg in msgs:
                        modified_record.msg = json_encode(msg)

                        # 1. Log the record to a file
                        try:
                            self.backup_handler.handle(modified_record)
                        except Exception:
                            raise TreasureDataDiskError("Error writing to disk")
                except Exception:
                    self.handleError(record)

            try:
                for msg in msgs:
                    self._tcp_emit(record, msg, td_table)
            except Exception:
                self.handleError(record)
        except Exception:
            self.handleError(record)

    def _tcp_emit(self, record, msg, table):
        tag = "td.%s.%s" % (self.database, table)
        m_time = int(record.created)
        if msg.get("time"):
            m_time = int(msg.get("time"))
            msg["time"] = m_time

        m_id = base64.b64encode(uuid.uuid4().bytes)
        option = {"chunk": m_id}

        packet = msgpack.packb([tag, m_time, msg, option], use_bin_type=False)
        self.backlog.add(m_id, packet)

        self._try_flush()

    def _try_flush(self, n=None):
        if n is None:
            n = self.flush_size

        logs = self.backlog.get_logs(n, send=True)
        for l in logs:
            self.io_handler.send(l)

    def _ack_callback(self, packet):
        try:
            msg = msgpack.unpackb(packet, raw=True)
            self.backlog.ack(msg["ack"])
            if self.td_log_ack_to_console:
                logging.debug("td-agent acknowledged log: %s", msg["ack"])
        # catch system error because msgpack has a bug on broken data
        except (ValueError, SystemError, KeyError):
            logging.exception("received invalid ack packet: %s", str(packet))

    def _flush_callback(self):
        # just reconnected, flush everything
        self._try_flush(n=self.max_backlog)

    def close(self):
        if self._closed:
            return

        # try to flush everything before quitting
        self._try_flush(self.max_backlog)

        self.io_handler.stop()
        logging.Handler.close(self)
        self._closed = True

    def __del__(self):
        self.close()


class DynamicTableTreasureDataHandler(TreasureDataHandler):
    """
        The table is not passed in. Instead, it is determined by the name
        of the logger used.

        For example, with root_name = 'project.prod'
        'project.prod.logs' will go to 'logs' table.
        'project.prod.notification.email' will go to 'notification__email'

        If the name does not match the given root or is root exactly with no
        lower levels, then the default is used.

        The backup log will be aggregated under
        /tmp/treasure_data/<database>/_dynamic_table_handler_/backup.log
    """

    def __init__(self, default_table="default", joiner="__", **kwargs):
        if "table" in kwargs:
            raise DynamicTableTreasureDataHandlerError("table argument not supported")

        kwargs["table"] = "_dynamic_table_handler_"

        TreasureDataHandler.__init__(self, **kwargs)

        self.default_table = default_table
        self.joiner = joiner

    def _get_table(self, record_name):
        name_split = record_name.split('.')
        try:
            td_index = name_split.index('td')
        except:
            td_index = len(name_split) - 1
        table = self.joiner.join(name_split[td_index+1:]) or self.default_table
        return table


class _TDAgentIOHandler(object):
    """
        Handles all IO for interaction with the TD Agent in a separate thread
        to avoid blocking logging operations, and to avoid filling the socket
        receive buffer

        io_timeout defines how long the handler will block for reading/writing
        operations, so a shorter period will create more CPU usage in return
        for less lag
    """

    # tcp code copied/adapted from
    # https://github.com/treasure-data/td-logger-python

    # No point to writing/reading more than the default send buf size
    # the actual value is relatively unimportant, but they CANNOT be 0
    MAX_WRITE_SIZE = 212992
    MAX_READ_SIZE = 212992

    # msgpack'ed ACK packets are always 30 bytes (6 overhead + 24 data)
    ACK_PACKET_SIZE = 30

    def __init__(self, host, port, ack_callback, flush_callback=None, io_timeout=0.5):
        self.host = host
        self.port = port
        self.io_timeout = float(io_timeout)
        self.ack_callback = ack_callback
        self.flush_callback = flush_callback

        if self.io_timeout < 0:
            raise ValueError("io_timeout must be non-negative")

        self._write_buf = deque()
        self._write_buf_lock = threading.RLock()

        # no lock as we don't expect it to be accessed by other threads
        self._read_buf = deque()

        self._thread = threading.Thread(target=self._run)
        self._sock = None
        self._iolock = threading.RLock()
        self._started = threading.Event()
        self._stopped = threading.Event()

    # can be called from other threads
    def send(self, packet):
        if self._stopped.is_set():
            return
        if not self._thread.is_alive():
            self.start()
        with self._write_buf_lock:
            self._write_buf.append(packet)

    def start(self):
        self._started.set()
        self._sock = None
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stopped.set()
        if self._started.is_set():
            self._thread.join()
        # the thread may have already died
        self._disconnect()

    def _is_stopped(self):
        return self._started.is_set() and not self._thread.is_alive()

    def _flush(self):
        self._read()
        self._process_acks()
        self._write()

    def _run(self):
        self._started.set()
        self._reconnect()
        while not self._stopped.is_set():
            start = time.time()
            try:
                self._flush()
            except:
                logging.exception("td-agent thread unexpected exception")
                METRIC_TD_AGENT.inc(event='unexpected_exceptions')
            finally:
                # make sure we don't busy loop if there's errors

                # makes sure we don't hang if the time moves backward
                # (i.e. freezegun)
                sleep_time = max(self.io_timeout - max(time.time() - start, 0), 0)
                time.sleep(sleep_time)

        # try to flush one more time when we're exiting
        self._flush()

        self._disconnect()

    def _reconnect(self):
        if self._sock is None:
            self._connect()

            # connection succeeded, flush all
            if self._sock != None:
                if self.flush_callback is not None:
                    logging.info("reconnected to td-agent, flushing all")
                    self.flush_callback()

    def _connect(self):
        with self._iolock:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self.host, self.port))
                self._sock.settimeout(self.io_timeout)
            except socket.error as e:
                self._connection_err(e)

    def _disconnect(self):
        with self._iolock:
            if self._sock == None:
                return
            self._sock.close()
            self._sock = None

            # if we've disconnected reset the buffers, they're useless now
            with self._write_buf_lock:
                self._write_buf = deque()
            self._read_buf = deque()

    # does logging to indicate failure
    def _connection_err(self, err):
        logging.exception("td-agent connection failed: %s", str(err))
        METRIC_TD_AGENT.inc(event='conn_fails')

        self._disconnect()

    def _write(self):
        with self._write_buf_lock:
            self._reconnect()
            while self._write_buf:
                merge_prefix(self._write_buf, self.MAX_WRITE_SIZE)
                try:
                    written = self._write_packet(self._write_buf[0])
                except socket.error:
                    # If a socket.error is raised, then disconnect() has been called
                    # and our _write_buf has been reset. Exit the loop.
                    continue
                if written == len(self._write_buf[0]):
                    self._write_buf.popleft()
                else:
                    # failed to fully write, try again later
                    self._write_buf[0] = self._write_buf[0][written:]
                    break

    # returns the number of bytes fully written
    def _write_packet(self, packet):
        bytes_written = 0
        with self._iolock:
            if not self._sock:
                return bytes_written
            try:
                while bytes_written < len(packet):
                    bytes_written += self._sock.send(packet[bytes_written:])
            except socket.timeout:
                # timed out
                pass
            except socket.error as e:
                # this might be a real error
                if e.errno not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    # we disconnected
                    self._connection_err(e)
                    raise
        return bytes_written

    def _read(self):
        with self._iolock:
            self._reconnect()
            if not self._sock:
                return
            try:
                while True:
                    packet = self._sock.recv(self.MAX_READ_SIZE)
                    if packet:
                        self._read_buf.append(packet)
                    else:
                        # the other side has closed
                        self._connection_err(IOError("Connection closed"))
                        break
            except socket.timeout:
                # timed out
                pass
            except socket.error as e:
                # this might be a real error
                if e.errno not in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    # we disconnected
                    self._connection_err(e)

    def _process_acks(self):
        while self._read_buf:
            merge_prefix(self._read_buf, self.ACK_PACKET_SIZE)
            if len(self._read_buf[0]) < self.ACK_PACKET_SIZE:
                # not enough data yet
                break
            self.ack_callback(self._read_buf[0])
            self._read_buf.popleft()
