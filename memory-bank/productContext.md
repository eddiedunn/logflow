# Product Context: logflow

**Why does logflow exist?**
- To address the need for a lightweight, easy-to-deploy, and production-ready logging solution for distributed systems, microservices, and edge environments.
- Existing solutions (ELK, Loki, Fluentd) are often too heavy, complex, or resource-intensive for simple log forwarding and collection needs.
- Many environments require simple UDP-based log transport with robust batching, S3 integration, and minimal operational overhead.

**Problems logflow solves:**
- Simplifies log forwarding and collection in environments where traditional logging stacks are overkill.
- Provides a seamless way to aggregate logs from many sources and forward them to cloud storage (S3/MinIO) or disk.
- Reduces operational complexity for teams needing reliable log collection without heavy dependencies.
- Enables logging pipelines for edge devices, microservices, and cloud workloads with minimal setup.

**How logflow should work:**
- Operate as both a log forwarder (client) and collector (server/listener) over UDP.
- Support batching of logs by size or time, and output logs in JSONL format.
- Allow easy extension for new sinks (e.g., cloud storage, disk, custom endpoints).
- Provide health check endpoints and monitoring hooks for integration with orchestration systems.
- Configuration should be possible via environment variables or CLI arguments for easy automation.

**User Experience Goals:**
- Quick onboarding and minimal configuration required.
- Clear documentation and examples for common deployment scenarios.
- Fast, reliable, and secure log transport and storage.
- Easy integration with Python logging and CLI workflows.
- Transparent operation with clear health and status reporting.
