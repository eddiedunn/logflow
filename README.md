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

### 4. Python Logging Handler Example
```python
from logflow.handler import UDPJsonLogHandler
import logging

logger = logging.getLogger("myapp")
logger.setLevel(logging.INFO)
logger.addHandler(UDPJsonLogHandler(ip="127.0.0.1", port=9999))
logger.info("Hello, logflow!")
```

### 5. CLI Forwarder Example
```sh
echo "test log" | logflow --ip 127.0.0.1 --port 9999
```

## Environment Variables (Listener)
- `UDP_LOG_LISTEN_IP` (default: 0.0.0.0)
- `UDP_LOG_LISTEN_PORT` (default: 9999)
- `UDP_BATCH_SIZE_BYTES` (default: 1048576)
- `UDP_BATCH_INTERVAL` (default: 60)
- `S3_ENDPOINT` (default: http://minio_logflow:9000)
- `S3_ACCESS_KEY`, `S3_SECRET_KEY` (default: minioadmin)
- `S3_BUCKET` (default: logflow-ingest)
- `S3_REGION` (default: us-east-1)

## Advanced: Customizing MinIO
- The MinIO container is named `minio_logflow` to avoid conflicts with other MinIO instances.
- You can run multiple MinIOs by changing container names and ports in `docker-compose.yaml`.

## FAQ
**Q: Why not use ELK/Loki/Fluentd/other?**
A: logflow is intentionally lightweight, portable, and simple—ideal for container-native, S3-ingesting, or edge logging use cases. It’s open-source and easy to extend.

## License
MIT
