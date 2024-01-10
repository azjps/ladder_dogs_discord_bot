FROM python:3.12.1-alpine3.19
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache \
    build-base \
    cargo \
    postgresql-dev \
    postgresql-libs \
    rust

RUN mkdir /code
WORKDIR /code

RUN pip install pipenv

COPY Pipfile Pipfile
RUN pipenv install

COPY ./docker_entrypoint.sh docker_entrypoint.sh
COPY ./alembic.ini alembic.ini
COPY ./run.py run.py
COPY ./alembic alembic
COPY ./bot bot

CMD ./docker_entrypoint.sh

