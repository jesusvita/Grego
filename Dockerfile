ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user and group
ARG APP_USER=appuser
RUN groupadd -r ${APP_USER} && useradd --no-log-init -r -g ${APP_USER} ${APP_USER}

# Install system dependencies
# libpq-dev provides runtime libraries for psycopg2 and build headers if building from source
# gcc is for building C extensions if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /code

# Copy requirements first to leverage Docker cache
COPY requirements.txt /code/requirements.txt

# Install Python dependencies
# --no-cache-dir: Disables the pip cache, reducing image size.
# Running as root here for pip install, then will switch user.
RUN set -ex && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# Copy the rest of the application code
COPY . /code

# Change ownership of the /code directory to the app user
RUN chown -R ${APP_USER}:${APP_USER} /code

# Switch to the non-root user
USER ${APP_USER}

# Collect static files as the app user
# --clear: Clears the existing files before trying to copy or link the static files.
RUN python manage.py collectstatic --noinput --clear

# Expose the port the app runs on
EXPOSE 8000

# Run the application
# The CMD will run as the APP_USER
CMD ["daphne","-b","0.0.0.0","-p","8000","chat_project.asgi:application"]
