"""Google spreadsheet related.

asyncio packages required: gspread_asyncio, oauth2client, google-api-python-client
non-asyncio: gspread, cryptography, oauth2client, google-api-python-client
"""
from typing import Optional
import logging

# asyncio imports
import gspread_asyncio
# from google-auth package
from google.oauth2.service_account import Credentials

# non-asyncio imports
import gspread
from gspread import Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build


logger = logging.getLogger(__name__)


# First, set up a callback function that fetches our credentials off the disk.
# gspread_asyncio needs this to re-authenticate when credentials expire.
def get_credentials(scopes: Optional[list] = None) -> Credentials:
    # To obtain a service account JSON file, follow these steps:
    # https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account
    creds = Credentials.from_service_account_file("google_secrets.json")
    scoped = creds.with_scopes(
        scopes
        or [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    return scoped


def get_manager() -> gspread_asyncio.AsyncioGspreadClientManager:
    return gspread_asyncio.AsyncioGspreadClientManager(get_credentials)


def spreadsheet_link(sheet_id: str):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


async def create_spreadsheet(
    agcm: gspread_asyncio.AsyncioGspreadClientManager,
    title: str,
    folder_id: Optional[str] = None,
    share_anyone: bool = True,
) -> gspread_asyncio.AsyncioGspreadSpreadsheet:
    """Create a new Google Spreadsheet. Wraps
        :meth:`gspread.Client.create`.

        :param str title: Human-readable name of the new spreadsheet.
        :param bool share_anyone: Anyone with link can edit
        :rtype: :class:`gspread_asyncio.AsyncioGspreadSpreadsheet`
        """
    agc = await agcm.authorize()

    # Re-implmented from gspread_asyncio for folder_id.
    # NOTE: now merged in https://github.com/dgilman/gspread_asyncio/pull/30
    ss = await agc.agcm._call(agc.gc.create, title, folder_id=folder_id)
    sheet = gspread_asyncio.AsyncioGspreadSpreadsheet(agc.agcm, ss)
    agc._ss_cache_title[title] = sheet
    agc._ss_cache_key[ss.id] = sheet

    if share_anyone:
        # Allow anyone with the URL to write to this spreadsheet.
        await agc.insert_permission(sheet.id, None, perm_type="anyone", role="writer")

    logger.info(f"Created spreadsheet at URL: {spreadsheet_link(sheet.id)}")
    return sheet


# async def example(agcm: gspread_asyncio.AsyncioGspreadClientManager):
#     # Always authorize first.
#     # If you have a long-running program call authorize() repeatedly.
#     agc = await agcm.authorize()
#
#     ss = await create_spreadsheet(agcm, "Test Spreadsheet")
#     print("Spreadsheet URL: https://docs.google.com/spreadsheets/d/{0}".format(ss.id))
#     print("Open the URL in your browser to see gspread_asyncio in action!")
3
#     # Allow anyone with the URL to write to this spreadsheet.
#     await agc.insert_permission(ss.id, None, perm_type="anyone", role="writer")
#
#     # Create a new spreadsheet but also grab a reference to the default one.
#     ws = await ss.add_worksheet("My Test Worksheet", 10, 5)
#     zero_ws = await ss.get_worksheet(0)
#
#     # Write some stuff to both spreadsheets.
#     for row in range(1, 11):
#         for col in range(1, 6):
#             val = "{0}/{1}".format(row, col)
#             await ws.update_cell(row, col, val + " ws")
#             await zero_ws.update_cell(row, col, val + " zero ws")
#     print("All done!")

# Create an AsyncioGspreadClientManager object which
# will give us access to the Spreadsheet API.
# agcm = gspread_asyncio.AsyncioGspreadClientManager(get_credentials)

# Turn on debugging if you're new to asyncio!
# asyncio.run(example(agcm), debug=True)


### Non-async API ###
# ref: Ref: https://gist.github.com/miohtama/f988a5a83a301dd27469
def get_credentials_synchronous(scopes: list) -> ServiceAccountCredentials:
    """Read Google's JSON permission file.
    https://developers.google.com/api-client-library/python/auth/service-accounts#example
    :param scopes: List of scopes we need access to
    """
    credentials = ServiceAccountCredentials.from_json_keyfile_name("google_secrets.json", scopes)
    return credentials


def open_google_spreadsheet(spreadsheet_id: str) -> Spreadsheet:
    """Open sheet using gspread.
    :param spreadsheet_id: Grab spreadsheet id from URL to open. Like *1jMU5gNxEymrJd-gezJFPv3dQCvjwJs7QcaB-YyN_BD4*.
    """
    credentials = get_credentials(["https://spreadsheets.google.com/feeds"])
    gc = gspread.authorize(credentials)
    return gc.open_by_key(spreadsheet_id)


def create_google_spreadsheet(
    title: str, parent_folder_ids: list = None, share_anyone: bool = False, share_domains: list = None
) -> Spreadsheet:
    """Create a new spreadsheet and open gspread object for it.
    .. note ::
        Created spreadsheet is not instantly visible in your Drive search and you need to access it by direct link.
    :param title: Spreadsheet title
    :param parent_folder_ids: A list of strings of parent folder ids (if any).
    :param share_domains: List of Google Apps domain whose members get full access rights to the created sheet. Very handy, otherwise the file is visible only to the service worker itself. Example:: ``["redinnovation.com"]``.
    """

    credentials = get_credentials(["https://www.googleapis.com/auth/drive"])

    drive_api = build("drive", "v3", credentials=credentials)

    logger.info("Creating Sheet %s", title)
    body = {"name": title, "mimeType": "application/vnd.google-apps.spreadsheet"}

    if parent_folder_ids:
        body["parents"] = parent_folder_ids
        # [{"kind": "drive#fileLink", "id": parent_folder_ids}]

    req = drive_api.files().create(body=body)
    new_sheet = req.execute()

    # Get id of fresh sheet
    spread_id = new_sheet["id"]

    # Grant permissions
    if share_anyone:
        permission = {
            "type": "anyone",
            "role": "writer",
            # 'domain': domain,
            # Magic almost undocumented variable which makes files appear in your Google Drive
            "allowFileDiscovery": True,
        }
        req = drive_api.permissions().create(fileId=spread_id, body=permission, fields="id")
        req.execute()
        print("Shared!")

    elif share_domains:
        for domain in share_domains:

            # https://developers.google.com/drive/v3/web/manage-sharing#roles
            # https://developers.google.com/drive/v3/reference/permissions#resource-representations
            domain_permission = {
                "type": "domain",
                "role": "writer",
                "domain": domain,
                # Magic almost undocumented variable which makes files appear in your Google Drive
                "allowFileDiscovery": True,
            }

            req = drive_api.permissions().create(fileId=spread_id, body=domain_permission, fields="id")

            req.execute()

    spread = open_google_spreadsheet(spread_id)

    return spread
