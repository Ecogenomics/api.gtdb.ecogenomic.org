FROM python:3.11-slim-buster

# Install OS requirements
RUN apt update -y -m && \
    DEBIAN_FRONTEND=noninteractive \
    apt install --no-install-recommends --no-install-suggests -y \
        wget \
        libpq-dev \
        libgomp1 \
        unzip \
        gcc \
        build-essential && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Download required files
WORKDIR /tmp
RUN wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.33/fastANI-Linux64-v1.33.zip" && \
    unzip -o fastANI-Linux64-v1.33.zip && \
    mv fastANI /bin/fastANI_1.33 && \
    chmod +x /bin/fastANI_1.33 && \
    wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.32/fastANI-Linux64-v1.32.zip" && \
    unzip -o fastANI-Linux64-v1.32.zip && \
    mv fastANI /bin/fastANI_1.32 && \
    chmod +x /bin/fastANI_1.32 && \
    wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.31/fastANI-Linux64-v1.31.zip" && \
    unzip -o fastANI-Linux64-v1.31.zip && \
    mv fastANI /bin/fastANI_1.31 && \
    chmod +x /bin/fastANI_1.31 && \
    wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.3/fastANI-Linux64-v1.3.zip" && \
    unzip -o fastANI-Linux64-v1.3.zip && \
    mv fastANI /bin/fastANI_1.3 && \
    chmod +x /bin/fastANI_1.3 && \
    wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.2/fastANI-Linux64-v1.2.zip" && \
    unzip -o fastANI-Linux64-v1.2.zip && \
    mv fastANI /bin/fastANI_1.2 && \
    chmod +x /bin/fastANI_1.2 && \
    wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.1/fastani-Linux64-v1.1.zip" && \
    unzip -o fastani-Linux64-v1.1.zip && \
    mv fastANI /bin/fastANI_1.1 && \
    chmod +x /bin/fastANI_1.1 && \
    wget "https://github.com/ParBLiSS/FastANI/releases/download/v1.0/fastani-Linux64-v1.0.zip" && \
    unzip -o fastani-Linux64-v1.0.zip && \
    mv fastani-Linux64-v1.0/fastANI /bin/fastANI_1.0 && \
    chmod +x /bin/fastANI_1.0 && \
    rm -rf /tmp/*

# Copy the API
RUN mkdir -p /api
COPY . /api
WORKDIR /api

# Install python requirements
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Run the queue
RUN chmod +x /api/docker/fastani/entrypoint.sh
ENTRYPOINT ["/bin/bash", "-c", "/api/docker/fastani/entrypoint.sh"]
