FROM node:20-alpine

# Install dependencies
RUN apk add --no-cache bash curl unzip zip python3 py3-pip && \
  pip install awscli && \
  npm install -g @vercel/ncc

WORKDIR /workspace
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
