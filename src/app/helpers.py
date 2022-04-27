import string
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from src.analysis.data import load_json


def assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / 'assets'


@lru_cache()
def load_table_layout(flat: bool = False) -> List[List[str]]:
    layout = load_json(assets_dir() / 'table_layout.json')
    return [skill for row in layout for skill in row] if flat else layout


@lru_cache()
def load_boxplot_offsets(split) -> Tuple[float, float]:
    xy_offsets = load_json(assets_dir() / 'boxplot_offsets.json')
    return tuple(xy_offsets[split])


@lru_cache()
def load_boxplot_icon(skill) -> Image:
    path = os.path.join(assets_dir(), "icons", f"{skill}_icon.png")
    return Image.open(path)


def validate_username(username):
    if len(username) > 12:
        return False
    if username.strip(string.ascii_lowercase + string.ascii_uppercase + string.digits + ' -_'):
        return False
    return True


def skill_upper(skill):
    return skill[0].upper() + skill[1:]


def format_skill(skill):
    return f"{skill_upper(skill)} level"


def get_color_label(skill):
    return f"{skill_upper(skill)}\nlevel"


def get_color_range(skill):
    return [500, 2277] if skill == 'total' else [1, 99]


def get_point_size(ptsize_name):
    return {'small': 1, 'medium': 2, 'large': 3}[ptsize_name]


def get_level_tick_marks(skill):
    if skill == 'total':
        return {i: str(i) for i in [1, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2277]}
    return {i: str(i) for i in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]}
