#!/bin/bash
set -euo pipefail

# Environment variables expected:
# ZIP_URL, S3_BUCKET, S3_KEY

if [ -z "${ZIP_URL:-}" ] || [ -z "${S3_BUCKET:-}" ] || [ -z "${S3_KEY:-}" ]; then
  echo "Missing required environment variables: ZIP_URL, S3_BUCKET, S3_KEY"
  exit 1
fi

echo "Starting Metorial Python Build Process"

echo "Downloading source code..."

# Download with error handling
HTTP_CODE=$(curl -L "$ZIP_URL" -o /tmp/source.zip -w "%{http_code}" -s)

if [ "$HTTP_CODE" != "200" ]; then
  echo "Download failed with HTTP status: $HTTP_CODE"
  echo "Response content:"
  cat /tmp/source.zip
  exit 1
fi

# Verify it's a valid zip file
if ! file /tmp/source.zip | grep -q "Zip archive"; then
  echo "Downloaded file is not a valid ZIP archive:"
  file /tmp/source.zip
  echo "First 500 bytes:"
  head -c 500 /tmp/source.zip
  exit 1
fi

mkdir -p /workspace/src
unzip -q /tmp/source.zip -d /workspace/src

cd /workspace/src

# Detect entrypoint
ENTRYPOINTS=(
  "server.py" "main.py" "index.py" "app.py"
  "handler.py" "lambda.py" "mcp.py"
)

ENTRY=""
for f in "${ENTRYPOINTS[@]}"; do
  if [ -f "$f" ]; then
    ENTRY="$f"
    break
  fi
done

if [ -z "$ENTRY" ]; then
  echo "ERROR: No valid entrypoint found."
  echo "Searched for: ${ENTRYPOINTS[*]}"
  exit 1
fi

echo "Detected entrypoint: $ENTRY"

# Handle requirements.txt
HAS_REQUIREMENTS=false
if [ -f "requirements.txt" ]; then
  HAS_REQUIREMENTS=true
  echo "Installing user dependencies from requirements.txt..."
  pip install --no-cache-dir -r requirements.txt -t .
else
  echo "No requirements.txt found. Will create minimal one."
fi

# Always install mcp dependency
echo "Installing MCP SDK..."
pip install --no-cache-dir "mcp>=1.0.0" -t .

# Copy boot scripts to root level for user imports
echo "Copying Metorial boot scripts..."
cp -r /boot /workspace/src/boot

# Also copy to __metorial__ directory for internal use
mkdir -p /workspace/src/__metorial__
cp -r /boot/* /workspace/src/__metorial__/

# Copy the Lambda handler entry point
cp /index.py /workspace/src/index.py

# Clean up Python cache and build artifacts
echo "Cleaning up build artifacts..."
find /workspace/src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /workspace/src -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find /workspace/src -type f -name "*.pyc" -delete 2>/dev/null || true
find /workspace/src -type f -name "*.pyo" -delete 2>/dev/null || true

# Zip the Lambda package
echo "Creating deployment package..."
cd /workspace/src
zip -qr /workspace/artifact.zip .

echo "Deployment package contents:"
unzip -l /workspace/artifact.zip

# Upload to S3
echo "Uploading to S3..."
aws s3 cp /workspace/artifact.zip "s3://${S3_BUCKET}/${S3_KEY}"

echo "Build completed successfully"
echo "Entrypoint: $ENTRY"
echo "S3 Location: s3://${S3_BUCKET}/${S3_KEY}"

