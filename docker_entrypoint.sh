#!/bin/sh

alembic upgrade head && \
python run.py

