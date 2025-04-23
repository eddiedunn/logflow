import os
import socket
import threading
import time
import pytest
import asyncio
import boto3
from logflow.listener import run_logflow_server

@pytest.mark.integration
def test_udp_to_s3(monkeypatch):
    # Arrange: Set env vars for MinIO/S3
    minio_ip = socket.gethostbyname("minio_logflow")
    endpoint = f"http://{minio_ip}:9000"
    print(f"[test] S3_ENDPOINT set to {endpoint}")
    os.environ["S3_ENDPOINT"] = endpoint
    os.environ["S3_ACCESS_KEY"] = "minioadmin"
    os.environ["S3_SECRET_KEY"] = "minioadmin"
    os.environ["S3_BUCKET"] = "logflow-ingest"
    os.environ["S3_REGION"] = "us-east-1"
    server_addr = ('127.0.0.1', 9999)
    received = []
    stop_event = threading.Event()
    def callback(msg):
        received.append(msg)
    def server():
        async def run():
            await run_logflow_server(ip=server_addr[0], port=server_addr[1], sinks=[], received_callback=callback, batch_size_bytes=1, batch_interval=0.1, stop_event=stop_event)
        asyncio.run(run())
    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    time.sleep(0.5)
    # Act: Send UDP packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = b'{"msg": "integration-s3"}'
    sock.sendto(msg, server_addr)
    # Wait for upload (up to 5s)
    print(f"[test] boto3 client using endpoint_url={endpoint}")
    s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin", region_name="us-east-1")
    # Ensure bucket exists
    try:
        s3.create_bucket(Bucket="logflow-ingest")
        print("[test] Created bucket logflow-ingest")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print("[test] Bucket logflow-ingest already exists")
    except Exception as e:
        print(f"[test] Unexpected error creating bucket: {e}")
    found = False
    for _ in range(20):
        resp = s3.list_objects_v2(Bucket="logflow-ingest", Prefix="logs/")
        for obj in resp.get("Contents", []):
            data = s3.get_object(Bucket="logflow-ingest", Key=obj["Key"])["Body"].read().decode()
            if "integration-s3" in data:
                found = True
                break
        if found:
            break
        time.sleep(0.25)
    stop_event.set()
    thread.join(timeout=2)
    assert found, "S3 sink did not receive log batch in MinIO."
