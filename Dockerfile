# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Add /app to Python path so 'src' module is discoverable
ENV PYTHONPATH=/app

# Install Chromium for Kaleido static image export (PNG/PDF/SVG)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Tell Kaleido where to find Chrome
ENV CHROME_BIN=/usr/bin/chromium

# Copy dependency files first (for Docker caching)
COPY pyproject.toml .

# Install dependencies into the system python environment
# This avoids needing to activate a virtualenv inside the container
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the application
COPY src/ ./src/

# Default command (can be overridden)
CMD ["bash"]

