# https://hub.docker.com/r/nginx/unit
FROM unit:1.31.1-python3.11

# Install dependencies
RUN apt update -y -m && \
    DEBIAN_FRONTEND=noninteractive \
    apt install --no-install-recommends --no-install-suggests -y \
        libpq-dev \
        gcc && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Copy across the application, setup NGINX, and install Poetry
COPY . /api
RUN cp /api/docker/config.json /docker-entrypoint.d/config.json && \
    pip install poetry

# Set the working directory and configure Poetry
WORKDIR /api
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi
