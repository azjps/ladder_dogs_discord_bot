# Discord Bot for Ladder Dogs
Discord bot which manages puzzle channels for puzzle hunts via discord commands.
Initially created from [cookiecutter-discord.py-postgres](https://github.com/makupi/cookiecutter-discord.py-postgres).
Currently for simplicity, I am not using a postgres DB, just storing some simple metadata via JSON files.

# Usage

TODO

# Todos

* `!list`
* Google Drive API
* Some simple logging

# Setup

Clone this repository
```
git clone https://github.com/azjps/ladder_dogs_discord_bot
```
Create a [discord application, bot](https://realpython.com/how-to-make-a-discord-bot-python/), and add the bot's token to a [`config.json` file](https://github.com/makupi/cookiecutter-discord.py-postgres/blob/master/%7B%7Bcookiecutter.bot_slug%7D%7D/config.json) in the root directory of this project:
```json
{
  "token": "{{discord_bot_token}}",
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

# Credits

Inspired by various open source discord bot python projects like [cookiecutter-discord.py-postres](https://github.com/makupi/cookiecutter-discord.py-postgres) and [discord-pretty-help](https://github.com/stroupbslayen/discord-pretty-help/). Licensed under [GPL 3.0](https://choosealicense.com/licenses/gpl-3.0/).