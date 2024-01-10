"""
aiogoogle utilities for finding and creating folders in Google Drive
"""
import json
import logging
from typing import Optional

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

# Not sure if this can be consolidated with the gspread_asyncio credentials?
creds = ServiceAccountCreds(
    scopes=["https://www.googleapis.com/auth/drive"], **json.load(open("google_secrets.json"))
)

logger = logging.getLogger(__name__)


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
                fields="files(id, name)",
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


async def rename_file(file_id: str, name_lambda: callable) -> dict:
    """Rename file

    Ref: https://developers.google.com/drive/api/v3/reference/files/update

    Args:
        name_lambda: method which takes original name and returns new name
    """
    aiogoogle = Aiogoogle(service_account_creds=creds)
    async with aiogoogle:
        drive_v3 = await aiogoogle.discover("drive", "v3")
        result = await aiogoogle.as_service_account(
            drive_v3.files.get(
                fileId=file_id,
            )
        )
        try:
            name = result["name"]
        except KeyError:
            logger.exception(f"Unable to get name field for {file_id} from {result}")
            raise
        new_name = name_lambda(name)
        if name != new_name:
            payload = {"name": new_name}
            result = await aiogoogle.as_service_account(
                drive_v3.files.update(
                    json=payload,
                    fileId=file_id,
                )
            )
    return result  # {"name": .., "id": .., "kind": .., "mimeType": ..}
