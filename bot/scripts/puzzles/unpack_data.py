#!/usr/bin/env python3
"""
python -m bot.scripts.puzzles.pack_data > backup.json
python -m bot.scripts.unpack_data -p unpack_data.py
"""

import argparse
import json
from pathlib import Path

from bot.utils.puzzles_data import PuzzleJsonDb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", required=True, help="Path to data json built by pack_data.py")
    parser.add_argument("-y", action="store_true", help="Unpack with prompting")
    args = parser.parse_args()

    with open(args.path) as fp:
        all_data = json.load(fp)

    if not args.y:
        dir_path = PuzzleJsonDb.dir_path
        existing_paths = []
        for relpath in all_data.keys():
            json_path = dir_path / relpath
            if json_path.exists(): 
                existing_paths.append(json_path)

        if existing_paths:
            existing = "\n".join([str(p) for p in existing_paths])
            y_or_n = input(f"The following files will be overwritten:\n{existing}\nProceed? [y/N] ")
            if y_or_n.lower() == "n":
                return

    for relpath, contents in all_data.items():
        json_path = dir_path / relpath
        json_path.parent.parent.mkdir(exist_ok=True)
        json_path.parent.mkdir(exist_ok=True)
        with open(json_path, "w") as fp:
            json.dump(contents, fp, indent=4)

if __name__ == "__main__":
    main()
