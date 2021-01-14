#!/usr/bin/env python3
"""
Rename specified Google Drive file by id

python -m bot.scripts.gdrive.rename_file --id [ID] --name [..]
"""
import asyncio

from bot.utils.gdrive import rename_file

if __name__ == "__main__":
    # Find or create a new folder
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="ID of file to rename")
    parser.add_argument("--name", required=True, help="New name of file")
    args = parser.parse_args()

    result = asyncio.run(rename_file(args.id, lambda x: args.name), debug=True)
    print(result)
