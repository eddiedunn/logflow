import pytest
import threading
import requests
import time
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestHealthCheck:
    def test_health_endpoint_healthy(self, tmp_path):
        """Start logflow and verify health endpoint returns healthy status."""
        # Arrange
        server_addr = ('127.0.0.1', 10201)
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        stop_event = threading.Event()
        def server():
            import asyncio
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[DiskSink(str(output_dir))],
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event,
                    health_port=10202
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(1)
        # Act
        resp = requests.get("http://127.0.0.1:10202/health")
        stop_event.set()
        thread.join(timeout=2)
        # Assert
        assert resp.status_code == 200
        assert resp.json().get("status") == "healthy"

    def test_health_endpoint_unhealthy(self, tmp_path):
        """Induce a failure (e.g., S3 unreachable) and verify health endpoint status."""
        # Arrange: Use bogus S3 endpoint
        import os
        os.environ["S3_ENDPOINT"] = "http://127.0.0.1:9991"
        os.environ["S3_ACCESS_KEY"] = "minioadmin"
        os.environ["S3_SECRET_KEY"] = "minioadmin"
        os.environ["S3_BUCKET"] = "logflow-health-unhealthy"
        os.environ["S3_REGION"] = "us-east-1"
        server_addr = ('127.0.0.1', 10203)
        stop_event = threading.Event()
        def server():
            import asyncio
            from logflow.sink import S3Sink
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[S3Sink()],
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event,
                    health_port=10204
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(1)
        # Act
        resp = requests.get("http://127.0.0.1:10204/health")
        stop_event.set()
        thread.join(timeout=2)
        # Assert
        assert resp.status_code == 503 or resp.json().get("status") == "unhealthy", "Health endpoint did not reflect unhealthy state."
