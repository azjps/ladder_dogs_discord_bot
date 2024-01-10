import datetime
import json


from bot.utils.puzzles_data import PuzzleData


class TestPuzzleData:
    def dummy_data(self, name="dummy-puzzle", round_name="dummy-round", start_day=1):
        return PuzzleData(
            name=name,
            round_name=round_name,
            guild_name="dummy-guild",
            guild_id=1,
            channel_mention="#dummy-puzzle",
            channel_id=2,
            start_time=datetime.datetime(2020, 1, start_day),
        )

    def test_construct_dataclass_json(self):
        dummy_json = self.dummy_data().to_json()
        assert json.loads(dummy_json)["name"] == "dummy-puzzle"

        read_data = PuzzleData.from_json(dummy_json)
        assert read_data.name == "dummy-puzzle"

    def test_sort_puzzles(self):
        data = [
            # names constructed so that they end up in sorted order
            self.dummy_data(name="p2", round_name="r1", start_day=2),
            self.dummy_data(name="p1", round_name="r1", start_day=1),
            self.dummy_data(name="p5", round_name="r3", start_day=4),
            self.dummy_data(name="p6", round_name="r3", start_day=5),
            self.dummy_data(name="p4", round_name="r2", start_day=6),
            self.dummy_data(name="p3", round_name="r2", start_day=3),
        ]
        data_sorted = PuzzleData.sort_by_round_start(data)
        assert [p.name for p in data_sorted] == [f"p{i+1}" for i in range(len(data))]
