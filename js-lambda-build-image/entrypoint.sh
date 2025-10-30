#!/bin/bash
set -euo pipefail

# Environment variables expected:
# ZIP_URL, S3_BUCKET, S3_KEY

if [ -z "${ZIP_URL:-}" ] || [ -z "${S3_BUCKET:-}" ] || [ -z "${S3_KEY:-}" ]; then
  echo "Missing required environment variables: ZIP_URL, S3_BUCKET, S3_KEY"
  exit 1
fi

echo "Starting Metorial Node Build Process"

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
  "index.ts" "index.js" "index.cjs" "index.mjs"
  "app.ts" "app.js" "app.cjs" "app.mjs"
  "main.ts" "main.js" "main.cjs" "main.mjs"
  "server.ts" "server.js" "server.cjs" "server.mjs"
  "handler.ts" "handler.js" "handler.cjs" "handler.mjs"
  "lambda.ts" "lambda.js" "lambda.cjs" "lambda.mjs"
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
  echo "Searched for: ${ENTRYPOINTS[*]}"
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

npm install typescript > /dev/null

# Get absolute path to the entry point
ENTRY_ABSOLUTE="/workspace/src/$ENTRY"

echo "Entry point absolute path: $ENTRY_ABSOLUTE"

# Copy boot script and replace placeholder with actual entry point
mkdir -p /workspace/src/boot
cp -r /boot/* /workspace/src/boot/

# Replace the $ENTRY_POINT$ placeholder with the actual path
sed -i 's|await import('\''\$\$ENTRY_POINT\$\$'\'')|await import('"'"$ENTRY_ABSOLUTE"'"')|g' /workspace/src/boot/boot.ts

cp /tsconfig.json /workspace/src/boot/tsconfig.json
cp /tsconfig.json /workspace/tsconfig.json

# Build the boot script with ncc (this will bundle everything together)
echo "Building code for Metorial..."
cat > /workspace/src/__metorial_index.ts << 'EOF'
export * from './boot/boot';
EOF

mkdir -p /workspace/dist
ncc build /workspace/src/__metorial_index.ts -o /workspace/dist --minify --source-map > /dev/null

# Create package.json for Lambda runtime
cat > /workspace/package.json << 'EOF'
{
  "name": "lambda-function",
  "version": "1.0.0",
  "main": "dist/index.js",
  "type": "commonjs"
}
EOF

# Zip the Lambda package
cd /workspace
zip -qr artifact.zip dist package.json

unzip -l artifact.zip

# Upload to S3
aws s3 cp artifact.zip "s3://${S3_BUCKET}/${S3_KEY}"

echo "Build completed"