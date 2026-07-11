"""Fetch publication metadata from the OpenAlex API (https://openalex.org)."""

import urllib.parse
import urllib.request
import json

API_URL = "https://api.openalex.org/works"


def _reconstruct_abstract(inverted_index):
    """OpenAlex stores abstracts as {word: [positions]}; rebuild the plain text."""
    if not inverted_index:
        return ""
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def search_publications(topic, limit=20, mailto=None):
    """Search OpenAlex for works matching `topic`, sorted by relevance.

    `mailto` adds your email to the request per OpenAlex's polite pool
    guidance, which gets you faster, more reliable responses.
    """
    params = {
        "search": topic,
        "per-page": min(limit, 200),
        "sort": "relevance_score:desc",
    }
    if mailto:
        params["mailto"] = mailto

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.load(resp)

    results = []
    for work in payload.get("results", []):
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        open_access = work.get("open_access") or {}

        results.append({
            "title": work.get("title") or "(untitled)",
            "year": work.get("publication_year"),
            "doi": work.get("doi"),
            "journal": source.get("display_name"),
            "publisher": source.get("host_organization_name"),
            "is_oa": bool(open_access.get("is_oa")),
            "oa_status": open_access.get("oa_status"),
            "oa_url": open_access.get("oa_url"),
            "authors": [
                a.get("author", {}).get("display_name")
                for a in work.get("authorships", [])
                if a.get("author")
            ],
            "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
        })
    return results
