import os
import sys
import time
from logflow.ipc import IPCClient

if __name__ == "__main__":
    sock_path = os.getenv("LOGFLOW_IPC_SOCKET", "/tmp/logflow-listener-test.sock")
    client = IPCClient(sock_path=sock_path)
    try:
        client.connect()
        sys.stdout.flush()
        sys.stderr.flush()
        client.tail()
        sys.stdout.flush()
        sys.stderr.flush()
        # If TAIL_HOLD_OPEN=1, keep the connection open indefinitely
        if os.getenv("TAIL_HOLD_OPEN") == "1":
            print("[tail_client] Holding connection open...")
            sys.stdout.flush()
            while True:
                time.sleep(10)
    except Exception as e:
        print(f"[tail_client] Exception: {e}")
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(1)
