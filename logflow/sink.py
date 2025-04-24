from abc import ABC, abstractmethod
from typing import List
import os
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import BotoCoreError, NoCredentialsError
except ImportError:
    boto3 = None

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

class S3Sink(BaseSink):
    """S3/MinIO sink for uploading log batches."""
    def __init__(self):
        if boto3 is None:
            raise ImportError("boto3 is required for S3Sink")
        self.cfg = self._get_s3_config()
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.cfg["endpoint_url"],
            aws_access_key_id=self.cfg["aws_access_key_id"],
            aws_secret_access_key=self.cfg["aws_secret_access_key"],
            region_name=self.cfg["region_name"],
        )
        self.last_health = True  # Assume healthy at start

    def _get_s3_config(self):
        return {
            "endpoint_url": os.getenv("S3_ENDPOINT", "http://minio_logflow:9000"),
            "aws_access_key_id": os.getenv("S3_ACCESS_KEY", "minioadmin"),
            "aws_secret_access_key": os.getenv("S3_SECRET_KEY", "minioadmin"),
            "region_name": os.getenv("S3_REGION", "us-east-1"),
            "bucket": os.getenv("S3_BUCKET", "logflow-ingest"),
        }

    def write_batch(self, batch: List[str]):
        if not batch:
            return
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        key = f"logs/{ts}.jsonl"
        data = "\n".join(batch)
        print(f"[S3Sink] Uploading batch to {self.cfg['bucket']}/{key}")
        try:
            self.s3.put_object(Bucket=self.cfg["bucket"], Key=key, Body=data.encode())
            self.last_health = True
        except Exception as e:
            print(f"[S3Sink] Upload failed: {e}")
            self.last_health = False
            raise

    def is_healthy(self):
        # If last upload failed, report unhealthy immediately
        if not self.last_health:
            return False
        try:
            # Try a lightweight S3 op (head_bucket) with a short timeout
            import socket
            import botocore
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(2)
            try:
                self.s3.head_bucket(Bucket=self.cfg["bucket"])
            finally:
                socket.setdefaulttimeout(old_timeout)
            return True
        except Exception as e:
            print(f"[S3Sink] Health check failed: {e}")
            return False
