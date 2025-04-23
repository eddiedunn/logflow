import asyncio
import os
import json
import time
import uuid
from datetime import datetime
from typing import List
from .sink import BaseSink, DiskSink

try:
    import boto3
    from botocore.exceptions import BotoCoreError, NoCredentialsError
except ImportError:
    boto3 = None

# Configurable parameters (env or defaults)
UDP_IP = os.getenv("UDP_LOG_LISTEN_IP", "0.0.0.0")
UDP_PORT = int(os.getenv("UDP_LOG_LISTEN_PORT", 9999))
BATCH_SIZE_BYTES = int(os.getenv("UDP_BATCH_SIZE_BYTES", 1024 * 1024))  # 1MB
BATCH_INTERVAL = int(os.getenv("UDP_BATCH_INTERVAL", 60))  # 60 seconds

def get_s3_config():
    endpoint = os.getenv("S3_ENDPOINT", "http://minio_logflow:9000")
    print(f"[listener:get_s3_config] S3_ENDPOINT={endpoint}")
    return {
        "endpoint_url": endpoint,
        "aws_access_key_id": os.getenv("S3_ACCESS_KEY", "minioadmin"),
        "aws_secret_access_key": os.getenv("S3_SECRET_KEY", "minioadmin"),
        "region_name": os.getenv("S3_REGION", "us-east-1"),
        "bucket": os.getenv("S3_BUCKET", "logflow-ingest"),
    }

async def udp_server(batch_queue: asyncio.Queue):
    print(f"[listener] Listening for UDP logs on {UDP_IP}:{UDP_PORT}")
    loop = asyncio.get_running_loop()
    sock = asyncio.DatagramProtocol()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPHandler(batch_queue),
        local_addr=(UDP_IP, UDP_PORT)
    )
    try:
        await asyncio.Future()  # run forever
    finally:
        transport.close()

class UDPHandler(asyncio.DatagramProtocol):
    def __init__(self, batch_queue, received_callback=None):
        self.batch_queue = batch_queue
        self.received_callback = received_callback
    def datagram_received(self, data, addr):
        try:
            msg = data.decode()
            self.batch_queue.put_nowait(msg)
            if self.received_callback:
                self.received_callback(msg)
        except Exception as e:
            print(f"[listener] Failed to decode UDP packet: {e}")

async def batch_and_upload(batch_queue: asyncio.Queue, sinks, batch_size_bytes, batch_interval, stop_event=None):
    batch: List[str] = []
    batch_bytes = 0
    last_flush = time.time()
    while not (stop_event and stop_event.is_set()):
        try:
            msg = await asyncio.wait_for(batch_queue.get(), timeout=1)
            print(f"[batch_and_upload] Got message: {msg}")
            batch.append(msg)
            batch_bytes += len(msg.encode())
        except asyncio.TimeoutError:
            pass
        now = time.time()
        if batch and (batch_bytes >= batch_size_bytes or now - last_flush >= batch_interval):
            print(f"[batch_and_upload] Flushing batch: {batch}")
            for sink in sinks:
                print(f"[batch_and_upload] Writing to sink: {sink}")
                sink.write_batch(batch)
            try:
                await upload_batch(batch)
            except Exception as e:
                print(f"[batch_and_upload] upload_batch error: {e}")
            batch.clear()
            batch_bytes = 0
            last_flush = now

async def upload_batch(batch: List[str]):
    if not batch:
        return
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    key = f"logs/{ts}-{uuid.uuid4().hex}.jsonl"
    data = "\n".join(batch)
    print(f"[listener] Uploading batch: {key} ({len(batch)} logs, {len(data)} bytes)")
    if boto3 is None:
        print("[listener] boto3 not installed, skipping S3 upload.")
        return
    cfg = get_s3_config()
    print(f"[listener:upload_batch] boto3 endpoint_url={cfg['endpoint_url']}")
    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint_url"],
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
        region_name=cfg["region_name"],
    )
    try:
        s3.put_object(Bucket=cfg["bucket"], Key=key, Body=data.encode())
        print(f"[listener] Uploaded batch to {cfg['bucket']}/{key}")
    except (BotoCoreError, NoCredentialsError) as e:
        print(f"[listener] S3 upload failed: {e}")

async def health_check_server():
    from aiohttp import web
    async def handle(request):
        return web.Response(text="OK")
    app = web.Application()
    app.router.add_get("/healthz", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("[listener] Health check endpoint running on :8080/healthz")

async def run_logflow_server(ip=None, port=None, sinks=None, received_callback=None, batch_size_bytes=None, batch_interval=None, stop_event=None):
    batch_queue = asyncio.Queue()
    if sinks is None:
        sinks = []
    if batch_size_bytes is None:
        batch_size_bytes = BATCH_SIZE_BYTES
    if batch_interval is None:
        batch_interval = BATCH_INTERVAL
    udp_task = asyncio.create_task(
        udp_server_with_callback(batch_queue, ip, port, received_callback, stop_event)
    )
    batch_task = asyncio.create_task(
        batch_and_upload(batch_queue, sinks, batch_size_bytes, batch_interval, stop_event)
    )
    health_task = asyncio.create_task(health_check_server())
    await asyncio.gather(udp_task, batch_task, health_task)

async def main():
    sinks = []
    disk_dir = os.getenv("DISK_SINK_DIR")
    if disk_dir:
        sinks.append(DiskSink(disk_dir))
    await run_logflow_server(sinks=sinks)

def start_udp_server(batch_queue=None, ip=None, port=None, received_callback=None, stop_event=None):
    """Convenience wrapper to start the UDP server for testing/integration, supports stop_event for clean shutdown."""
    import asyncio
    if batch_queue is None:
        batch_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    async def run_server():
        await udp_server_with_callback(batch_queue, ip, port, received_callback, stop_event)
    loop.create_task(run_server())
    return batch_queue

def udp_server_with_callback(batch_queue, ip, port, received_callback, stop_event=None):
    # Helper for testable UDP server
    async def inner():
        nonlocal ip, port
        ip = ip or UDP_IP
        port = port or UDP_PORT
        print(f"[listener] Listening for UDP logs on {ip}:{port}")
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPHandler(batch_queue, received_callback),
            local_addr=(ip, port)
        )
        try:
            while not (stop_event and stop_event.is_set()):
                await asyncio.sleep(0.1)
        finally:
            transport.close()
    return inner()

if __name__ == "__main__":
    try:
        import aiohttp  # Ensure aiohttp is available for health check
    except ImportError:
        print("[listener] Please install aiohttp for health check endpoint: pip install aiohttp")
        exit(1)
    asyncio.run(main())
