# Python Lambda Build Image

A Docker-based build system for packaging Python MCP servers as AWS Lambda functions with the Metorial runtime.

## Overview

This build image downloads user Python code, bundles it with Metorial boot scripts, and creates a deployment package ready for AWS Lambda.

## Structure

```
python-lambda-build-image/
├── boot/                    # Metorial runtime files
│   ├── __init__.py
│   ├── bootstrap.py         # Main Lambda orchestration
│   ├── config.py           # Configuration management
│   ├── oauth.py            # OAuth handling
│   ├── callbacks.py        # Callbacks handling
│   ├── metorial.py         # User-facing API
│   └── lib/
│       ├── __init__.py
│       └── utils.py        # Utility functions
├── index.py                # Lambda handler entry point
├── Dockerfile              # Build environment
├── entrypoint.sh           # Build script
└── requirements.txt        # Boot dependencies (mcp>=1.0.0)
```

## Build Process

1. **Download**: Fetches source code ZIP from `ZIP_URL`
2. **Extract**: Unzips to `/workspace/src`
3. **Detect**: Finds entrypoint (server.py, main.py, index.py, app.py)
4. **Install**: Installs user dependencies from requirements.txt
5. **Bundle**: Copies boot scripts to `__metorial__/` directory
6. **Package**: Creates deployment ZIP with all files
7. **Upload**: Uploads artifact to S3

## Environment Variables

Required:
- `ZIP_URL` - URL to download source code ZIP
- `S3_BUCKET` - Target S3 bucket for deployment
- `S3_KEY` - S3 object key for the artifact

## Usage

```bash
docker build -t python-lambda-build .

docker run \
  -e ZIP_URL="https://example.com/source.zip" \
  -e S3_BUCKET="my-bucket" \
  -e S3_KEY="builds/lambda.zip" \
  python-lambda-build
```

## Entrypoint Detection

The build script searches for these files in order:
1. server.py
2. main.py
3. index.py
4. app.py
5. handler.py
6. lambda.py
7. mcp.py

## User Code Requirements

User Python code should:
1. Import `metorial` from the boot module
2. Call `metorial.create_server(name)` to create a server
3. Register handlers using decorators
4. Optionally configure OAuth and callbacks

Example:
```python
from boot import metorial

server = metorial.create_server("My Server")

@server.list_tools()
async def list_tools():
  return [{"name": "example", "description": "Example tool"}]

@server.call_tool()
async def call_tool(name, arguments):
  return {"result": "Success"}
```

