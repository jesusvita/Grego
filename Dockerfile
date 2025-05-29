# Use the Python version specified in your runtime.txt
ARG PYTHON_VERSION=3.12.3-slim
FROM python:${PYTHON_VERSION}

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Define an app home directory
ENV APP_HOME /app

# Create a non-root user and group for better security
RUN groupadd --system app
RUN useradd --system --gid app --shell /bin/bash --home ${APP_HOME} --create-home app

# Install system dependencies
# - build-essential: For compiling C extensions if pip needs to build from source.
# - libpq-dev: PostgreSQL development headers, crucial for building psycopg2 if a binary wheel isn't available.
# - curl: Can be useful for health checks or other utilities.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR ${APP_HOME}

# Install Python dependencies
# Copy requirements.txt first and install dependencies to leverage Docker layer caching.
# Use --no-cache-dir to reduce image size.
# Ensure files are owned by the app user.
COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# Ensure files are owned by the app user.
COPY --chown=app:app . .

# Switch to the non-root user
USER app

# Collect static files
RUN python manage.py collectstatic --noinput --clear
    

EXPOSE 8000

# Command to run the application
# For Django Channels, use an ASGI server like Daphne.
# Ensure 'chat_project.asgi:application' correctly points to your ASGI application.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "chat_project.asgi:application"]
