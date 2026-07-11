"""Determine whether a publication is likely accessible to a TU Delft user."""

import json
import os

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "tudelft_publishers.json",
)


def _load_publishers():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [p.lower() for p in data["publishers"]]


_PUBLISHERS = _load_publishers()

OPEN_ACCESS = "Open Access (free for anyone)"
TUD_ACCESS = "TU Delft subscription (likely)"
NO_ACCESS = "Not covered - check Library / request via ILL"
UNKNOWN = "Unknown publisher - check Library manually"


def check_access(publication):
    """Return one of the access-status constants above for a publication dict
    as produced by research_tool.openalex.search_publications.
    """
    if publication.get("is_oa"):
        return OPEN_ACCESS

    publisher = (publication.get("publisher") or "").strip()
    if not publisher:
        return UNKNOWN

    publisher_lower = publisher.lower()
    for known in _PUBLISHERS:
        if known in publisher_lower or publisher_lower in known:
            return TUD_ACCESS

    return NO_ACCESS
