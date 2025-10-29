#!/bin/bash
set -euo pipefail

# Environment variables expected:
# ZIP_URL, S3_BUCKET, S3_KEY

if [ -z "${ZIP_URL:-}" ] || [ -z "${S3_BUCKET:-}" ] || [ -z "${S3_KEY:-}" ]; then
  echo "Missing required environment variables: ZIP_URL, S3_BUCKET, S3_KEY"
  exit 1
fi

echo "Starting Metorial JS Lambda Build Process"

echo "Downloading source zip from ${ZIP_URL}"
curl -L "$ZIP_URL" -o /tmp/source.zip

echo "Unpacking..."
mkdir -p /workspace/src
unzip -q /tmp/source.zip -d /workspace/src

cd /workspace/src

# Detect entrypoint
ENTRYPOINTS=(
  "index.ts" "index.js" "index.cjs" "index.mjs"
  "app.ts" "app.js" "app.cjs" "app.mjs"
  "main.ts" "main.js" "main.cjs" "main.mjs"
  "server.ts" "server.js" "server.cjs" "server.mjs"
  "boot.ts" "boot.js" "boot.cjs" "boot.mjs"
  "mcp.ts" "mcp.js" "mcp.cjs" "mcp.mjs"
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
  exit 1
fi

echo "Detected entrypoint: $ENTRY"

HAS_PACKAGE_JSON=false
if [ -f "package.json" ]; then
  HAS_PACKAGE_JSON=true
fi

if [ "$HAS_PACKAGE_JSON" = true ]; then
  echo "Installing dependencies from package.json..."
  npm install
else
  echo "No package.json found. Initializing npm project..."
  npm init -y
fi

npm install typescript

# Build with ncc
mkdir -p /workspace/dist
ncc build "$ENTRY" -o /workspace/dist

# Zip the dist folder
cd /workspace
zip -qr artifact.zip dist

# Upload to S3 with tagging
echo "Uploading artifact.zip to s3://${S3_BUCKET}/${S3_KEY}..."
aws s3 cp artifact.zip "s3://${S3_BUCKET}/${S3_KEY}" --tagging "temporary=true"

echo "Build complete and uploaded successfully."
