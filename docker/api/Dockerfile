# https://hub.docker.com/r/nginx/unit
FROM unit:1.31.1-python3.11

COPY . /api

RUN apt update -y -m && \
    DEBIAN_FRONTEND=noninteractive \
    apt install --no-install-recommends --no-install-suggests -y \
        libpq-dev \
        gcc && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* && \
    cp /api/docker/api/config.json /docker-entrypoint.d/config.json && \
    pip install poetry


WORKDIR /api
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi
