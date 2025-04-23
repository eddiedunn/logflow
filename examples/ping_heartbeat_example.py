import logging
import time
from udp_log_forwarder.handler import UDPJsonLogHandler

logger = logging.getLogger("heartbeat_example")
logger.setLevel(logging.INFO)
logger.addHandler(UDPJsonLogHandler(ip="192.168.11.96", port=9999))

logger.info("[PING] Example script started")

try:
    while True:
        logger.info("[PING] heartbeat alive")
        time.sleep(30)
except KeyboardInterrupt:
    logger.info("[PING] Example script stopped by user")
