import argparse
import csv
import json
import sys
import textwrap

from research_tool.openalex import search_publications
from research_tool.accessibility import check_access
from research_tool.summarize import summarize_abstract


def _wrap(text, width=88, indent="      "):
    if not text:
        return f"{indent}(not available)"
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


def _print_report(records):
    for i, r in enumerate(records, 1):
        print("=" * 90)
        print(f"[{i}] {r['title']} ({r['year'] or 'n.d.'})")
        authors = ", ".join(a for a in r["authors"] if a) or "Unknown authors"
        print(f"    Authors:  {authors}")
        print(f"    Journal:  {r['journal'] or 'Unknown'}")
        print(f"    Publisher: {r['publisher'] or 'Unknown'}")
        if r["doi"]:
            print(f"    DOI:      {r['doi']}")
        print(f"    Access:   {r['access_status']}")
        if r["is_oa"] and r["oa_url"]:
            print(f"    OA link:  {r['oa_url']}")
        print()
        print("    Introduction:")
        print(_wrap(r["summary"]["introduction"]))
        print("    Results:")
        print(_wrap(r["summary"]["results"]))
        print("    Conclusion:")
        print(_wrap(r["summary"]["conclusion"]))
        print()


def _write_csv(records, path):
    fields = [
        "title", "year", "authors", "journal", "publisher", "doi",
        "access_status", "oa_url", "summary_introduction",
        "summary_results", "summary_conclusion",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "title": r["title"],
                "year": r["year"],
                "authors": "; ".join(a for a in r["authors"] if a),
                "journal": r["journal"],
                "publisher": r["publisher"],
                "doi": r["doi"],
                "access_status": r["access_status"],
                "oa_url": r["oa_url"],
                "summary_introduction": r["summary"]["introduction"],
                "summary_results": r["summary"]["results"],
                "summary_conclusion": r["summary"]["conclusion"],
            })


def _write_json(records, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def build_records(topic, limit, mailto):
    publications = search_publications(topic, limit=limit, mailto=mailto)
    records = []
    for pub in publications:
        pub["access_status"] = check_access(pub)
        pub["summary"] = summarize_abstract(pub["abstract"])
        records.append(pub)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="search.py",
        description=(
            "Search academic publications on a topic, flag whether TU Delft "
            "likely has access, and summarize each abstract into "
            "introduction/results/conclusion."
        ),
    )
    parser.add_argument("topic", help="Research topic / search query")
    parser.add_argument("--limit", type=int, default=15, help="Max results (default: 15)")
    parser.add_argument(
        "--sort",
        choices=["relevance", "access"],
        default="relevance",
        help="Sort by relevance (default) or group accessible results first",
    )
    parser.add_argument("--csv", help="Also write results to this CSV file")
    parser.add_argument("--json", help="Also write results to this JSON file")
    parser.add_argument(
        "--mailto",
        help="Your email, sent to OpenAlex's polite pool for faster/more reliable responses",
    )
    args = parser.parse_args(argv)

    try:
        records = build_records(args.topic, args.limit, args.mailto)
    except Exception as exc:  # network/API errors surface directly to the user
        print(f"Error fetching publications: {exc}", file=sys.stderr)
        return 1

    if not records:
        print("No publications found for that topic.")
        return 0

    if args.sort == "access":
        priority = {
            "Open Access (free for anyone)": 0,
            "TU Delft subscription (likely)": 1,
            "Unknown publisher - check Library manually": 2,
            "Not covered - check Library / request via ILL": 3,
        }
        records.sort(key=lambda r: priority.get(r["access_status"], 99))

    _print_report(records)

    accessible = sum(
        1 for r in records
        if r["access_status"] in ("Open Access (free for anyone)", "TU Delft subscription (likely)")
    )
    print(f"{accessible}/{len(records)} results are likely accessible to you.")

    if args.csv:
        _write_csv(records, args.csv)
        print(f"Wrote CSV to {args.csv}")
    if args.json:
        _write_json(records, args.json)
        print(f"Wrote JSON to {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
