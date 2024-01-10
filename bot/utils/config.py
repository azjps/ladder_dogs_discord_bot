import json
import os

default_config = {
    "discord_bot_token": "",
    "prefix": "!",
    "database": "postgresql://localhost/postgres",
    "debug": False,
}


class Config:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.config = {}
        if not os.path.isfile(filename):
            with open(filename, "w") as file:
                json.dump(default_config, file)
        with open(filename) as file:
            self.config = json.load(file)
        self.prefix = self.config.get("prefix", default_config.get("prefix"))
        self.token = self.config.get("discord_bot_token", default_config.get("discord_bot_token"))
        self.database = os.getenv("DB_DSN")  # for docker
        self.debug = self.config.get("debug", default_config.get("debug"))
        if not self.database:
            self.database = self.config.get("database", default_config.get("database"))

    def store(self):
        data = {"prefix": self.prefix, "discord_bot_token": self.token, "database": self.database}
        with open(self.filename, "w") as file:
            json.dump(data, file)
