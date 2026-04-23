import hashlib
import json
from datetime import datetime


def generate_event_hash(event_type: str, payload: dict, prev_hash: str) -> str:
    content = f"{event_type}:{json.dumps(payload, sort_keys=True)}:{prev_hash}:{datetime.utcnow().isoformat()}"
    return "0x" + hashlib.sha256(content.encode()).hexdigest()
