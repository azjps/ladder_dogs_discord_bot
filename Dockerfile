FROM python:3.8.5-alpine
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    postgresql-libs

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

CMD docker_entrypoint.sh

