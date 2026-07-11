# Research Tool

A command-line tool that searches academic publications on a topic, flags
whether TU Delft likely gives you access to the full text, and breaks each
abstract into introduction / results / conclusion so you can scan results
faster.

## Usage

No dependencies to install — it only uses the Python standard library.

```
python search.py "topic you're researching"
```

Options:

```
python search.py "topic" --limit 25 --sort access --csv results.csv --json results.json --mailto you@tudelft.nl
```

- `--limit N` — number of results to fetch (default 15)
- `--sort access` — group likely-accessible results first instead of by relevance
- `--csv PATH` / `--json PATH` — also export the results
- `--mailto EMAIL` — sent to OpenAlex's "polite pool" for faster, more reliable responses (optional but recommended)

## How it works

1. **Search** — queries the [OpenAlex](https://openalex.org) API (free, no key required) for publications matching your topic.
2. **Accessibility check** — flags each result as:
   - *Open Access* — free for anyone, no institution needed
   - *TU Delft subscription (likely)* — publisher matches `data/tudelft_publishers.json`, a curated list of publishers TU Delft has consortial/subscription access to (Elsevier, Springer, Wiley, IEEE, ACM, etc.)
   - *Not covered* — likely needs an interlibrary loan request
   - *Unknown publisher* — couldn't determine the publisher from metadata

   This list is a best-effort approximation, not pulled from TU Delft's actual
   subscription database (no public API exists for that). Edit
   `data/tudelft_publishers.json` if you find it's missing or wrongly
   including a publisher — check the [TU Delft Library](https://www.tudelft.nl/library)
   catalog to confirm access to a specific title.
3. **Summary** — since only abstracts are available (not full text, unless
   open access), each abstract is split into introduction/results/conclusion.
   If the abstract already has structured labels (e.g. "Background: ...
   Results: ... Conclusion: ..."), those are used directly. Otherwise it's a
   rough positional split (early sentences = introduction, middle = results,
   final sentences = conclusion) — treat it as a skim aid, not a substitute
   for reading the abstract.

## Project layout

```
search.py                          entry point
research_tool/
  openalex.py                      OpenAlex API client + abstract reconstruction
  accessibility.py                 TU Delft access-status logic
  summarize.py                     abstract -> intro/results/conclusion heuristic
  cli.py                           argument parsing, report printing, CSV/JSON export
data/
  tudelft_publishers.json          curated publisher list (edit as needed)
```
