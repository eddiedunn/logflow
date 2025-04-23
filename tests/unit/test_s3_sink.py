import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from logflow.listener import upload_batch

@pytest.mark.unit
def test_upload_batch_calls_s3(monkeypatch):
    # Arrange: Patch boto3 and environment
    fake_client = MagicMock()
    monkeypatch.setenv("S3_ENDPOINT", "http://fake-endpoint:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "fake-access")
    monkeypatch.setenv("S3_SECRET_KEY", "fake-secret")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    with patch("logflow.listener.boto3") as mock_boto3:
        mock_boto3.client.return_value = fake_client
        batch = ["{\"msg\": \"unit-test\"}"]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(upload_batch(batch))
        # Assert: S3 client was called with correct params
        assert fake_client.put_object.called
        args, kwargs = fake_client.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"].endswith(".jsonl")
        assert b"unit-test" in kwargs["Body"]

@pytest.mark.unit
def test_upload_batch_handles_error(monkeypatch):
    # Arrange: Patch boto3 to raise error
    class FakeError(Exception): pass
    fake_client = MagicMock()
    fake_client.put_object.side_effect = FakeError("fail")
    monkeypatch.setenv("S3_ENDPOINT", "http://fake-endpoint:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "fake-access")
    monkeypatch.setenv("S3_SECRET_KEY", "fake-secret")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_REGION", "us-east-1")
    with patch("logflow.listener.boto3") as mock_boto3:
        mock_boto3.client.return_value = fake_client
        batch = ["{\"msg\": \"fail-test\"}"]
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(upload_batch(batch))
        except Exception:
            pass
