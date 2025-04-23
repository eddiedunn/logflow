import pytest
import threading
import time
from logflow.listener import run_logflow_server
from logflow.sink import DiskSink

class DummySink:
    def __init__(self):
        self.received = []
    def write_batch(self, batch):
        self.received.append(batch)
    def close(self):
        pass

@pytest.mark.integration
class TestExtensibleSink:
    def test_new_sink_plugin(self, tmp_path):
        """Implement a dummy sink plugin; verify it loads and works with logflow."""
        server_addr = ('127.0.0.1', 10601)
        stop_event = threading.Event()
        dummy_sink = DummySink()
        def callback(msg):
            pass
        def server():
            import asyncio
            async def run():
                await run_logflow_server(
                    ip=server_addr[0], port=server_addr[1],
                    sinks=[dummy_sink],
                    received_callback=callback,
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act
        sock = threading.Thread(target=lambda: [
            __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_DGRAM).sendto(b'{"msg": "dummy-sink-test"}', server_addr)
        ])
        sock.start()
        sock.join()
        time.sleep(0.5)
        stop_event.set()
        thread.join(timeout=2)
        # Assert
        found = any(b"dummy-sink-test" in str(batch) for batch in dummy_sink.received)
        assert found, "Dummy sink did not receive log batch."

    def test_multiple_sinks(self, tmp_path):
        """Configure multiple sinks (disk + dummy); verify logs are delivered to all sinks."""
        output_dir = tmp_path / "logs"
        output_dir.mkdir()
        server_addr = ('127.0.0.1', 10602)
        stop_event = threading.Event()
        file_written_event = threading.Event()
        file_path_holder = {}
        dummy_sink = DummySink()
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
                    sinks=[DiskSink(str(output_dir), on_write=on_write), dummy_sink],
                    received_callback=callback,
                    batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event
                )
            asyncio.run(run())
        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        time.sleep(0.5)
        # Act
        sock = threading.Thread(target=lambda: [
            __import__('socket').socket(__import__('socket').AF_INET, __import__('socket').SOCK_DGRAM).sendto(b'{"msg": "multi-sink-test"}', server_addr)
        ])
        sock.start()
        sock.join()
        file_written = file_written_event.wait(timeout=3)
        stop_event.set()
        thread.join(timeout=2)
        # Assert
        file_path = file_path_holder['path']
        content = open(file_path).read()
        found_disk = "multi-sink-test" in content
        found_dummy = any(b"multi-sink-test" in str(batch) for batch in dummy_sink.received)
        assert found_disk, "Disk sink did not receive log batch."
        assert found_dummy, "Dummy sink did not receive log batch."
