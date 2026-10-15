"""Helpers for reading Server-Sent Events in tests."""

import json


def parse_sse(body: str) -> list[dict]:
    """Return the JSON payload of every `data:` event in an SSE body."""
    events = []
    for frame in body.split("\n\n"):
        for line in frame.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events
