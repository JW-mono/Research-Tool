"""Look up whether a legal free copy of a paper exists, given its DOI.

Pure metadata lookup against the OpenAlex API (which aggregates Unpaywall,
institutional repositories, PubMed Central, etc.) -- never touches the
publisher's own site, so there's nothing paywall- or access-control-related
here. This is the same mechanism services like Unpaywall use.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)


def extract_doi(text):
    """Pull a DOI out of free text (a bare DOI, a doi.org URL, a citation, ...)."""
    match = DOI_PATTERN.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip(".,)")


def find_legal_copy(doi_or_text, mailto=None):
    """Given a DOI (or text containing one), return:

    {"found": bool, "doi": str|None, "reason": str,  # only when found=False
     "title": str, "journal": str, "publisher": str,
     "is_oa": bool, "oa_status": str|None, "oa_url": str|None}
    """
    doi = extract_doi(doi_or_text)
    if not doi:
        return {"found": False, "doi": None, "reason": "No DOI found in the input."}

    url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi, safe='')}"
    if mailto:
        url += f"?{urllib.parse.urlencode({'mailto': mailto})}"

    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"found": False, "doi": doi, "reason": "DOI not found in OpenAlex."}
        raise

    open_access = data.get("open_access") or {}
    source = ((data.get("primary_location") or {}).get("source")) or {}

    return {
        "found": True,
        "doi": doi,
        "title": data.get("title"),
        "journal": source.get("display_name"),
        "publisher": source.get("host_organization_name"),
        "is_oa": bool(open_access.get("is_oa")),
        "oa_status": open_access.get("oa_status"),
        "oa_url": open_access.get("oa_url"),
    }
