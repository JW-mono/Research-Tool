#!/usr/bin/env python3
"""Entry point: python search.py "your research topic" """

import sys

# Publication metadata routinely contains non-ASCII characters (accents, en/em
# dashes, etc). Windows consoles often default to a codepage (e.g. cp1252)
# that can't encode them, so force UTF-8 output to avoid crashing mid-report.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from research_tool.cli import main

if __name__ == "__main__":
    sys.exit(main())
