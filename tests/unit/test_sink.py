import os
import tempfile
from logflow.sink import DiskSink

def test_disk_sink_creates_file_and_writes_batch(tmp_path):
    # Arrange
    output_dir = tmp_path / "logs"
    sink = DiskSink(str(output_dir))
    batch = ["{\"msg\": \"foo\"}", "{\"msg\": \"bar\"}"]
    # Act
    sink.write_batch(batch)
    # Assert
    files = list(output_dir.iterdir())
    assert files, "No file was created by DiskSink."
    content = files[0].read_text().splitlines()
    assert content == ["{\"msg\": \"foo\"}", "{\"msg\": \"bar\"}"], f"Unexpected file content: {content}"

def test_disk_sink_empty_batch_does_nothing(tmp_path):
    output_dir = tmp_path / "logs"
    sink = DiskSink(str(output_dir))
    sink.write_batch([])
    assert not any(output_dir.iterdir()), "DiskSink should not create a file for empty batch."
