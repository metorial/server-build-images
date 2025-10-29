# Use Node.js base image
FROM node:24-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
  curl \
  unzip \
  file \
  awscli \
  && rm -rf /var/lib/apt/lists/*

# Install ncc globally
RUN npm install -g @vercel/ncc typescript

# Create working directories
RUN mkdir -p /workspace /boot

# Copy the boot scripts into the image
COPY boot /boot

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
COPY tsconfig.json /tsconfig.json

RUN chmod +x /entrypoint.sh

# Set working directory
WORKDIR /workspace

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]