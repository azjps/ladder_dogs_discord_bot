#!/bin/bash
# Launch discord bot, wrapping with pipenv and logging to {repo}/bot.log & discord.log.
# Example:
# ln -s ~/ladder_dogs_discord_bot/run-bot.sh ~/run-bot.sh   # create symlink in home dir
# nohup ./run-bot.sh &

set -euo pipefail

echo "Starting discord bot"
script_dir=$(dirname "$(readlink -f "$0")")
cd "$script_dir"
exec pipenv run python run.py > bot.log 2>&1