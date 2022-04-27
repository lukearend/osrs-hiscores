""" Top-level definitions. """

import json
from functools import lru_cache
from pathlib import Path
from typing import List


@lru_cache()
def osrs_skills(include_total: bool = False) -> List[str]:
    """ Load the list of OSRS skills in an order for use throughout the project. """

    file = Path(__file__).resolve().parents[2] / "ref" / "osrs-skills.json"
    with open(file, 'r') as f:
        skill_names = json.load(f)
    if include_total:
        skill_names.insert(0, 'total')
    return skill_names


@lru_cache()
def csv_api_stats() -> List[str]:
    """ Load the list of header fields returned from the OSRS hiscores CSV API. """

    file = Path(__file__).resolve().parents[2] / "ref" / "csv-api-stats.json"
    with open(file, 'r') as f:
        stat_names = json.load(f)
        assert stat_names[:3] == ['total_rank', 'total_level', 'total_xp']
        return stat_names