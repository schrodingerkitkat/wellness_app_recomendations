# Use the official Python base image with a specific version
FROM python:3.9-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Copy only the requirements file
COPY --chown=appuser:appuser requirements.txt .

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    pip install --no-cache-dir --user -r requirements.txt && \
    apt-get purge -y --auto-remove build-essential && \
    rm -rf /var/lib/apt/lists/*

# ---
FROM python:3.9-slim

# Create a non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Copy the installed packages from the builder stage
COPY --from=builder --chown=appuser:appuser /home/appuser/.local /home/appuser/.local

# Copy the application code
COPY --chown=appuser:appuser ./api_service.py .

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED 1

# Expose the port on which the API service will run
EXPOSE 8000

# Switch to the non-root user
USER appuser

# Run the API service
CMD ["python", "./api_service.py"]
