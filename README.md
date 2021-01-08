# Discord Bot for Ladder Dogs
Discord bot which manages puzzle channels for puzzle hunts via discord commands.
Initially created from [cookiecutter-discord.py-postgres](https://github.com/makupi/cookiecutter-discord.py-postgres).
To keep things very simple, currently this is not using a postgres DB, and is just storing some simple puzzle metadata via JSON files.

# Usage

Most users will just need to become familiar with two commands:
1. To post a new puzzle channel, post `!p puzzle-name` in the `#meta` channel of the corresponding puzzle round.
   This will create a new text and voice channel where puzzle discussion can take place.
   You can scroll the sidebar or use `Ctrl + K` to help search for existing puzzle channels. 
2. When Hunt HQ has confirmed that the puzzle has been solved, post `!solve SOLUTION` in the puzzle channel.
   The channels will be automatically archived afterwards.

----

For a new round/world of puzzles, first start by posting `!round` in the `#bot` channel:
```
!r puzzle-round-name
``` 
This will create a `#puzzleround-name` [category](https://support.discord.com/hc/en-us/articles/115001580171-Channel-Categories-101)
along with a `#meta` puzzle text and voice channel for the round. The `#meta` channels are the place for general discussion about the round,
as well as discussion about the meta puzzle (if there is more than one meta, creating new puzzle channels would be prudent).  

For a new puzzle, one can either post the puzzle via `!puzzle` in the `#bot` channel:
```
!p puzzle-round-name: puzzle-name
```
Or simply `!p puzzle-name` in the corresponding round's `#meta` channel. This will create a `#puzzle-name` text and voice channel
where discussion of the puzzle can take place.

When the puzzle is solved, post `!solve SOLUTION` in the puzzle's channel. The text channel will automatically get archived (moved
to the `#solved-puzzles` category) after ~5 minutes, and the voice channel will be deleted. If this is mistakenly entered,
this can be undone by posting `!unsolve`.

# Todos

* Google Drive API
* Archiving solved puzzles
* Some simple logging

# Setup

Clone this repository
```
git clone https://github.com/azjps/ladder_dogs_discord_bot
```
Create a [discord application, bot](https://realpython.com/how-to-make-a-discord-bot-python/), and add the bot's token to a [`config.json` file](https://github.com/makupi/cookiecutter-discord.py-postgres/blob/master/%7B%7Bcookiecutter.bot_slug%7D%7D/config.json) in the root directory of this project:
```json
{
  "discord_bot_token": "{{discord_bot_token}}",
  "prefix": "!",
  "database": "postgresql://postgres:postgres@localhost:5432/postgres"
}
```
(The database URI can be omitted.)

Now you can run the bot by running the following in a shell:
```bash
# Setup python environment
pip install pipenv
pipenv install  # creates a new virtualenv
pipenv shell
# Start bot
python run.py
```

## Tests

Use `pipenv install --dev` to install dev packages, and in the repo root directory, run
```bash
python -m pytest
```

# Credits

Inspired by various open source discord bot python projects like [cookiecutter-discord.py-postres](https://github.com/makupi/cookiecutter-discord.py-postgres) and [discord-pretty-help](https://github.com/stroupbslayen/discord-pretty-help/). Licensed under [GPL 3.0](https://choosealicense.com/licenses/gpl-3.0/).