#!/bin/sh
set -e

MINIO_HOST=${MINIO_HOST:-minio_logflow}
MINIO_PORT=${MINIO_PORT:-9000}
MAX_WAIT=${MAX_WAIT:-120}

# Wait for DNS to resolve minio_logflow
for i in $(seq 1 $MAX_WAIT); do
    IP=$(getent hosts "$MINIO_HOST" | awk '{ print $1 }' || true)
    if [ -n "$IP" ]; then
        echo "[wait-for-minio] MINIO_HOST=$MINIO_HOST resolves to $IP"
        break
    fi
    echo "[wait-for-minio] Waiting for DNS... ($i/$MAX_WAIT)"
    sleep 1
done

# Touch health file to avoid missing file error
: > /tmp/minio_health.txt

for i in $(seq 1 $MAX_WAIT); do
    STATUS=$(curl -s -o /tmp/minio_health.txt -w "%{http_code}" http://$MINIO_HOST:$MINIO_PORT/minio/health/ready || true)
    BODY=$(cat /tmp/minio_health.txt)
    echo "[wait-for-minio] Attempt $i/$MAX_WAIT: status=$STATUS body='$BODY'"
    if { [ "$STATUS" = "200" ] && echo "$BODY" | grep -q OK; } || { [ "$STATUS" = "400" ] && echo "$BODY" | grep -q 'InvalidRequest'; }; then
        echo "MinIO is healthy!"
        exec "$@"
        exit 0
    fi
    sleep 1
done

echo "MinIO did not become healthy in time!" >&2
exit 1
