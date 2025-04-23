# Project Brief: logflow

**Project Name:** logflow

**Purpose:**
logflow is a lightweight, open-source, production-grade Python utility for UDP log forwarding and collection. It aims to provide a simple, fast, and secure way to forward and collect logs over UDP, supporting both log forwarding (client) and log collection (listener/server), with extensible sinks such as S3/MinIO and disk.

**Vision:**
- Make log forwarding and collection as easy and robust as possible for modern distributed systems.
- Enable seamless integration, monitoring, and scaling of logging in any environment (dev, prod, cloud, edge).
- Remain lighter and simpler than ELK, Loki, or Fluentd for many use-cases, especially for microservices, edge devices, and S3-centric log pipelines.

**Key Features:**
- Async UDP log ingestion and forwarding
- Batching (by size/time) and JSONL output
- S3/MinIO integration with unique, project-specific container naming
- Health check endpoint
- Python logging handler and CLI client
- Docker Compose for local/cloud deployment
- Minimal dependencies, open for extension

**Why logflow?**
- Lighter and simpler than ELK, Loki, or Fluentd for many use-cases
- Ideal for microservices, edge devices, and S3-centric log pipelines
- Easy to deploy, container-native, and open-source

**Initial Setup:**
- All configuration via environment variables or CLI arguments
- Project is organized for clean onboarding, testing, and extension

**Documentation:**
- The memory bank documents project goals, architecture, design decisions, and ongoing progress
- Context will be updated as logflow evolves
