from bot.database import db
from bot.database.models import HuntSettings


class RoundData(db.Model):
    __tablename__ = "round_data"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    category_id = db.Column(db.BIGINT, default=0)
    solved_category_id = db.Column(db.BIGINT, default=0)
    hunt_id = db.Column(db.BIGINT, default=0)
 
    async def hunt_name(self):
        hunt = await HuntSettings.get(self.hunt_id)
        return hunt.hunt_name
