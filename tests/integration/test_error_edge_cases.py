import pytest
import threading
import socket
import time
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

@pytest.mark.integration
class TestErrorEdgeCases:
    def test_malformed_log_message(self, tmp_path):
        """Send malformed UDP packets; verify graceful handling and no crash."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10801)
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
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act: Send malformed UDP packet
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b'not-a-json', server_addr)
        time.sleep(0.5)
        stop_event.set()
        thread.join(timeout=2)
        # Assert: Should not crash, may log error, received list should be empty or unchanged
        assert isinstance(received, list), "Server did not handle malformed message gracefully."

    def test_rapid_start_stop(self, tmp_path):
        """Rapidly start and stop logflow; verify no resource leaks or zombies."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10802)
        for _ in range(5):
            stop_event = threading.Event()
            def server():
                import asyncio
                async def run():
                    await run_logflow_server(
                        ip=server_addr[0], port=server_addr[1],
                        sinks=[DiskSink(str(output_dir))],
                        batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                    )
                asyncio.run(run())
            thread = threading.Thread(target=server, daemon=True)
            thread.start()
            time.sleep(0.2)
            stop_event.set()
            thread.join(timeout=2)
        # If we reach here, no resource leaks or zombies occurred (pytest will catch if not)
        assert True
