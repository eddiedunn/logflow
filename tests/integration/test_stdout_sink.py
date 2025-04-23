import os
import socket
import threading
import time
import pytest
from logflow.listener import run_logflow_server
from logflow.sink import TestSink

@pytest.mark.integration
def test_stdout_sink():
    # No DISK_SINK_DIR or ENABLE_S3_SINK, use TestSink directly for test
    server_addr = ("127.0.0.1", 18080)
    health_port = 18880
    stop_event = threading.Event()
    ready_event = threading.Event()
    error = []
    received_batches = []
    def server():
        import asyncio
        async def run():
            try:
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[TestSink(received_batches)],
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event,
                    health_port=health_port, ready_event=ready_event
                )
            except Exception as e:
                error.append(e)
        asyncio.run(run())
    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    ready_event.wait(timeout=5)
    time.sleep(0.2)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = b'{"msg": "stdout-sink-test"}'
    sock.sendto(msg, server_addr)
    time.sleep(0.5)
    stop_event.set()
    thread.join(timeout=2)
    if error:
        raise error[0]
    non_empty_batches = [b for b in received_batches if b]
    assert any("stdout-sink-test" in str(batch) for batch in non_empty_batches), f"TestSink did not receive log batch. Received: {received_batches}"
