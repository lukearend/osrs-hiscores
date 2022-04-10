""" Common knowledge. """

import json

from functools import cache
from pathlib import Path
from typing import List, OrderedDict, Dict, Any


@cache
def osrs_skills(include_total: bool = False) -> List[str]:
    """ Load the list of OSRS skills in an order for use throughout the project. """

    file = Path(__file__).resolve().parents[2] / "ref" / "osrs-skills.json"
    with open(file, 'r') as f:
        skills = json.load(f)
    if include_total:
        skills.insert(0, 'total')
    return skills


@cache
def load_splits(file: str = None) -> OrderedDict[str, List[str]]:
    """ Load the 'skill splits' of the dataset for use throughout the project.
    Each split is a subset of skills to be used as features for clustering. """

    if file is None:
        file = Path(__file__).resolve().parents[2] / "ref" / "skill-splits.json"
    with open(file, 'r') as f:
        return json.load(f, object_pairs_hook=OrderedDict)
