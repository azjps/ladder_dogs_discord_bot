"""
aiogoogle utilities for finding and creating folders in Google Drive
"""
import asyncio
import json
from typing import Optional

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

# Not sure if this can be consolidated with the gspread_asyncio credentials?
creds = ServiceAccountCreds(scopes=["https://www.googleapis.com/auth/drive"], **json.load(open("google_secrets.json")))


async def create_folder(name: str, parent_id: Optional[str] = None) -> dict:
    aiogoogle = Aiogoogle(service_account_creds=creds)
    async with aiogoogle:
        drive_v3 = await aiogoogle.discover("drive", "v3")
        payload = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            payload["parents"] = [parent_id]
        result = await aiogoogle.as_service_account(
            drive_v3.files.create(json=payload, fields="id")
        )
    return result  # {"id": ".. folder_id .."}


async def find_folder(name: str, parent_id: str) -> dict:
    aiogoogle = Aiogoogle(service_account_creds=creds)
    async with aiogoogle:
        drive_v3 = await aiogoogle.discover("drive", "v3")
        result = await aiogoogle.as_service_account(
            drive_v3.files.list(
                q=f"mimeType='application/vnd.google-apps.folder' "
                f"and name = '{name}' and parents in '{parent_id}'",
                spaces="drive",
                fields="files(id, name)"
            )
        )
    return result  # {"files": [{"id": .., "name": ..}]}


async def get_or_create_folder(name: str, parent_id: str) -> dict:
    """Find folder inside existing folder
    
    Args:
        parent_id: ID of parent folder in Drive URL
    """
    existing_folder = await find_folder(name, parent_id)
    if existing_folder.get("files"):
        existing_folder = existing_folder["files"][0]
        existing_folder["created"] = False
        return existing_folder
    
    created_folder = await create_folder(name, parent_id)
    created_folder["name"] = name
    created_folder["created"] = True
    return created_folder


if __name__ == "__main__":
    # Find or create a new folder
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Name of folder to create")
    parser.add_argument("--parent", required=True, help="ID of folder in which to create this folder")
    args = parser.parse_args()

    result = asyncio.run(get_or_create_folder(args.name, args.parent), debug=True)
    print(result)
