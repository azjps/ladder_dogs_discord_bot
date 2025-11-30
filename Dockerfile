#-------------------------------------------------------------------------------
# Base image contains the core dependencies for running a server
#-------------------------------------------------------------------------------
FROM python:3.10.13-alpine3.19 as base
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    postgresql-libs

RUN mkdir /code
WORKDIR /code

RUN pip install pipenv

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

#-------------------------------------------------------------------------------
# Devtools contains linters or autoformatters which aren't needed in production
#-------------------------------------------------------------------------------
FROM base as devtools

RUN pipenv install --system --dev

CMD "echo No default command"

#-------------------------------------------------------------------------------
# The server image installs the code, locked dependencies, then runs the bot.
#-------------------------------------------------------------------------------
FROM base as server 

COPY ./docker_entrypoint.sh docker_entrypoint.sh
COPY ./alembic.ini alembic.ini
COPY ./run.py run.py
COPY ./alembic alembic
COPY ./bot bot

RUN pipenv install --system

CMD ./docker_entrypoint.sh


