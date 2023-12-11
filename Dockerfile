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

COPY . /code

CMD pipenv run python run.py

