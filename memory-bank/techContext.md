# Tech Context: logflow

**Primary Technologies:**
- Python 3.9+
- Asyncio for asynchronous I/O
- Standard Python logging module integration
- Boto3 (for S3/MinIO integration)
- Docker & Docker Compose (for deployment)

**Development Setup:**
- All configuration via environment variables or CLI arguments
- Minimal dependencies for easy installation and maintenance
- Designed for containerized and local deployments

**Technical Constraints:**
- Must remain lightweight and fast (low memory/CPU footprint)
- Avoid heavy dependencies unless absolutely necessary
- All features must be configurable without code changes

**Dependencies:**
- Python standard library (asyncio, logging, socket, etc)
- Boto3 (for S3/MinIO)
- aiohttp (for optional HTTP endpoints)
- pytest (for testing)
- Docker (for containerization)
