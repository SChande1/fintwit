import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")


def _empty_state():
    return {
        "seen_ids": [],
        "daily_tweets": [],
        "summary_sent_date": None,
        "mentioned_accounts": {},
    }


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return _empty_state()


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
