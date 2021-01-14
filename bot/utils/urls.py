import re
from typing import Optional

REGEX_DRIVE_ID = re.compile(r"[-\w]{25,}")
REGEX_DRIVE_URL = re.compile(r".*/d/(?P<id>[-\w]{25,})[^-\w]?.*")

def spreadsheet_url(sheet_id: str) -> str:
    if sheet_id.startswith("https://"):
        return sheet_id
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"

def docs_url(file_id: str) -> str:
    if file_id.startswith("https://"):
        return file_id
    return f"https://docs.google.com/document/d/{file_id}"

def drive_folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/u/0/folders/{folder_id}"

def extract_id_from_url(url: str) -> Optional[str]:
    m = re.match(REGEX_DRIVE_URL, url)
    if m:
        return m["id"]
    m = re.match(REGEX_DRIVE_ID, url)
    if m:
        return url
    return None
