FROM python:3.12-slim

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
     # Poetry's configuration:
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local'

RUN apt update \
    && apt upgrade -y \
    && apt install --no-install-recommends -y \
      build-essential \
      curl \
      gettext \
      libpq-dev \
    # Installing `poetry` package manager:
    # https://github.com/python-poetry/poetry
    && curl -sSL 'https://install.python-poetry.org' | python - \
    && poetry --version \
    # Cleaning cache:
    && apt clean -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY poetry.lock pyproject.toml README.md ./

# Install dependencies
RUN poetry config virtualenvs.in-project true && \
    poetry install --without dev,test --no-root && \
    poetry add uvicorn

# Copy application code
COPY . ./

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with uvicorn
CMD ["poetry", "run", "uvicorn", "minager.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
