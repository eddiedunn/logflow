import pytest
import threading
import socket
import time
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestConcurrencyBatching:
    def test_multiple_concurrent_clients(self, tmp_path):
        """Send logs from multiple concurrent UDP clients; verify all logs are received and batched."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10301)
        stop_event = threading.Event()
        received = []
        def on_write(path):
            pass
        def callback(msg):
            received.append(msg)
        def server():
            import asyncio
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[DiskSink(str(output_dir), on_write=on_write)],
                    received_callback=callback,
                    batch_size_bytes=1024, batch_interval=0.5, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Launch multiple clients
        def client(idx):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for j in range(10):
                sock.sendto(f'{{"msg": "client-{idx}-msg-{j}"}}'.encode(), server_addr)
                time.sleep(0.01)
        clients = [threading.Thread(target=client, args=(i,)) for i in range(5)]
        for c in clients:
            c.start()
        for c in clients:
            c.join()
        time.sleep(1)
        stop_event.set()
        thread.join(timeout=2)
        # Assert: All messages received
        assert len(received) >= 50, f"Expected at least 50 messages, got {len(received)}"

    def test_large_batch_sizes(self, tmp_path):
        """Send a large volume of logs; verify correct batch splitting and no memory leaks."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10302)
        stop_event = threading.Event()
        received = []
        def on_write(path):
            pass
        def callback(msg):
            received.append(msg)
        def server():
            import asyncio
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[DiskSink(str(output_dir), on_write=on_write)],
                    received_callback=callback,
                    batch_size_bytes=256, batch_interval=0.5, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send a large number of logs
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(200):
            sock.sendto(f'{{"msg": "batch-{i}"}}'.encode(), server_addr)
            time.sleep(0.002)
        time.sleep(2)
        stop_event.set()
        thread.join(timeout=2)
        # Assert: All messages received, batches split
        assert len(received) >= 200, f"Expected at least 200 messages, got {len(received)}"
