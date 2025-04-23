import asyncio
import socket
import threading
import time
import pytest
from logflow.listener import start_udp_server
from logflow.handler import LogBatcher

@pytest.mark.integration
def test_udp_flow(tmp_path):
    # Start UDP server in background
    server_addr = ('127.0.0.1', 9999)
    received = []
    def callback(msg):
        import json
        received.append(json.loads(msg))

    stop_event = threading.Event()
    def server():
        async def run():
            start_udp_server(ip=server_addr[0], port=server_addr[1], received_callback=callback, stop_event=stop_event)
            await asyncio.sleep(1.5)  # Keep server alive for test duration
        asyncio.run(run())
    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    time.sleep(0.5)  # Allow server to start

    # Send UDP packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = b'{"msg": "integration-test"}'
    sock.sendto(msg, server_addr)
    time.sleep(1)

    # Check if received
    assert received
    assert received[0]["msg"] == "integration-test"
    # Always cleanup server thread
    stop_event.set()
    try:
        thread.join(timeout=2)
    except Exception as e:
        print(f"[test_udp_flow] Exception during thread join: {e}")
