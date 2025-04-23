import asyncio
import os
import json
import time
import uuid
from datetime import datetime
from typing import List
from .sink import BaseSink, DiskSink, StdoutSink
import socket

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
HEALTH_CHECK_PORT = int(os.getenv("LOGFLOW_HEALTH_PORT", 8080))  # Now configurable

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

async def udp_server(batch_queue: asyncio.Queue, ready_event=None):
    print(f"[listener] Preparing to listen for UDP logs on {UDP_IP}:{UDP_PORT}")
    loop = asyncio.get_running_loop()
    sock = asyncio.DatagramProtocol()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPHandler(batch_queue),
        local_addr=(UDP_IP, UDP_PORT)
    )
    if ready_event:
        ready_event.set()
        print(f"[listener] UDP server is READY on {UDP_IP}:{UDP_PORT}")
    try:
        await asyncio.Future()  # run forever
    finally:
        transport.close()

class UDPHandler(asyncio.DatagramProtocol):
    def __init__(self, batch_queue, received_callback=None):
        self.batch_queue = batch_queue
        self.received_callback = received_callback
    def datagram_received(self, data, addr):
        print(f"[UDPHandler] datagram_received called from {addr}")
        try:
            msg = data.decode()
            print(f"[UDPHandler] Received datagram from {addr}: {msg}")
            self.batch_queue.put_nowait(msg)
            if self.received_callback:
                print(f"[UDPHandler] Calling received_callback with: {msg}")
                self.received_callback(msg)
        except Exception as e:
            print(f"[listener] Failed to decode UDP packet: {e}")

async def batch_and_upload(batch_queue: asyncio.Queue, sinks, batch_size_bytes, batch_interval, stop_event=None):
    batch: List[str] = []
    batch_bytes = 0
    last_flush = time.time()
    enable_s3 = os.getenv("ENABLE_S3_SINK", "").lower() in ("1", "true", "yes")
    while not (stop_event and stop_event.is_set()):
        try:
            msg = await asyncio.wait_for(batch_queue.get(), timeout=1)
            print(f"[batch_and_upload] Got message from queue: {msg}")
            batch.append(msg)
            batch_bytes += len(msg.encode())
        except asyncio.TimeoutError:
            pass
        now = time.time()
        if batch and (batch_bytes >= batch_size_bytes or now - last_flush >= batch_interval):
            print(f"[batch_and_upload] Flushing batch: {batch}")
            for sink in sinks:
                print(f"[batch_and_upload] Writing to sink: {sink}")
                if batch:
                    print(f"[batch_and_upload] About to call sink.write_batch with: {batch}")
                    sink.write_batch(batch)
            if enable_s3:
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
    except Exception as e:
        print(f"[listener] S3 upload failed: {e}")
        raise

async def health_check_server(port=None):
    from aiohttp import web
    async def handle(request):
        return web.Response(text="OK")
    app = web.Application()
    app.router.add_get("/healthz", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port or HEALTH_CHECK_PORT)
    await site.start()
    print(f"[listener] Health check endpoint running on :{port or HEALTH_CHECK_PORT}/healthz")

async def udp_server_with_callback(batch_queue, ip, port, received_callback, stop_event=None, ready_event=None):
    bind_ip = ip if ip else UDP_IP  # Use default UDP_IP if not provided
    bind_port = port if port is not None else UDP_PORT  # Use default UDP_PORT if not provided
    print(f"[listener] Preparing to listen for UDP logs on {bind_ip}:{bind_port}")
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPHandler(batch_queue, received_callback),
        local_addr=(bind_ip, bind_port),
        family=socket.AF_INET
    )
    sockname = transport.get_extra_info('sockname')
    sock = transport.get_extra_info('socket')
    if sock:
        print(f"[listener] UDP socket info: sockname={sockname}, family={sock.family}, type={sock.type}, proto={sock.proto}")
    else:
        print(f"[listener] UDP socket info: sockname={sockname}, NO RAW SOCKET")
    if ready_event:
        ready_event.set()
    try:
        while not (stop_event and stop_event.is_set()):
            await asyncio.sleep(0.1)
    finally:
        transport.close()

async def run_logflow_server(ip=None, port=None, sinks=None, received_callback=None, batch_size_bytes=None, batch_interval=None, stop_event=None, health_port=None, ready_event=None):
    batch_queue = asyncio.Queue()
    if sinks is None:
        sinks = []
    if batch_size_bytes is None:
        batch_size_bytes = BATCH_SIZE_BYTES
    if batch_interval is None:
        batch_interval = BATCH_INTERVAL
    # Always use defaults if ip/port not provided
    ip = ip if ip is not None else UDP_IP
    port = port if port is not None else UDP_PORT
    udp_task = asyncio.create_task(
        udp_server_with_callback(batch_queue, ip, port, received_callback, stop_event, ready_event)
    )
    batch_task = asyncio.create_task(
        batch_and_upload(batch_queue, sinks, batch_size_bytes, batch_interval, stop_event)
    )
    health_task = asyncio.create_task(health_check_server(health_port))
    await asyncio.gather(udp_task, batch_task, health_task)

async def main():
    sinks = []
    disk_dir = os.getenv("DISK_SINK_DIR")
    enable_s3 = os.getenv("ENABLE_S3_SINK", "").lower() in ("1", "true", "yes")
    if disk_dir:
        sinks.append(DiskSink(disk_dir))
    else:
        sinks.append(StdoutSink())
    if enable_s3:
        # S3Sink import and config, only if ENABLE_S3_SINK is set
        try:
            from .sink import S3Sink
            sinks.append(S3Sink())
        except ImportError:
            print("[listener] S3Sink not available (boto3 missing or not implemented)")
    await run_logflow_server(sinks=sinks)

def main_entrypoint():
    try:
        import aiohttp  # Ensure aiohttp is available for health check
    except ImportError:
        print("[listener] Please install aiohttp for health check endpoint: pip install aiohttp")
        exit(1)
    import asyncio
    asyncio.run(main())

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

if __name__ == "__main__":
    main_entrypoint()
