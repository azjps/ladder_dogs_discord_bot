from bot.database import db
from bot.database.models.hunt_settings import HuntSettings, HuntNotFoundError

from typing import Optional


class RoundData(db.Model):
    __tablename__ = "round_data"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    category_id = db.Column(db.BIGINT, default=0)
    solved_category_id = db.Column(db.BIGINT, default=0)
    hunt_id = db.Column(db.BIGINT, default=0)
 
    @classmethod
    async def get_or_create(cls, category: int):
        """query round data, create if it does not exist"""
        round_data = await cls.query_by_category(category)
        if round_data is None:
            round_data = await RoundData.create()
            await round_data.update(
                category_id = category
            ).apply()
        return round_data

    async def hunt_name(self):
        hunt = await HuntSettings.get(self.hunt_id)
        return hunt.hunt_name

    @classmethod
    async def query_by_category(cls, category: int):
        round_data = await RoundData.query.where(
            (RoundData.category_id == category) |
            (RoundData.solved_category_id == category)
        ).gino.first()
        return round_data

    @classmethod
    async def get_hunt_from_category(cls, from_category: int):
        round_data = await cls.query_by_category(from_category)
        if round_data is not None and round_data.hunt_id > 0:
            return round_data.hunt_id
        hunt = await HuntSettings.create()
        return hunt.id

    @classmethod
    async def create_round(cls, guild_id: int, from_category: int, category: int, name: Optional[str], hunt: Optional[str]):
        round_data = await cls.get_or_create(category)
        hunt_id = 0
        if hunt is None:
            hunt_id = await cls.get_hunt_from_category(from_category)
        else:
            hunt_id = await HuntSettings.get_id_for_name(guild_id, hunt)
            if hunt_id is None:
                raise HuntNotFoundError(f"Hunt {hunt} not found in database")
        await round_data.update(
            hunt_id = hunt_id,
            category_id = category,
            name = name
        ).apply()

