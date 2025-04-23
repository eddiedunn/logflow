import sys
import logging
import threading
import time
from .handler import UDPJsonLogHandler


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Forward stdin logs to a UDP listener as JSON logs.")
    parser.add_argument("--ip", type=str, default=None, help="Destination IP (default: env or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Destination port (default: env or 9999)")
    args = parser.parse_args()

    logger = logging.getLogger("udp_forward")
    logger.setLevel(logging.INFO)
    logger.addHandler(UDPJsonLogHandler(ip=args.ip, port=args.port))

    def send_ping():
        while True:
            logger.info("[PING] udp_log_forwarder alive")
            time.sleep(30)

    # Send a ping immediately on startup
    logger.info("[PING] udp_log_forwarder started")
    ping_thread = threading.Thread(target=send_ping, daemon=True)
    ping_thread.start()

    for line in sys.stdin:
        logger.info(line.rstrip())

if __name__ == "__main__":
    main()
