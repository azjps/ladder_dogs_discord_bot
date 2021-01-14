#!/usr/bin/env python3

import argparse
import json

from bot.utils.puzzles_data import PuzzleJsonDb

if __name__ == "__main__":
    print(json.dumps(PuzzleJsonDb.aggregate_json(), indent=4))