from abc import ABC, abstractmethod
from typing import List
import os
from datetime import datetime

class BaseSink(ABC):
    """
    Abstract base class for all log sinks.
    Implementations must provide write_batch(batch: List[str]).
    """
    @abstractmethod
    def write_batch(self, batch: List[str]):
        pass

class DiskSink(BaseSink):
    """
    Writes batches of logs to disk as JSONL files in a specified directory.
    Each batch is written to a new file with a timestamp and unique identifier.
    """
    def __init__(self, output_dir: str, on_write=None):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.on_write = on_write  # Optional callback for test synchronization

    def write_batch(self, batch: List[str]):
        if not batch:
            return
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"logflow-{ts}.jsonl"
        path = os.path.join(self.output_dir, filename)
        print(f"[DiskSink] Writing batch to {path}")
        with open(path, "w", encoding="utf-8") as f:
            for line in batch:
                f.write(line.rstrip() + "\n")
        if self.on_write:
            self.on_write(path)

class StdoutSink(BaseSink):
    """Echoes each log batch to standard output."""
    def write_batch(self, batch: List[str]):
        if not batch:
            return
        print("[StdoutSink] Log batch:")
        for line in batch:
            print(line)

class TestSink(BaseSink):
    """Test-only sink that appends each batch to a shared list for assertion."""
    def __init__(self, received_batches):
        self.received_batches = received_batches
    def write_batch(self, batch: List[str]):
        if not batch:
            return
        self.received_batches.append(list(batch))
