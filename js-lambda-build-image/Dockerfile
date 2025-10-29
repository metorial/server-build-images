FROM node:20-bookworm

# Install system tools and AWS CLI via apt
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  bash \
  curl \
  unzip \
  zip \
  python3 \
  python3-pip \
  awscli \
  ca-certificates && \
  rm -rf /var/lib/apt/lists/*

# Install JS bundler
RUN npm install -g @vercel/ncc

WORKDIR /workspace

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
