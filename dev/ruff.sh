#!/bin/bash

REPO_TOP=$(dirname -- "$(dirname -- "$( readlink -f -- "$0"; )"; )"; )

cd ${REPO_TOP}

if [[ -z $@ ]]; then
    ARGS="check --fix"
else
    ARGS=$@
fi

docker buildx build --target=devtools -t splat-bot-devtools .
docker run --rm -v ${REPO_TOP}:/code -it splat-bot-devtools sh -c "ruff ${ARGS}"

