# Use Python base image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
  curl \
  zip \
  unzip \
  file \
  && pip install --no-cache-dir awscli \
  && rm -rf /var/lib/apt/lists/*

# Create working directories
RUN mkdir -p /workspace /boot

# Copy the boot scripts into the image
COPY boot /boot

# Copy the index.py entry point
COPY index.py /index.py

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Set working directory
WORKDIR /workspace

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

