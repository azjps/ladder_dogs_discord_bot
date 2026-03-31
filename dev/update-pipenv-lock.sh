#!/bin/bash

REPO_TOP=$(dirname -- "$(dirname -- "$( readlink -f -- "$0"; )"; )"; )

cd ${REPO_TOP}

docker buildx build --target=devtools -t splat-bot-devtools .
docker run --rm -it splat-bot-devtools sh -c "pipenv lock > /dev/null 2>&1 && cat Pipfile.lock" > Pipfile.lock

