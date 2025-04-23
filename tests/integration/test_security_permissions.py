import pytest
import os
import threading
import time
import stat
import shutil
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestSecurityPermissions:
    def test_s3_permissions(self, tmp_path, monkeypatch):
        """Run with restricted S3 credentials; verify graceful failure and clear errors."""
        # Set invalid S3 credentials
        os.environ["S3_ENDPOINT"] = "http://127.0.0.1:9000"
        os.environ["S3_ACCESS_KEY"] = "invalid"
        os.environ["S3_SECRET_KEY"] = "invalid"
        os.environ["S3_BUCKET"] = "logflow-security-test"
        os.environ["S3_REGION"] = "us-east-1"
        server_addr = ('127.0.0.1', 10901)
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
        sock = threading.Thread(target=lambda: [
            __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_DGRAM).sendto(b'{"msg": "s3-permission-test"}', server_addr)
        ])
        sock.start()
        sock.join()
        time.sleep(1)
        stop_event.set()
        thread.join(timeout=2)
        # Assert: Should trigger error
        assert error_triggered.is_set(), "S3 permission error not triggered or not handled gracefully."

    def test_file_permissions(self, tmp_path):
        """Run with restricted disk permissions; verify correct error handling."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        # Remove write permission
        os.chmod(output_dir, stat.S_IREAD)
        server_addr = ('127.0.0.1', 10902)
        stop_event = threading.Event()
        error_triggered = threading.Event()
        def on_write(path):
            pass
        def callback(msg):
            pass
        def server():
            import asyncio
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
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send UDP packet
        sock = threading.Thread(target=lambda: [
            __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_DGRAM).sendto(b'{"msg": "file-permission-test"}', server_addr)
        ])
        sock.start()
        sock.join()
        time.sleep(1)
        stop_event.set()
        thread.join(timeout=2)
        # Cleanup permissions
        os.chmod(output_dir, stat.S_IWRITE | stat.S_IREAD)
        shutil.rmtree(output_dir, ignore_errors=True)
        # Assert: Should trigger error
        assert error_triggered.is_set(), "Disk permission error not triggered or not handled gracefully."
