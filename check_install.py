"""Check that your Robin is really working, end to end.

Run it after the install, and any time something looks wrong:

    .venv/Scripts/python.exe check_install.py          # Windows
    .venv/bin/python check_install.py                  # macOS / Linux

It checks, in order: Python, the packages, which keys are present (names only - it never prints a
key), that each service answers, that the look-up corpus is in place, and then - unless you pass
--no-chat - it sends one real message through Robin and reads the trace back out of Langfuse to
confirm the whole chain worked.

That last part is the one that matters. An answer appearing on screen only proves the model
replied; it says nothing about whether the trace arrived, whether the guardrail steps are in it, or
whether your prompts were created. This checks those.

One message costs a fraction of a cent.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    mark = {PASS: "  ok  ", FAIL: " FAIL ", WARN: " warn "}[status]
    print(f"{mark} {name}" + (f" - {detail}" if detail else ""))


REQUIRED_KEYS = {
    "ANTHROPIC_API_KEY": "Claude, for Robin's answers and guardrails (platform.claude.com)",
    "OPENAI_API_KEY": "embeddings for the look-up (platform.openai.com)",
    "LANGFUSE_PUBLIC_KEY": "your Langfuse project (Settings > API Keys)",
    "LANGFUSE_SECRET_KEY": "your Langfuse project (Settings > API Keys)",
}


def check_python() -> None:
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 11):
        record(PASS, "Python version", f"{major}.{minor}")
    else:
        record(FAIL, "Python version", f"{major}.{minor}; Robin needs 3.11 or newer")


def check_packages() -> bool:
    missing = []
    for module in ("flask", "waitress", "langfuse", "anthropic", "openai", "dotenv"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        record(FAIL, "Packages", f"missing: {', '.join(missing)} - run pip install -r requirements.txt")
        return False
    record(PASS, "Packages", "all present")
    return True


def check_keys() -> set[str] | None:
    """Which required keys are not filled in. None means there is no .env at all."""
    from dotenv import load_dotenv

    if not (ROOT / ".env").exists():
        record(FAIL, ".env file", "not found - copy .env.example to .env and fill in your keys")
        return None
    load_dotenv(ROOT / ".env")
    record(PASS, ".env file", "found")

    missing = set()
    for name, what in REQUIRED_KEYS.items():
        value = os.getenv(name, "")
        if not value or value.endswith("..."):
            record(FAIL, name, f"not filled in - needed for {what}")
            missing.add(name)
        else:
            record(PASS, name, "set")  # never print the value
    base = os.getenv("LANGFUSE_BASE_URL", "")
    record(PASS if base else WARN, "LANGFUSE_BASE_URL",
           base or "not set; the SDK will use its default. EU is https://cloud.langfuse.com")
    return missing


def check_claude() -> bool:
    import anthropic

    try:
        anthropic.Anthropic(max_retries=0).models.list(limit=1)
    except Exception as error:  # noqa: BLE001
        record(FAIL, "Claude reachable", f"{type(error).__name__}: {str(error)[:110]}")
        return False
    record(PASS, "Claude reachable", "the key works")
    return True


def check_openai() -> bool:
    from openai import OpenAI

    try:
        OpenAI(max_retries=0).embeddings.create(model="text-embedding-3-small", input=["hello"])
    except Exception as error:  # noqa: BLE001
        record(FAIL, "OpenAI embeddings reachable", f"{type(error).__name__}: {str(error)[:110]}")
        return False
    record(PASS, "OpenAI embeddings reachable", "the key works")
    return True


def check_langfuse() -> bool:
    from langfuse import get_client

    try:
        get_client().api.prompts.list(limit=1)
    except Exception as error:  # noqa: BLE001
        record(FAIL, "Langfuse reachable", f"{type(error).__name__}: {str(error)[:110]}")
        return False
    record(PASS, "Langfuse reachable", "the keys work")
    return True


def check_corpus() -> None:
    import lookup

    if lookup.using_database():
        record(PASS, "Look-up store", "Postgres (DATABASE_URL is set)")
        return
    if not lookup.CHUNKS_FILE.exists():
        record(FAIL, "Look-up store", f"{lookup.CHUNKS_FILE.name} is missing - "
                                      "run python ingestion/ingest_source_docs.py")
        return
    status = lookup.corpus_status()
    if status.get("matches_source") is False:
        record(WARN, "Look-up store",
               "the chunks no longer match source-docs/ - re-run the ingestion to refresh them")
    else:
        record(PASS, "Look-up store",
               f"{lookup.CHUNKS_FILE.name}, corpus {status.get('corpus_version', '?')}")


def check_a_real_turn() -> None:
    """Send one message, then read the trace back out of Langfuse."""
    import anthropic
    from langfuse import get_client
    from openai import OpenAI

    import robin

    try:
        result = robin.handle_turn(
            "Can I return a vase I bought last week?", [],
            client=anthropic.Anthropic(), embed_client=OpenAI(),
            participant="install-check", session_id="install-check",
        )
    except Exception as error:  # noqa: BLE001
        record(FAIL, "Robin answers", f"{type(error).__name__}: {str(error)[:140]}")
        return

    if not result.answer.strip():
        record(FAIL, "Robin answers", f"empty answer, outcome: {result.outcome}")
        return
    record(PASS, "Robin answers", f"outcome: {result.outcome}")

    langfuse = get_client()
    langfuse.flush()

    trace = None
    for _ in range(10):  # Langfuse takes a moment to make a trace readable
        try:
            trace = langfuse.api.trace.get(result.trace_id)
            break
        except Exception:  # noqa: BLE001
            time.sleep(2)
    if trace is None:
        record(FAIL, "Trace arrived in Langfuse",
               f"trace {result.trace_id} was not readable after 20 seconds")
        return
    record(PASS, "Trace arrived in Langfuse", f"id {result.trace_id}")

    names = [getattr(o, "name", "") for o in (getattr(trace, "observations", None) or [])]
    wanted = ["1. Input guardrail", "2. Input guardrail", "3. Robin writes the answer",
              "4. Output guardrail"]
    found = [w for w in wanted if any(n.startswith(w) for n in names)]
    if len(found) == len(wanted):
        record(PASS, "The steps are in the trace", f"{len(names)} observations")
    else:
        record(WARN, "The steps are in the trace",
               f"found {len(found)} of {len(wanted)} expected steps; saw: {', '.join(names) or 'none'}")

    try:
        import prompts as robin_prompts

        existing = {p.name for p in langfuse.api.prompts.list(limit=100).data}
        missing = sorted(set(robin_prompts.LANGFUSE_PROMPTS) - existing)
        if missing:
            record(WARN, "Your prompts were created", f"still missing: {', '.join(missing)}")
        else:
            record(PASS, "Your prompts were created",
                   f"all {len(robin_prompts.LANGFUSE_PROMPTS)} robin/ prompts are in your project")
    except Exception as error:  # noqa: BLE001
        record(WARN, "Your prompts were created", f"could not check: {type(error).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that your Robin works end to end.")
    parser.add_argument("--no-chat", action="store_true",
                        help="skip the real message and the trace check (no API cost)")
    args = parser.parse_args()

    print("Checking your Robin install.\n")
    check_python()
    if not check_packages():
        return report()
    missing = check_keys()
    if missing is None:
        return report()

    # Check everything that can still be checked, so one missing key doesn't hide the next
    # problem. A service whose key isn't filled in is skipped rather than reported twice.
    claude_ok = "ANTHROPIC_API_KEY" not in missing and check_claude()
    openai_ok = "OPENAI_API_KEY" not in missing and check_openai()
    langfuse_ok = not ({"LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"} & missing) and check_langfuse()
    check_corpus()

    if args.no_chat:
        print("\n(skipping the real message, as asked)")
    elif claude_ok and openai_ok and langfuse_ok:
        print("\nSending one real message and reading the trace back...")
        check_a_real_turn()
    else:
        print("\nSkipping the real message until the above is fixed - it needs all three services.")
    return report()


def report() -> int:
    failures = [r for r in results if r[0] == FAIL]
    warnings = [r for r in results if r[0] == WARN]
    print()
    if failures:
        print(f"{len(failures)} thing(s) need fixing:")
        for _, name, detail in failures:
            print(f"  - {name}: {detail}")
        return 1
    if warnings:
        print(f"Working, with {len(warnings)} thing(s) worth a look:")
        for _, name, detail in warnings:
            print(f"  - {name}: {detail}")
        return 0
    print("Everything checks out. Your Robin works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
