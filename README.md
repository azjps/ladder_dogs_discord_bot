# Discord Bot for Ladder Dogs
Simple discord bot which manages puzzle channels for puzzle hunts via discord commands, used by a small-to-medium sized team.

This was initially created from [`cookiecutter-discord.py-postgres`](https://github.com/makupi/cookiecutter-discord.py-postgres) and uses [`aiogoogle`](https://aiogoogle.readthedocs.io/en/latest/)/[`gspread_asyncio`](https://gspread-asyncio.readthedocs.io/en/latest/index.html) for (optional) Google Drive integration. It uses [`gino`](https://python-gino.org/) to store puzzle metadata in a PostgreSQL database.

Thanks to a few other teams who have helped to improve on the bot's features. Credit especially to [@AkbarTheGreat on Splat](https://github.com/AkbarTheGreat/splat_storage_discord_bot) for adding the discord slash commands and PostgreSQL backend support.

# Usage

Most users will just need to become familiar with two slash commands:
1. To post a new puzzle channel, post `/puzzle puzzle-name` in the `#general` channel of the corresponding puzzle round.
   This will create a new text and voice channel where puzzle discussion can take place, as well as
   a new Google Spreadsheet with a handy `Quick Links` worksheet.
   You can scroll the sidebar or use `Ctrl + K` to help search for existing puzzle channels.
2. When Hunt HQ has confirmed that the puzzle has been solved, post `/solve SOLUTION` in the puzzle channel.
   The channels will be automatically archived afterwards.

----

To start a new hunt, start with
```
/hunt <hunt-url e.g. https://mysteryhunt.edu> <hunt-name>
```

For a new round/world of puzzles, first start by posting `/round` in the `#<discord_bot_channel>` channel (assuming there's only one active hunt), or in the `#general` channel associated with the hunt:
```
/round hunt-round-name
```
This will create a `#hunt-round-name` [category](https://support.discord.com/hc/en-us/articles/115001580171-Channel-Categories-101)
along with a `#general` puzzle text and voice channel for the round. The `#general` channels are the place for general discussion
about the round, but the name can be changed as a setting if desired.  If the name is `#meta`, a sheet will also be created for
tracking the meta puzzle. (If there is more than one meta, creating new puzzle channels would be prudent).

For a new puzzle, one can either post the puzzle via `/puzzle` in the `#<discord_bot_channel>` channel:
```
/puzzle <puzzle:puzzle-name> <hunt_round:round-name>
```
Or simply `/puzzle puzzle-name` in the corresponding round's `#general` channel. This will create a `#puzzle-name` text and voice channel
where discussion of the puzzle can take place.

When the puzzle is solved, post `/solve SOLUTION` in the puzzle's channel. The text channel will automatically get archived (moved
to the `#solved-puzzles` category) after ~5 minutes, and the voice channel will be deleted. If this is mistakenly entered,
this can be undone by posting `/unsolve`.

There are various other commands for updating the status, type, priority, and notes associated with a puzzle.
These fields are mainly for others to easily find out about the status of other puzzles. They can be retrieved
on the discord channels using the corresponding commands (see `/info` for the available commands), or viewed
in aggregate on the Nexus spreadsheet, where all puzzles and links are listed.

## Admin

Users with the `manage_channel` role can update administrative settings via `/update_setting {key} {value}`, where
all of the settings can be viewed via `/show_settings`. At the start of a hunt, an admin should create
`/hunt <hunt_url> <hunt_name>` and then update the hunt settings
`/update_hunt_setting hunt_url https://hunt-website/puzzle/` to the base url where puzzles can be found.
This hunt url will be used to guess the link to the puzzle when new puzzles are posted. If the generated
puzzle link is wrong, it can be updated by posting `/link https://correct-hunt-website-link` in the puzzle channel.

There are also various links to Google Drive that should be updated prior to the start of hunt,
like the IDs of the root Google Drive folder, Resources document, and Nexus spreadsheet. The ID is just the ~33 ASCII character ID string in the URL, not the full URL to the Google documents.

## Google Drive

When a puzzle channel is created, if Google Drive integration is enabled, a corresponding spreadsheet is created
in the a folder for the puzzle round in the root Google Drive directory. The spreadsheet will have a secondary
"Quick Links" tab created for convenience.

![Puzzle spreadsheet Quick Links tab example](docs/gsheet_puzzle_quick_links.png)

The bot periodically updates a "nexus spreadsheet" which shows a list of all puzzles along with relevant information
such as the puzzle url, spreadsheet link. (The formatting of the nexus spreadsheet can be done manually by the user;
the bot only populates the contents of the spreadsheet cells.)

![Nexus spreadsheet example](docs/gsheet_nexus_example.png)

# Setup with Docker Compose

I don't recommend using docker compose for production instances, I maintain my runs on Kubernetes by deploying a postgres container as a statefulset and the bot as a deployment on its own. But for testing local changes against a test bot, docker compose has been very useful.

Clone this repository
```
git clone https://github.com/azjps/ladder_dogs_discord_bot
```
Create a [discord application and bot](https://realpython.com/how-to-make-a-discord-bot-python/). For [discord bot gateway intents](https://discordpy.readthedocs.io/en/stable/intents.html), navigate in the [discord developer portal](https://discord.com/developers/applications/) to `{your app} > Bot > Privileged Gateway Intents`, and toggle on `MESSAGE CONTENT INTENT`. (This might no longer be necessary as the bot now uses the [slash commands API](https://support.discord.com/hc/en-us/articles/1500000368501-Slash-Commands-FAQ).) Add the bot's token to a [`config.json` file](https://github.com/makupi/cookiecutter-discord.py-postgres/blob/master/%7B%7Bcookiecutter.bot_slug%7D%7D/config.json) in the root directory of this project:
```json
{
  "discord_bot_token": "{{discord_bot_token}}",
  "prefix": "!",
  "database": "postgresql://postgres:postgres@localhost:5432/postgres"
}
```

Create a `.env` file with relevant database information, such as:
```bash
DB_PORT=5432
DB_DATABASE=postgres
DB_USER=postgres
DB_PASSWORD=CHANGEME
```
(It would have been nice if `gino` supported `sqlite` for something more lightweight. It would not be too hard to switch to `sqlalchemy` if the need arises, especially given `sqlalchemy` natively supports asyncio now. Also its a bit unfortunate that there are multiple config files & secrets files required.)

For the Google Drive integration (optional -- comment out the `gsheet` cog if not desired), create a [Google service account (for example see these instructions from `gspread`)](
https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access), and save the service account key JSON file as `google_secrets.json`.

Now you can run the bot by running the following in a shell: `docker compose up`. On a barebones VM, you may first have to install Docker & `docker-compose`:
```bash
sudo yum install docker -y
sudo systemctl start docker
# Check docker-compose website for relevant release
curl -SL https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-linux-x86_64 -o bin/docker-compose
sudo ~/bin/docker-compose up
```

To launch a postgres cli shell to see the state of the database:
```bash
sudo docker ps
sudo docker exec -it ladder_dogs_discord_bot-db-1 psql -U postgres
```

To launch an interactive python shell with the same environment:
```bash
sudo docker-compose run bot sh
pipenv run python
```

If you're interested in running the latest released version somewhere and don't want to build it yourself, @AkbarTheGreat has a docker image on dockerhub for Splat's latest bot release, that can be retrieved with `docker pull akbarthegreat/splat-storage-discord`

## Tests

(Currently not maintained.) Use `pipenv install --dev` to install dev packages, and in the repo root directory, run
```bash
python -m pytest
```
Formatting / linting is done with [`ruff`](https://github.com/astral-sh/ruff).

# Credits

Inspired by various open source discord bot python projects like [cookiecutter-discord.py-postgres](https://github.com/makupi/cookiecutter-discord.py-postgres). Licensed under GPL 3.0 (due to the aforementioned cookiecutter).