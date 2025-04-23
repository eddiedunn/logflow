import os
import socket
import threading
import time
import pytest
import asyncio
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
def test_udp_to_disk(tmp_path):
    # Arrange
    server_addr = ('127.0.0.1', 9998)
    output_dir = tmp_path / "logs"
    file_written_event = threading.Event()
    file_path_holder = {}
    def on_write(path):
        file_path_holder['path'] = path
        file_written_event.set()
    received = []
    def callback(msg):
        received.append(msg)

    stop_event = threading.Event()
    def server():
        async def run():
            await run_logflow_server(
                ip=server_addr[0],
                port=server_addr[1],
                sinks=[DiskSink(str(output_dir), on_write=on_write)],
                received_callback=callback,
                batch_size_bytes=1,  # force flush after first message
                batch_interval=0.1,   # flush almost immediately
                stop_event=stop_event
            )
        asyncio.run(run())
    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    time.sleep(0.5)

    # Act: Send UDP packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = b'{"msg": "integration-disk"}'
    sock.sendto(msg, server_addr)

    # Wait for file write event (up to 3s)
    file_written = file_written_event.wait(timeout=3)
    assert file_written, "DiskSink did not write a file within timeout."
    file_path = file_path_holder['path']
    content = open(file_path).read().splitlines()
    assert any("integration-disk" in line for line in content), f"Expected log not found in disk sink: {content}"
    # Always cleanup server thread
    stop_event.set()
    try:
        thread.join(timeout=2)
    except Exception as e:
        print(f"[test_udp_to_disk] Exception during thread join: {e}")
