import logging
import socket
import json
import os
from datetime import datetime

class UDPJsonLogHandler(logging.Handler):
    def __init__(self, ip=None, port=None):
        super().__init__()
        self.addr = (
            ip or os.getenv("UDP_LOG_FORWARD_IP", "127.0.0.1"),
            int(port or os.getenv("UDP_LOG_FORWARD_PORT", 9999))
        )
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }
        try:
            self.sock.sendto(json.dumps(log_obj).encode(), self.addr)
        except Exception:
            pass

class LogBatcher:
    """Batch logs by size or count, and flush as needed."""
    def __init__(self, batch_size=10, batch_time=10):
        self.batch_size = batch_size
        self.batch_time = batch_time
        self.buffer = []
        self.last_flush = datetime.utcnow()

    def add_log(self, log):
        self.buffer.append(log)

    def flush(self):
        if len(self.buffer) >= self.batch_size:
            flushed = self.buffer[:]
            self.buffer.clear()
            self.last_flush = datetime.utcnow()
            return flushed
        return []
