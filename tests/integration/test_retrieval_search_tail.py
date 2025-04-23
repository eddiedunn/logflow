import pytest
import os
import socket
import threading
import time
import shutil
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestRetrievalSearchTail:
    def test_s3_log_retrieval(self, tmp_path, monkeypatch):
        """After logs are written to S3, fetch and validate log content."""
        # This test assumes S3/MinIO is running and accessible.
        # Arrange: Set up S3 environment
        os.environ["S3_ENDPOINT"] = "http://127.0.0.1:9000"
        os.environ["S3_ACCESS_KEY"] = "minioadmin"
        os.environ["S3_SECRET_KEY"] = "minioadmin"
        os.environ["S3_BUCKET"] = "logflow-integration-test"
        os.environ["S3_REGION"] = "us-east-1"
        server_addr = ('127.0.0.1', 10401)
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = b'{"msg": "s3-retrieval-test"}'
        sock.sendto(msg, server_addr)
        time.sleep(2)
        stop_event.set()
        thread.join(timeout=2)
        # Assert: Retrieve from S3
        import boto3
        s3 = boto3.client("s3", endpoint_url="http://127.0.0.1:9000", aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin", region_name="us-east-1")
        found = False
        resp = s3.list_objects_v2(Bucket="logflow-integration-test")
        for obj in resp.get("Contents", []):
            data = s3.get_object(Bucket="logflow-integration-test", Key=obj["Key"])["Body"].read().decode()
            if "s3-retrieval-test" in data:
                found = True
                break
        assert found, "S3 log not found after upload."

    def test_disk_log_retrieval(self, tmp_path):
        """After logs are written to disk, read files and verify log integrity."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10402)
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = b'{"msg": "disk-retrieval-test"}'
        sock.sendto(msg, server_addr)
        file_written = file_written_event.wait(timeout=3)
        stop_event.set()
        thread.join(timeout=2)
        # Assert
        assert file_written, "Disk log file was not written."
        file_path = file_path_holder['path']
        content = open(file_path).read()
        assert "disk-retrieval-test" in content, f"Expected log not found in disk sink: {content}"
        shutil.rmtree(output_dir, ignore_errors=True)

    def test_search_and_tail(self, tmp_path):
        """Test searching for a term and tailing logs in both S3 and disk sinks (if CLI/API exists)."""
        # For now, this test will simulate local disk search/tail.
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10403)
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = b'{"msg": "tail-search-test"}'
        sock.sendto(msg, server_addr)
        file_written = file_written_event.wait(timeout=3)
        stop_event.set()
        thread.join(timeout=2)
        # Search
        assert file_written, "Disk log file was not written for search/tail test."
        file_path = file_path_holder['path']
        with open(file_path) as f:
            lines = f.readlines()
        found = any("tail-search-test" in line for line in lines)
        assert found, f"Expected log not found in search/tail: {lines}"
