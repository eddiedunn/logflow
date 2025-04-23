# System Patterns: logflow

**System Architecture:**
- logflow is composed of two main components:
  1. **Log Forwarder (Client):** Sends logs over UDP to a specified collector address. Can be used as a Python logging handler or via CLI.
  2. **Log Collector (Server/Listener):** Receives UDP logs, batches them (by size/time), and writes them to one or more sinks (S3/MinIO, disk, etc).
- Designed for asynchronous operation using Python's async features for high throughput and low resource usage.
- Extensible sink architecture: new output destinations can be added via a simple interface.

**Key Design Patterns:**
- **Async I/O:** All network and file operations are non-blocking for scalability.
- **Batching:** Logs are buffered and written in batches to reduce I/O and network overhead.
- **Pluggable Sinks:** Output destinations (disk, S3, etc) are modular and easy to extend.
- **Environment/CLI Config:** All behavior is controlled by environment variables or CLI arguments for easy deployment and automation.
- **Health Check Endpoint:** Exposes a simple HTTP endpoint for health/status monitoring.

**Component Relationships:**
- Forwarders send logs to one or more collectors.
- Collectors may write to multiple sinks in parallel.
- Each deployment can scale horizontally (multiple collectors/forwarders).

**Extensibility:**
- New sinks and integrations can be added without changing core logic.
- Designed to support additional protocols or features as needed.
