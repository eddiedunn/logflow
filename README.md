# logflow

A lightweight, production-grade Python package and containerized stack for UDP log forwarding and collection—with batching, async processing, and S3/MinIO integration.

## Features
- UDP log forwarder (Python logging handler & CLI)
- UDP log collector (async listener, batch uploader)
- Batching and JSONL output
- S3/MinIO batch sink (with project-unique container name: `minio_logflow`)
- Health check endpoint
- Easy Docker Compose deployment

## Quickstart

### 1. Run with Docker Compose (MinIO + Listener)
```sh
docker-compose up --build
```
- Starts a dedicated MinIO instance (`minio_logflow`) and the async logflow listener.
- Listener receives logs on UDP port 9999, batches them (1MB or 60s), uploads to the `logflow-ingest` bucket in MinIO.
- Health check: [http://localhost:8080/healthz](http://localhost:8080/healthz)

### 2. Send Logs to the Listener
```sh
echo '{"event": "test", "msg": "hello world"}' | nc -u -w1 localhost 9999
```
Or use the Python logging handler or CLI forwarder.

### 3. Access Logs in MinIO
- Visit [http://localhost:9003](http://localhost:9003) (login: minioadmin/minioadmin)
- Download `.jsonl` log batches from the `logflow-ingest` bucket.

---

## Standalone Listener (No Docker)

You can use logflow with or without S3/MinIO storage:

### Option 1: S3/MinIO Storage (bring your own endpoint)
- Set `ENABLE_S3_SINK=1` to enable S3/MinIO upload. All S3 connection variables must also be set.
- You must provide your own S3-compatible endpoint (MinIO, AWS S3, etc).
- This can be a MinIO server running locally, in a VM, or in the cloud.
- Set the following environment variables to point to your S3/MinIO:

```sh
export ENABLE_S3_SINK=1
export S3_ENDPOINT=http://localhost:9000   # or your S3/MinIO URL
export S3_ACCESS_KEY=...
export S3_SECRET_KEY=...
export S3_BUCKET=logflow-ingest
```
- Then start the listener:
```sh
python -m logflow.listener
```

#### Running MinIO Locally (without Docker Compose)
- Download MinIO from https://min.io/download
- Start MinIO:
  ```sh
  minio server /data --console-address :9003
  ```
- Access the MinIO web console at [http://localhost:9003](http://localhost:9003)
- Use `minioadmin`/`minioadmin` as default credentials

### Option 2: Local Disk Storage Only (no S3/MinIO)
- Set the environment variable `DISK_SINK_DIR` to specify the output directory:

```sh
export DISK_SINK_DIR=/tmp/logflow-logs
```
- In your logflow configuration or code, ensure only DiskSink is used as the sink.
- S3-related environment variables are not required in this mode.

### Option 3: Echo to Standard Out (default fallback)
- If neither `DISK_SINK_DIR` nor `ENABLE_S3_SINK` is set, log batches will be echoed to standard output for debugging or development.

---

## Health Check
- Visit [http://localhost:8080/healthz](http://localhost:8080/healthz) to verify the listener is running.

---

## Python Logging Handler Example
```python
from logflow.handler import UDPJsonLogHandler
import logging

logger = logging.getLogger("myapp")
logger.setLevel(logging.INFO)
logger.addHandler(UDPJsonLogHandler(ip="127.0.0.1", port=9999))
logger.info("Hello, logflow!")
```

## CLI Forwarder Example
```sh
echo "test log" | logflow --ip 127.0.0.1 --port 9999
```

---

## Environment Variables (Listener)
- `UDP_LOG_LISTEN_IP` (default: 0.0.0.0)
- `UDP_LOG_LISTEN_PORT` (default: 9999)
- `UDP_BATCH_SIZE_BYTES` (default: 1048576)
- `UDP_BATCH_INTERVAL` (default: 60)
- `S3_ENDPOINT` (default: http://minio_logflow:9000)
- `S3_ACCESS_KEY`, `S3_SECRET_KEY` (default: minioadmin)
- `S3_BUCKET` (default: logflow-ingest)
- `S3_REGION` (default: us-east-1)
- `LOGFLOW_HEALTH_PORT` (default: 8080)
- `ENABLE_S3_SINK` (default: 0)
- `DISK_SINK_DIR` (optional)

---

## Health Check Endpoint
- The listener exposes a health endpoint at `/healthz` (default port 8080):
  - `http://<listener_host>:<health_port>/healthz`
- Useful for readiness/liveness probes in Kubernetes or Docker Compose.

---

## Troubleshooting
- **UDP on MacOS:** If logs are not received, check firewall settings and consider using raw sockets for testing.
- **Port conflicts:** Change `UDP_LOG_LISTEN_PORT` or `LOGFLOW_HEALTH_PORT` as needed.
- **S3/MinIO issues:** Verify credentials and endpoint URLs. MinIO web UI is at [http://localhost:9003](http://localhost:9003).
- **Batch not written:** Ensure at least one log is sent per batch interval/size.

---

## Advanced: Customizing MinIO
- The MinIO container is named `minio_logflow` to avoid conflicts with other MinIO instances.
- You can run multiple MinIOs by changing container names and ports in `docker-compose.yaml`.

---

## FAQ
**Q: Why not use ELK/Loki/Fluentd/other?**
A: logflow is intentionally lightweight, portable, and simple—ideal for container-native, S3-ingesting, or edge logging use cases. It’s open-source and easy to extend.

## License
MIT
