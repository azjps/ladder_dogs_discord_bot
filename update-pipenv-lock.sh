#!/bin/sh

docker buildx build -t pipenv_update .
docker run --rm -it pipenv_update sh -c "pipenv lock > /dev/null 2>&1 && cat Pipfile.lock" > Pipfile.lock

