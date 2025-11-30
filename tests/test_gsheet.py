# tests/test_gsheet.py
from unittest.mock import patch, MagicMock

from bot.utils.gsheet import (
    get_credentials,
    get_manager,
    spreadsheet_link,
    get_credentials_synchronous,
    open_google_spreadsheet,
    create_google_spreadsheet,
)


class TestGSheet:
    @patch("bot.utils.gsheet.Credentials.from_service_account_file")
    def test_get_credentials(self, mock_from_file):
        """Test that get_credentials returns proper credentials"""
        # Mock the credential object
        mock_creds = MagicMock()
        mock_from_file.return_value = mock_creds

        creds = get_credentials()
        assert creds is not None
        mock_from_file.assert_called_once_with("google_secrets.json")

    @patch("bot.utils.gsheet.gspread_asyncio.AsyncioGspreadClientManager")
    def test_get_manager(self, mock_manager_class):
        """Test that get_manager returns a manager object"""
        # Mock the manager instance
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        manager = get_manager()
        assert manager is not None
        mock_manager_class.assert_called_once_with(get_credentials)

    def test_spreadsheet_link(self):
        """Test that spreadsheet_link creates proper URL"""
        sheet_id = "test123"
        link = spreadsheet_link(sheet_id)
        assert link == f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    @patch("bot.utils.gsheet.ServiceAccountCredentials.from_json_keyfile_name")
    def test_get_credentials_synchronous(self, mock_from_json):
        """Test that get_credentials_synchronous returns proper credentials"""
        # Mock the credential object
        mock_creds = MagicMock()
        mock_from_json.return_value = mock_creds

        scopes = ["https://spreadsheets.google.com/feeds"]
        creds = get_credentials_synchronous(scopes)
        assert creds is not None
        mock_from_json.assert_called_once_with("google_secrets.json", scopes)

    @patch("bot.utils.gsheet.gspread")
    @patch("bot.utils.gsheet.get_credentials")
    def test_open_google_spreadsheet(self, mock_get_credentials, mock_gspread):
        """Test open_google_spreadsheet function"""
        # Mock the credentials
        mock_creds = MagicMock()
        mock_get_credentials.return_value = mock_creds

        # Mock the gspread client
        mock_gc = MagicMock()
        mock_gspread.authorize.return_value = mock_gc

        # Mock the spreadsheet
        mock_spreadsheet = MagicMock()
        mock_gc.open_by_key.return_value = mock_spreadsheet

        result = open_google_spreadsheet("test_id")
        assert result is not None
        mock_gspread.authorize.assert_called_once_with(mock_creds)

    @patch("bot.utils.gsheet.get_credentials")
    @patch("bot.utils.gsheet.build")
    @patch("bot.utils.gsheet.gspread")
    def test_create_google_spreadsheet(self, mock_gspread, mock_build, mock_get_credentials):
        """Test create_google_spreadsheet function"""
        # Mock the credentials
        mock_creds = MagicMock()
        mock_get_credentials.return_value = mock_creds

        # Mock the build function
        mock_drive_api = MagicMock()
        mock_build.return_value = mock_drive_api

        # Mock the drive API response
        mock_drive_api.files().create().execute.return_value = {"id": "test_id"}

        # Mock the gspread client
        mock_gc = MagicMock()
        mock_gspread.authorize.return_value = mock_gc

        # Mock the spreadsheet
        mock_spreadsheet = MagicMock()
        mock_gc.open_by_key.return_value = mock_spreadsheet

        # Mock the permissions
        mock_drive_api.permissions().create().execute.return_value = {}

        result = create_google_spreadsheet("test_title")
        assert result is not None
