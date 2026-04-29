import time

_STATE_STORE: dict[str, dict] = {}
TTL_SECONDS = 300


def save_state(state: str, code_verifier: str):
    _STATE_STORE[state] = {
        "code_verifier": code_verifier,
        "created_at": time.time()
    }


def validate_state(state: str) -> bool:
    data = _STATE_STORE.get(state)

    if not data:
        return False

    if time.time() - data["created_at"] > TTL_SECONDS:
        _STATE_STORE.pop(state, None)
        return False

    return True


def pop_verifier(state: str) -> str | None:
    data = _STATE_STORE.pop(state, None)

    if not data:
        return None

    return data["code_verifier"]