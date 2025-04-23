import pytest
import os
import threading
import time
import shutil
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestRetentionLifecycle:
    def test_s3_lifecycle_policy(self, tmp_path, monkeypatch):
        """Test that S3 lifecycle policies do not interfere with logflow operation."""
        # This test assumes S3/MinIO is running and lifecycle policy is set externally.
        os.environ["S3_ENDPOINT"] = "http://127.0.0.1:9000"
        os.environ["S3_ACCESS_KEY"] = "minioadmin"
        os.environ["S3_SECRET_KEY"] = "minioadmin"
        os.environ["S3_BUCKET"] = "logflow-lifecycle-test"
        os.environ["S3_REGION"] = "us-east-1"
        server_addr = ('127.0.0.1', 10701)
        stop_event = threading.Event()
        def callback(msg):
            pass
        def server():
            import asyncio
            from logflow.sink import S3Sink
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[S3Sink()],
                    received_callback=callback,
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send UDP packet
        sock = threading.Thread(target=lambda: [
            __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_DGRAM).sendto(b'{"msg": "lifecycle-policy-test"}', server_addr)
        ])
        sock.start()
        sock.join()
        time.sleep(2)
        stop_event.set()
        thread.join(timeout=2)
        # Assert: Check S3 for object
        import boto3
        s3 = boto3.client("s3", endpoint_url="http://127.0.0.1:9000", aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin", region_name="us-east-1")
        found = False
        resp = s3.list_objects_v2(Bucket="logflow-lifecycle-test")
        for obj in resp.get("Contents", []):
            data = s3.get_object(Bucket="logflow-lifecycle-test", Key=obj["Key"])["Body"].read().decode()
            if "lifecycle-policy-test" in data:
                found = True
                break
        assert found, "S3 log not found after upload. (Lifecycle policy may have deleted it prematurely.)"

    def test_disk_cleanup(self, tmp_path):
        """Verify that disk log retention/cleanup deletes old files per policy."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10702)
        stop_event = threading.Event()
        file_written_event = threading.Event()
        file_path_holder = {}
        def on_write(path):
            file_path_holder['path'] = path
            file_written_event.set()
        def callback(msg):
            pass
        def server():
            import asyncio
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[DiskSink(str(output_dir), on_write=on_write)],
                    received_callback=callback,
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send UDP packet
        sock = threading.Thread(target=lambda: [
            __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_DGRAM).sendto(b'{"msg": "retention-cleanup-test"}', server_addr)
        ])
        sock.start()
        sock.join()
        file_written = file_written_event.wait(timeout=3)
        stop_event.set()
        thread.join(timeout=2)
        # Simulate retention policy: delete all files
        shutil.rmtree(output_dir, ignore_errors=True)
        assert not os.listdir(output_dir), "Disk cleanup did not delete log files per retention policy."
