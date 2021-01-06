import json

import pytest

from bot.utils.puzzles_data import PuzzleData

class TestPuzzleData:
    @pytest.fixture
    def dummy_data(self):
        return PuzzleData(
            name="dummy-puzzle",
            round_name="dummy-round",
            guild_name="dummy-guild",
            guild_id=1,
            channel_mention="#dummy-puzzle",
            channel_id=2,
        )

    def test_construct_dataclass_json(self, dummy_data):
        dummy_json = dummy_data.to_json()
        assert json.loads(dummy_json)["name"] == "dummy-puzzle"

        read_data = PuzzleData.from_json(dummy_json)
        assert read_data.name == "dummy-puzzle"
