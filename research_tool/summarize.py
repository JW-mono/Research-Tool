"""LLM-based abstract summarization via the Claude API.

Uses claude-haiku-4-5: this is a short, well-specified extraction task (a
~150-300 word abstract in, three short structured fields out) run in a loop
over every search result. Haiku matches that complexity at a fraction of the
cost and latency of Sonnet/Opus, with no quality loss for structured
extraction from a single short input -- there's no multi-step reasoning or
long-context work here that would need a bigger model.
"""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import anthropic
from pydantic import BaseModel

MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = (
    "You summarize academic abstracts for a researcher skimming search results. "
    "Given an abstract, extract three short sections in your own words: "
    "introduction (the background/motivation), results (what was found or done), "
    "and conclusion (the takeaway/implication). One to two sentences each. "
    "If the abstract doesn't contain enough information for a section, "
    "return an empty string for it rather than guessing."
)

def _summary(introduction="", results="", conclusion="", status="ok", error=None):
    return {
        "introduction": introduction,
        "results": results,
        "conclusion": conclusion,
        "status": status,  # "ok" | "no_abstract" | "error"
        "error": error,
    }


class AbstractSummary(BaseModel):
    introduction: str
    results: str
    conclusion: str


class MissingAPIKeyError(RuntimeError):
    pass


_client = None
_warned_lock = threading.Lock()
_warned = False


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def _warn_once(message):
    global _warned
    with _warned_lock:
        if _warned:
            return
        _warned = True
    print(f"Warning: {message}", file=sys.stderr)


def summarize_abstract(abstract):
    """Return a dict with introduction/results/conclusion text plus a
    "status" of "ok" (summarized normally), "no_abstract" (OpenAlex didn't
    have an abstract for this result -- nothing to summarize, not a failure),
    or "error" (the Claude API call failed -- see the "error" field).
    """
    abstract = (abstract or "").strip()
    if not abstract:
        return _summary(status="no_abstract")

    missing_key_message = (
        "ANTHROPIC_API_KEY is not set (or is invalid). Set it in your "
        "environment before running, e.g.:\n"
        '  setx ANTHROPIC_API_KEY "sk-ant-..."   (Windows, new terminals)\n'
        '  $env:ANTHROPIC_API_KEY = "sk-ant-..."   (PowerShell, this session)'
    )

    try:
        response = _get_client().messages.parse(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": abstract}],
            output_format=AbstractSummary,
        )
    except anthropic.AuthenticationError as exc:
        raise MissingAPIKeyError(missing_key_message) from exc
    except TypeError as exc:
        # The SDK raises a plain TypeError (not AuthenticationError) when no
        # credentials are configured at all, before any network call is made.
        if "authentication" in str(exc).lower():
            raise MissingAPIKeyError(missing_key_message) from exc
        raise
    except anthropic.APIError as exc:
        message = f"{type(exc).__name__}: {exc}"
        _warn_once(
            f"Claude API call failed ({message}). "
            "Affected results will show this error instead of a summary until it's resolved."
        )
        return _summary(status="error", error=message)

    parsed = response.parsed_output
    if parsed is None:
        message = f"Claude returned no parsed output (stop_reason={response.stop_reason!r})"
        _warn_once(message + ". Affected results will show this error until it's resolved.")
        return _summary(status="error", error=message)

    fields = parsed.model_dump()
    return _summary(status="ok", **fields)


def summarize_abstracts(abstracts, max_workers=5):
    """Summarize many abstracts concurrently, preserving input order."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(summarize_abstract, abstracts))
