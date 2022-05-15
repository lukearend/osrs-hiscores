import base64
import os
from pathlib import Path


def assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / 'assets'


def load_icon_b64(skill: str):
    file = os.path.join(assets_dir(), 'icons', skill + '.png')
    with open(file, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')
