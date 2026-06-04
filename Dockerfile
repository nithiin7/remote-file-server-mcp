# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# file-server-mcp — MCP server for SMB/CIFS file share access
#
# Build:
#   docker build -t file-server-mcp .
#
# Run (inject secrets at runtime — NEVER bake them into the image):
#   docker run --rm -i \
#     -e SMB_HOST=192.168.1.100 \
#     -e SMB_SHARE=my_share \
#     -e SMB_USERNAME=my_user \
#     -e SMB_PASSWORD=my_password \
#     file-server-mcp
#
# Or use --env-file to keep secrets out of shell history:
#   docker run --rm -i --env-file .env file-server-mcp
#
# Optional env vars: SMB_PORT, SMB_ENCRYPT, MAX_FILE_SIZE_MB,
#                    ALLOWED_PATHS, AUDIT_LOG_PATH, READ_PREVIEW_LINES
# ---------------------------------------------------------------------------

# Pin to a specific digest for reproducible builds.
# To update: docker pull python:3.12-slim && docker inspect python:3.12-slim --format='{{index .RepoDigests 0}}'
# Or manage automatically with Dependabot (see .github/dependabot.yml).
FROM python:3.14-slim@sha256:c845af9399020c7e562969a13689e929074a10fd057acd1b1fad06a2fb068e97 AS base

# Create a non-root user — never run the server as root
RUN useradd --create-home --shell /bin/bash mcpuser

WORKDIR /app

# Copy the full package source (pyproject.toml must be present for pip install)
COPY pyproject.toml README.md ./
COPY server.py config.py ./
COPY smb/ smb/
COPY tools/ tools/
COPY utils/ utils/

# Install the package and all dependencies
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# Drop to non-root user for all subsequent operations
USER mcpuser

# MCP servers communicate over stdio — no ports to expose
# Secrets must be injected via environment variables at runtime
ENV SMB_PORT=445 \
    SMB_ENCRYPT=true \
    SMB_TIMEOUT=30 \
    MAX_FILE_SIZE_MB=10 \
    READ_PREVIEW_LINES=100

# No HEALTHCHECK: this server speaks MCP over stdio, not HTTP.
# There is no listening socket for Docker or orchestrators to probe.
# Liveness is determined by the MCP client maintaining the stdio connection.
HEALTHCHECK NONE

ENTRYPOINT ["file-server-mcp"]
