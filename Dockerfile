# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Install system dependencies and curl for healthcheck
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Copy the .env file into the container
COPY .env .

# Add healthcheck with proper host binding
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://0.0.0.0:5000/ || exit 1

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=5000

# Add proper signal handling
STOPSIGNAL SIGTERM

# Expose the port the app runs on
EXPOSE 5000

# Define the command to run the application with proper host binding
CMD ["python", "-u", "app.py"]