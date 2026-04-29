import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".insighta"
TOKEN_FILE = CONFIG_PATH / "credentials.json"


def save_tokens(access_token: str, refresh_token: str):
    CONFIG_PATH.mkdir(exist_ok=True)

    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    TOKEN_FILE.write_text(json.dumps(data, indent=2))


def load_tokens():
    if not TOKEN_FILE.exists():
        return None

    return json.loads(TOKEN_FILE.read_text())