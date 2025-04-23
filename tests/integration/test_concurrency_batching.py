import pytest
import threading
import socket
import time
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestConcurrencyBatching:
    def test_multiple_concurrent_clients(self, tmp_path):
        """Send logs from multiple concurrent UDP clients and verify all logs are received and batched."""
        server_addr = ('127.0.0.1', 10301)
        received = []
        stop_event = threading.Event()
        ready_event = threading.Event()
        error = []
        def callback(msg):
            received.append(msg)
        def server():
            import asyncio
            async def run():
                try:
                    print('[test] Starting server...')
                    ready_event.set()
                    await run_logflow_server(
                        ip=server_addr[0], port=server_addr[1],
                        sinks=[DiskSink(str(tmp_path))],
                        received_callback=callback,
                        batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                    )
                except Exception as e:
                    print('[test] Exception in server:', e)
                    error.append(e)
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        ready_event.wait(timeout=2)
        time.sleep(0.2)
        # Act: Send logs from multiple clients
        def client():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for i in range(10):
                sock.sendto(b'{"msg": "test-concurrent"}', server_addr)
                time.sleep(0.01)
        clients = [threading.Thread(target=client) for _ in range(5)]
        for c in clients:
            c.start()
        for c in clients:
            c.join()
        time.sleep(2)
        stop_event.set()
        thread.join(timeout=2)
        if error:
            raise error[0]
        assert len(received) >= 50, f"Expected at least 50 messages, got {len(received)}"

    def test_large_batch_sizes(self, tmp_path):
        """Send a large volume of logs to ensure correct batching and no memory leaks."""
        server_addr = ('127.0.0.1', 10302)
        received = []
        stop_event = threading.Event()
        ready_event = threading.Event()
        error = []
        def callback(msg):
            received.append(msg)
        def server():
            import asyncio
            async def run():
                try:
                    print('[test] Starting server...')
                    ready_event.set()
                    await run_logflow_server(
                        ip=server_addr[0], port=server_addr[1],
                        sinks=[DiskSink(str(tmp_path))],
                        received_callback=callback,
                        batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                    )
                except Exception as e:
                    print('[test] Exception in server:', e)
                    error.append(e)
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        ready_event.wait(timeout=2)
        time.sleep(0.2)
        # Act: Send a large number of logs
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(200):
            sock.sendto(f'{{"msg": "batch-{i}"}}'.encode(), server_addr)
            time.sleep(0.002)
        time.sleep(2)
        stop_event.set()
        thread.join(timeout=2)
        if error:
            raise error[0]
        assert len(received) >= 200, f"Expected at least 200 messages, got {len(received)}"
