#!/usr/bin/env python3
"""Entry point: python find_free_copy.py "<DOI or text/URL containing a DOI>"

Checks OpenAlex's open-access data (Unpaywall, repositories, PMC, etc.) for
a legal free copy of a specific paper -- for when you hit a paywall on one
article you already have a link/DOI for, outside of a topic search.
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from research_tool.oa_finder import find_legal_copy


def main():
    if len(sys.argv) < 2:
        print('Usage: python find_free_copy.py "<DOI or URL containing a DOI>"')
        return 1

    query = " ".join(sys.argv[1:])
    result = find_legal_copy(query)

    if not result["found"]:
        print(f"Could not look this up: {result['reason']}")
        if result["doi"] is None:
            print("Paste the DOI (e.g. 10.1093/mam/ozae134) rather than just the article URL --")
            print("publisher URLs don't always embed the DOI directly.")
        return 1

    print(f"Title:     {result['title']}")
    print(f"Journal:   {result['journal'] or 'Unknown'}")
    print(f"Publisher: {result['publisher'] or 'Unknown'}")
    print(f"DOI:       {result['doi']}")
    print()

    if result["is_oa"] and result["oa_url"]:
        print(f"Free legal copy found ({result['oa_status']}):")
        print(f"  {result['oa_url']}")
    else:
        print("No free legal copy found in OpenAlex/Unpaywall data.")
        print("Check TU Delft Library access, or request via interlibrary loan.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
