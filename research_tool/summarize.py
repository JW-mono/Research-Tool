"""Heuristic intro/results/conclusion extraction from an abstract.

No LLM involved: most abstracts are 3-6 sentences, so this does what it can
with structure. If the abstract has explicit labels (common in PubMed-style
structured abstracts, e.g. "Background: ... Methods: ... Results: ...
Conclusion: ..."), those are used directly. Otherwise it falls back to
splitting the abstract into thirds by sentence position, which is a rough
approximation since most abstracts blend background/results/conclusion
together in just a few sentences.
"""

import re

_INTRO_LABELS = r"(background|objective|objectives|purpose|aim|aims|introduction)"
_RESULTS_LABELS = r"(results|findings|methods and results)"
_CONCLUSION_LABELS = r"(conclusion|conclusions|discussion|summary)"

_LABEL_PATTERN = re.compile(
    rf"(?P<label>{_INTRO_LABELS}|{_RESULTS_LABELS}|{_CONCLUSION_LABELS})\s*:\s*",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _bucket_for_label(label):
    label = label.lower()
    if re.fullmatch(_INTRO_LABELS, label):
        return "introduction"
    if re.fullmatch(_RESULTS_LABELS, label):
        return "results"
    return "conclusion"


def _split_structured(abstract):
    matches = list(_LABEL_PATTERN.finditer(abstract))
    if len(matches) < 2:
        return None

    buckets = {"introduction": [], "results": [], "conclusion": []}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(abstract)
        text = abstract[start:end].strip()
        if text:
            buckets[_bucket_for_label(match.group("label"))].append(text)

    return {k: " ".join(v) for k, v in buckets.items()}


def _split_by_position(abstract):
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(abstract) if s.strip()]
    n = len(sentences)
    if n == 0:
        return {"introduction": "", "results": "", "conclusion": ""}
    if n <= 2:
        # Too short to meaningfully separate; show the whole thing as-is.
        joined = " ".join(sentences)
        return {"introduction": joined, "results": "", "conclusion": ""}

    intro_end = max(1, round(n * 0.35))
    results_end = max(intro_end + 1, round(n * 0.75))

    return {
        "introduction": " ".join(sentences[:intro_end]),
        "results": " ".join(sentences[intro_end:results_end]),
        "conclusion": " ".join(sentences[results_end:]),
    }


def summarize_abstract(abstract):
    """Return {"introduction": str, "results": str, "conclusion": str}.

    Uses labeled sections when the abstract is structured; otherwise falls
    back to a naive positional split. Always returns all three keys, empty
    string if nothing could be attributed to that section.
    """
    abstract = (abstract or "").strip()
    if not abstract:
        return {"introduction": "", "results": "", "conclusion": ""}

    structured = _split_structured(abstract)
    if structured:
        return structured

    return _split_by_position(abstract)
