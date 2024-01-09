from bot.database import db
from bot.database.models.hunt_settings import HuntSettings, HuntNotFoundError

from typing import Optional


class RoundData(db.Model):
    __tablename__ = "round_data"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    hunt_id = db.Column(
        db.BIGINT,
        db.ForeignKey("hunt_settings.id", onupdate="CASCADE", ondelete="CASCADE"),
        default=0,
    )
    name = db.Column(db.Text)
    category_id = db.Column(db.BIGINT, nullable=True, unique=True)  # discord assigned id
    solved_category_id = db.Column(db.BIGINT, default=0)
    round_url = db.Column(db.Text)  # if there is a separate url scheme for round
    round_url_sep = db.Column(db.Text)  # if there is a different separater for round

    __table_args__ = (db.UniqueConstraint(hunt_id, name, name="uq_round_data_hunt_id_name"),)

    @classmethod
    async def get_or_create(cls, category: int, **kwargs) -> "RoundData":
        """query round data, create if it does not exist"""
        round_data = await cls.query_by_category(category)
        if round_data is None:
            round_data = await RoundData.create(category_id=category, **kwargs)
        return round_data

    @classmethod
    async def get_hunt_from_round(cls, guild_id: int, round_channel: int) -> HuntSettings:
        round_data = await cls.get_or_create(round_channel)
        hunt = await HuntSettings.get(round_data.hunt_id)
        if hunt is None:
            hunt = await HuntSettings.create()
            # Also update the round
            await round_data.update(hunt_id=hunt.id).apply()
        return hunt

    @classmethod
    async def rounds_in_hunt(cls, hunt: HuntSettings):
        rounds = await cls.query.where((cls.hunt_id == hunt.id)).gino.all()
        return rounds

    async def hunt_name(self):
        hunt = await HuntSettings.get(self.hunt_id)
        return hunt.hunt_name

    @classmethod
    async def query_by_category(cls, category: int, require_active=False) -> Optional["RoundData"]:
        round_data = await RoundData.query.where(
            (RoundData.category_id == category) | (RoundData.solved_category_id == category)
        ).gino.first()
        if require_active and round_data:
            hunt_data = await HuntSettings.query.where(
                HuntSettings.id == round_data.hunt_id
            ).gino.first()
            if hunt_data:
                if hunt_data.end_time:
                    return None
            else:
                return None
        return round_data

    @classmethod
    async def get_hunt_from_category(cls, guild_id: int, from_category: int):
        round_data = await cls.query_by_category(from_category)
        if round_data is not None and round_data.hunt_id > 0:
            return round_data.hunt_id
        hunt = await HuntSettings.create(guild_id=guild_id)
        return hunt.id

    @classmethod
    async def create_round(
        cls,
        guild_id: int,
        from_category: int,
        category: int,
        name: Optional[str],
        hunt: Optional[str],
    ):
        hunt_id = 0
        if hunt is None:
            hunt_id = await cls.get_hunt_from_category(guild_id, from_category)
        else:
            hunt_id = await HuntSettings.get_id_for_name(guild_id, hunt)
            if hunt_id is None:
                raise HuntNotFoundError(f"Hunt {hunt} not found in database")
        return await cls.get_or_create(
            category=category,
            hunt_id=hunt_id,
            name=name,
        )
