#!/bin/bash
# MarketTrust AI — MinIO Bucket Initialization Script
# Creates the required bucket on first startup.

set -e

echo "Waiting for MinIO to be ready..."

# Wait for MinIO to be available
until mc alias set markettrust http://minio:9000 "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-minioadmin123}" 2>/dev/null; do
    echo "MinIO not ready, retrying in 2s..."
    sleep 2
done

echo "MinIO is ready!"

# Create bucket if it doesn't exist
BUCKET="${MINIO_BUCKET:-markettrust-uploads}"
if ! mc ls "markettrust/${BUCKET}" 2>/dev/null; then
    mc mb "markettrust/${BUCKET}"
    echo "Created bucket: ${BUCKET}"
else
    echo "Bucket already exists: ${BUCKET}"
fi

echo "MinIO initialization complete!"
