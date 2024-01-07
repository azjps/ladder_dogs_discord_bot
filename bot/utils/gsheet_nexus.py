"""
Maintain a central "nexus" dashboard with links to puzzles, status, and so forth
"""
import logging
import string
from typing import List

import gspread_asyncio

from bot.utils import urls
from bot.database.models import PuzzleData

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


async def update_nexus(agcm: gspread_asyncio.AsyncioGspreadClientManager, file_id: str, puzzles: List[PuzzleData], hunt_name: str, round_name: str):
    # Always authorize first.
    # If you have a long-running program call authorize() repeatedly.
    agc = await agcm.authorize()

    nexus_sheet = await agc.open_by_key(file_id)

    # Get reference to first spreadsheet
    zero_ws = await nexus_sheet.get_worksheet(0)

    # Update puzzle contents
    cell_range = await zero_ws.range(HEADER_ROW, 1, HEADER_ROW + len(puzzles), len(COLUMNS))
    cell_index = 0
    update_count = 0
    for column in COLUMNS:
        cell_range[cell_index].value = string.capwords(column.replace("_", " "))
        cell_index += 1
    for puzzle in puzzles:
        if puzzle.puzzle_type == "discussion":
            continue
        update_count = update_count + 1
        for column in COLUMNS:
            if column == "google_sheet_url" and puzzle.google_sheet_id:
                cell_range[cell_index].value = urls.spreadsheet_url(puzzle.google_sheet_id)
            else:
                cell_range[cell_index].value = str(getattr(puzzle, column, ""))
            cell_index += 1
    await zero_ws.update_cells(cell_range)
    logger.info(f"Finished updating {hunt_name}/{round_name} nexus spreadsheet with {update_count} puzzles")

