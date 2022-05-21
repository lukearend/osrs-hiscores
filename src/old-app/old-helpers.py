import base64
import string
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from src.data.io import load_json


def assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / 'assets'


@lru_cache()
def load_table_layout(flat: bool = False) -> List[List[str]]:
    layout = load_json(assets_dir() / 'table_layout.json')
    return [skill for row in layout for skill in row] if flat else layout


@lru_cache()
def load_skill_icon(skill) -> str:
    path = os.path.join(assets_dir(), 'icons', f'{skill}_icon.png')
    with open(path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    return f'data:image/png;base64,{img_b64}'


def validate_username(username):
    if len(username) > 12:
        return False
    if username.strip(string.ascii_lowercase + string.ascii_uppercase + string.digits + ' -_'):
        return False
    return True


def format_skill(skill):
    return f"{skill.capitalize()} level"


def get_color_label(skill):
    return f"{skill.capitalize()}\nlevel"


def get_point_size(ptsize_name):
    return {'small': 1, 'medium': 2, 'large': 3}[ptsize_name]


def get_level_tick_marks(skill):
    if skill == 'total':
        return [500, 750, 1000, 1250, 1500, 1750, 2000, 2277]
    return [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
