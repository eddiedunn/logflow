import pytest

MINIO_HEALTH_URL = "http://localhost:9002/minio/health/ready"

@pytest.fixture(scope="session", autouse=True)
def minio_docker():
    # MinIO is managed by docker-compose and is already healthy before tests run.
    # This fixture is now a no-op, but can provide connection info if needed.
    yield
