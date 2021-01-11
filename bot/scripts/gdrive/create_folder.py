"""
Create a Google Drive folder in specified parent folder

python -m bot.scripts.gdrive.create_folder --name [..] --parent [ID]
"""
import asyncio

from bot.utils.gdrive import get_or_create_folder

if __name__ == "__main__":
    # Find or create a new folder
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Name of folder to create")
    parser.add_argument("--parent", required=True, help="ID of folder in which to create this folder")
    args = parser.parse_args()

    result = asyncio.run(get_or_create_folder(args.name, args.parent), debug=True)
    print(result)
