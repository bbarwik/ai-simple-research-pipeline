FROM python:3.12-bookworm

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY ai_simple_research_pipeline ./ai_simple_research_pipeline

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip cache purge

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "-u", "-m", "ai_simple_research_pipeline"]
