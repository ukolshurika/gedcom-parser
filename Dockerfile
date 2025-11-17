# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create a working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# This leverages Docker's layer caching. If requirements don't change,
# this layer won't be rebuilt, speeding up subsequent builds.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Stage 2: Create the final image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy installed packages and executables from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application source code
COPY src /app/src

# Expose the port Uvicorn will listen on
EXPOSE 8000

# Run the application with Uvicorn
# This uses the exec form of CMD, which is preferred.
# The --host 0.0.0.0 is necessary for the server to be accessible from outside the container.
CMD ["uvicorn", "gedcom_mcp.fastapi_server:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/src"]
