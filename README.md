# *Storage Discord Bot
This discord bot is a fork of the bot created by Ladder Dogs to manage their hunt status in Discord.  Some design decisions didn't work 100% for our team, as well as some additional feature additions, but the initial implementation is stellar, you can find it at https://github.com/azjps/ladder_dogs_discord_bot

# Roadmap

I plan to change this over to using postgres as a backend, running Docker-first, switching from !commands to /commands, and adding some work to mesh better with our Sheets system, as well as some other minor QOL fixes as I see them.

# Usage

Most users will just need to become familiar with two commands:
1. To post a new puzzle channel, post `!p puzzle-name` in the `#meta` channel of the corresponding puzzle round.
   This will create a new text and voice channel where puzzle discussion can take place, as well as
   a new Google Spreadsheet with a handy `Quick Links` worksheet.
   You can scroll the sidebar or use `Ctrl + K` to help search for existing puzzle channels.
2. When Hunt HQ has confirmed that the puzzle has been solved, post `!solve SOLUTION` in the puzzle channel.
   The channels will be automatically archived afterwards.

----

For a new round/world of puzzles, first start by posting `!round` in the `#bot` channel:
```
!r puzzle-round-name
```
This will create a `#puzzleround-name` [category](https://support.discord.com/hc/en-us/articles/115001580171-Channel-Categories-101)
along with a `#general` puzzle text and voice channel for the round. The `#general` channels are the place for general discussion
about the round, but the name can be changed as a setting if desired.  If the name is `#meta`, a sheet will also be created for
tracking the meta puzzle.  (if there is more than one meta, creating new puzzle channels would be prudent).

For a new puzzle, one can either post the puzzle via `!puzzle` in the `#bot` channel:
```
!p puzzle-round-name: puzzle-name
```
Or simply `!p puzzle-name` in the corresponding round's `#general` channel. This will create a `#puzzle-name` text and voice channel
where discussion of the puzzle can take place.

When the puzzle is solved, post `!solve SOLUTION` in the puzzle's channel. The text channel will automatically get archived (moved
to the `#solved-puzzles` category) after ~5 minutes, and the voice channel will be deleted. If this is mistakenly entered,
this can be undone by posting `!unsolve`.

There are various other commands for updating the status, type, priority, and notes associated with a puzzle.
These fields are mainly for others to easily find out about the status of other puzzles. They can be retrieved
on the discord channels using the corresponding commands (see `!info` for the available commands), or viewed
in aggregate on the Nexus spreadsheet, where all puzzles and links are listed.

## Admin

Users with the `manage_channel` role can update administrative settings via `!update_setting {key} {value}`, where
all of the settings can be viewed via `!show_settings`. At the start of hunt, an admin should set
`!update_setting hunt_url https://hunt-website/puzzle/` to the base url where puzzles can be found.
This hunt url will be used to guess the link to the puzzle when new puzzles are posted. If the generated
puzzle link is wrong, it can be updated by posting `!link https://correct-hunt-website-link` in the puzzle channel.

There are also various links to Google Drive that should be updated prior to the start of hunt,
like the IDs of the root Google Drive folder, Resources document, and Nexus spreadsheet.

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

I don't recommend using docker compose for production instances, I maintain my runs on Kubernetes by deploying a postgres container as a statefulset and the bot as a deployment on its own.  But for testing local changes against a test bot, the docker compose has been very useful for me.

Clone this repository
```
git clone https://github.com/AkbarTheGreat/splat_storage_discord_bot
```
Create a [discord application and bot](https://realpython.com/how-to-make-a-discord-bot-python/). For [discord bot gateway intents](https://discordpy.readthedocs.io/en/stable/intents.html), navigate in the [discord developer portal](https://discord.com/developers/applications/) to `{your app} > Bot > Privileged Gateway Intents`, and toggle on `MESSAGE CONTENT INTENT`. (This bot currently uses message-based commands, and not the [new slash commands API](https://support.discord.com/hc/en-us/articles/1500000368501-Slash-Commands-FAQ).) Add the bot's token to a [`config.json` file](https://github.com/makupi/cookiecutter-discord.py-postgres/blob/master/%7B%7Bcookiecutter.bot_slug%7D%7D/config.json) in the root directory of this project:
```json
{
  "discord_bot_token": "{{discord_bot_token}}",
  "prefix": "!",
  "database": "postgresql://postgres:postgres@localhost:5432/postgres"
}
```

Create a .env file with relevant database information, such as:
```bash
DB_PORT=5432
DB_DATABASE=postgres
DB_USER=postgres
DB_PASSWORD=CHANGEME
```

For the Google Drive integration (optional -- comment out the `gsheet` cog if not desired), create a [Google service account (for example see these instructions from `gspread`)](
https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access), and save the service account key JSON file as `google_secrets.json`.

Now you can run the bot by running the following in a shell: `docker compose up`

The environment variable `$LADDER_SPOT_DATA_DIR` can be used to control the directory where guild settings and puzzle data are stored.

If you're interested in running the latest released version somewhere and don't want to build it yourself, I provide a docker image on dockerhub, that can be retrieved with `docker pull akbarthegreat/splat-storage-discord`

## Tests

Use `pipenv install --dev` to install dev packages, and in the repo root directory, run
```bash
python -m pytest
```

# Credits

Forked from https://github.com/azjps/ladder_dogs_discord_bot and continued licensing under [GPL 3.0](https://choosealicense.com/licenses/gpl-3.0/).