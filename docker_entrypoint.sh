#!/bin/sh

pipenv run alembic upgrade head && \
pipenv run python run.py

