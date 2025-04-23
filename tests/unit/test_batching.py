import pytest
from logflow.handler import LogBatcher

def test_batcher_add_and_flush():
    batcher = LogBatcher(batch_size=3, batch_time=10)
    batcher.add_log({"msg": "test1"})
    batcher.add_log({"msg": "test2"})
    assert len(batcher.buffer) == 2
    # Simulate flush
    flushed = batcher.flush()
    assert flushed == []  # Not enough logs to flush
    batcher.add_log({"msg": "test3"})
    flushed = batcher.flush()
    assert len(flushed) == 3
    assert flushed[0]["msg"] == "test1"

