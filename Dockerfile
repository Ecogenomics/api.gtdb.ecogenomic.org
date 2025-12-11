FROM python:3.13-slim

WORKDIR /code

COPY ./poetry.lock /code/poetry.lock
COPY ./pyproject.toml /code/pyproject.toml

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

COPY ./api /code/api
COPY ./.env /code/.env
COPY ./main.py /code/main.py

CMD ["fastapi", "run", "main.py", "--proxy-headers", "--port", "80"]

# Testing:
# docker build . -t gtdb-api-dev
# docker run -d --name gtdb-api-dev -p 80:80 gtdb-api-dev