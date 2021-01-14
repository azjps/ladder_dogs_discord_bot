"""
Maintain a central "nexus" dashboard with links to puzzles, status, and so forth
"""
import logging
import string
from typing import List, Optional

import gspread_asyncio

from bot.utils import urls
from bot.utils.puzzles_data import PuzzleData

logger = logging.getLogger(__name__)


HEADER_ROW = 2
COLUMNS = [
    "name",
    "round_name",
    "channel_mention",
    "hunt_url",
    "google_sheet_url",
    "status",
    "solution",
    "priority",
    "puzzle_type",
    "notes",
    "start_time",
    "solve_time",
]


async def update_nexus(agcm: gspread_asyncio.AsyncioGspreadClientManager, file_id: str, puzzles: List[PuzzleData]):
    # Always authorize first.
    # If you have a long-running program call authorize() repeatedly.
    agc = await agcm.authorize()

    nexus_sheet = await agc.open_by_key(file_id)

    # Get reference to first spreadsheet
    zero_ws = await nexus_sheet.get_worksheet(0)

    # Update puzzle contents
    cell_range = await zero_ws.range(HEADER_ROW, 1, HEADER_ROW + len(puzzles), len(COLUMNS))
    cell_index = 0
    for column in COLUMNS:
        cell_range[cell_index].value = string.capwords(column.replace("-", " "))
        cell_index += 1
    for puzzle in puzzles:
        for column in COLUMNS:
            if column == "google_sheet_url" and puzzle.google_sheet_id:
                cell_range[cell_index].value = urls.spreadsheet_url(puzzle.google_sheet_id)
            else:
                cell_range[cell_index].value = str(getattr(puzzle, column, ""))
            cell_index += 1
    assert cell_index == len(cell_range)
    await zero_ws.update_cells(cell_range)
    logger.info(f"Finished updating nexus spreadsheet with {len(puzzles)} puzzles")


if __name__ == "__main__":
    # Simple demo CLI, run as
    # python -m bot.utils.gsheet_nexus --sheet [] --guild []
    import argparse
    import asyncio
    from bot.utils.gsheet import get_credentials
    from bot.utils.puzzles_data import PuzzleJsonDb

    logging.basicConfig(level=logging.DEBUG)

    # Create an AsyncioGspreadClientManager object which
    # will give us access to the Spreadsheet API.
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_credentials)

    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", "--sheet-id", required=True, help="ID (in URL) of Nexus Google Sheet")
    parser.add_argument("--guild", "--guild-id", required=True, type=int, help="ID of Discord Guild with puzzle metadata")
    args = parser.parse_args()

    # Turn on debugging if you're new to asyncio!
    asyncio.run(update_nexus(agcm, args.sheet, PuzzleJsonDb.get_all(args.guild)), debug=True)
