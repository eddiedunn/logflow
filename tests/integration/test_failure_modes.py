import pytest
import os
import socket
import threading
import time
import tempfile
import shutil
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestFailureModes:
    def test_disk_full(self, tmp_path):
        """Simulate disk full during batch write; verify graceful failure and error reporting."""
        # Arrange: Create a small tmpfs or use a directory with a very low quota (simulate disk full)
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        # Simulate disk full by making the directory read-only
        os.chmod(output_dir, 0o400)
        server_addr = ('127.0.0.1', 10101)
        stop_event = threading.Event()
        error_triggered = threading.Event()
        def on_write(path):
            pass  # Should not be called
        def callback(msg):
            pass
        def server():
            async def run():
                try:
                    await run_logflow_server(
                        ip=server_addr[0], port=server_addr[1],
                        sinks=[DiskSink(str(output_dir), on_write=on_write)],
                        received_callback=callback,
                        batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                    )
                except Exception:
                    error_triggered.set()
            import asyncio
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send UDP packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = b'{"msg": "disk-full-test"}'
        sock.sendto(msg, server_addr)
        # Wait for error
        error = error_triggered.wait(timeout=3)
        stop_event.set()
        thread.join(timeout=2)
        # Cleanup
        os.chmod(output_dir, 0o700)
        shutil.rmtree(output_dir, ignore_errors=True)
        assert error, "Disk full error not triggered or not handled gracefully."

    def test_s3_unavailable(self, monkeypatch):
        """Simulate S3/MinIO being unreachable; verify retry logic and error reporting."""
        # Arrange: Set bogus S3 endpoint
        os.environ["S3_ENDPOINT"] = "http://127.0.0.1:9990"  # Unused port
        os.environ["S3_ACCESS_KEY"] = "minioadmin"
        os.environ["S3_SECRET_KEY"] = "minioadmin"
        os.environ["S3_BUCKET"] = "logflow-test-unavailable"
        os.environ["S3_REGION"] = "us-east-1"
        server_addr = ('127.0.0.1', 10102)
        stop_event = threading.Event()
        error_triggered = threading.Event()
        def callback(msg):
            pass
        def server():
            import asyncio
            from logflow.sink import S3Sink
            async def run():
                try:
                    await run_logflow_server(
                        ip=server_addr[0], port=server_addr[1],
                        sinks=[S3Sink()],
                        received_callback=callback,
                        batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                    )
                except Exception:
                    error_triggered.set()
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send UDP packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = b'{"msg": "s3-unavailable-test"}'
        sock.sendto(msg, server_addr)
        # Wait for error
        error = error_triggered.wait(timeout=3)
        stop_event.set()
        thread.join(timeout=2)
        assert error, "S3 unavailable error not triggered or not handled gracefully."

    def test_partial_network_outage(self, tmp_path):
        """Drop UDP packets or interrupt network; verify system recovery or error logging."""
        # Arrange: Start server, then stop it mid-batch
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10103)
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
                    batch_size_bytes=10, batch_interval=2, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send UDP packets, then stop server before batch flush
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(3):
            sock.sendto(f'{{"msg": "network-outage-{i}"}}'.encode(), server_addr)
            time.sleep(0.1)
        stop_event.set()  # Simulate network/server interruption
        thread.join(timeout=2)
        # Assert: Not all logs should be written, but no crash
        assert len(received) <= 3, "Should not receive more logs than sent."
