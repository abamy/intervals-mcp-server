FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Tokyo

# Install uv (used to install dependencies from the lockfile)
RUN pip install --no-cache-dir uv

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock ./

# Copy project sources needed to build/install the local package
COPY src src
COPY README.md README.md
COPY .env.example .env.example

# Install EXACTLY the locked dependencies (no fresh resolve, no dev extras).
# --frozen fails the build if uv.lock is out of date with pyproject.toml, so
# production can never silently drift onto an untested mcp SDK version.
RUN uv sync --frozen --no-dev

# Run inside the uv-managed virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Default command to run the MCP server using stdio transport
CMD ["python", "src/intervals_mcp_server/server.py"]
