"""Builds guardrails-data.json for the "RAG & Guardrails" tab of the dashboard-kit.

One record per Robin chat turn, for both the course chats (environment "course") and the
experiment runs (environment "sdk-experiment"). Each record says what every guardrail did
(PASS / BLOCK / MASKED / ERROR / OFF), what the look-up (RAG) found and how well it matched,
how the turn ended, and the results of the quality checks (the "eval: ..." scores).

Everything comes from what robin.py already writes onto each turn: the metadata of the
"Robin – chat turn" observation, and the evaluator scores attached to it.

Uses Langfuse's newer endpoints (/api/public/v2/observations and /api/public/v3/scores),
not the deprecated ones robin_adapter.py still uses.

Run from the Robin project root with its .env loaded:
    python dashboard-kit/guardrails_adapter.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from robin_adapter import BASE, _get, is_tester  # noqa: E402  (same .env, auth and retry logic)

# Langfuse environment -> the name the dashboard shows.
SOURCES = {"course": "course", "sdk-experiment": "experiment"}
TURN_NAME = "Robin – chat turn"
SECTION_HIT = re.compile(r"([^,(]+?)\s*\(([\d.]+)\)")


def _paged(path: str, **params) -> list[dict]:
    """All pages of a cursor-paged endpoint."""
    rows, cursor = [], None
    while True:
        query = dict(params, limit=100)
        if cursor:
            query["cursor"] = cursor
        page = _get(path, **query)
        rows.extend(page["data"])
        cursor = (page.get("meta") or {}).get("cursor")
        if not cursor or not page["data"]:
            return rows
        time.sleep(0.2)


def _step(meta: dict, key: str) -> str:
    """A guardrail's result for this turn. Old turns from before this was recorded show as UNKNOWN."""
    value = str(meta.get(key) or "").upper()
    return value if value in {"PASS", "BLOCK", "MASKED", "ERROR", "OFF", "SKIPPED"} else "UNKNOWN"


def _look_up(meta: dict) -> tuple[bool, int | None]:
    """Turns from before look-up existed have no `look_up` key: they ran without it, so count as off."""
    value = str(meta.get("look_up") or "")
    if value.startswith("on"):
        match = re.search(r"max (\d+)", value)
        return True, int(match.group(1)) if match else None
    return False, None


def _sections(meta: dict) -> tuple[list[list], bool]:
    text = str(meta.get("sections_found") or "")
    if text.startswith("ERROR"):
        return [], True
    return [[m.group(1).strip(), float(m.group(2))] for m in SECTION_HIT.finditer(text)], False


def build_turn(obs: dict, source: str) -> dict:
    meta = obs.get("metadata") or {}
    look_up, max_sections = _look_up(meta)
    sections, search_error = _sections(meta)
    return {
        "id": obs["traceId"],
        "source": source,
        "time": obs.get("startTime"),
        # Experiment runs put the run name in the session ID; course chats use it for the chat itself.
        # The date keeps two runs with the same settings (and so the same name) apart.
        "run": f"{obs.get('sessionId')} · {(obs.get('startTime') or '')[:10]}" if source == "experiment" else None,
        "isTester": is_tester(obs.get("userId")),
        "model": meta.get("robin_model"),
        "lookUp": look_up,
        "maxSections": max_sections,
        "bank": _step(meta, "step_1_bank_account_check"),
        "injection": _step(meta, "step_2_injection_check"),
        "facts": _step(meta, "step_4_facts_check"),
        "rewrite": meta.get("rewrite_needed") == "yes",
        "outcome": meta.get("outcome") or "unknown",
        "sections": sections,
        "searchError": search_error,
        "query": meta.get("search_query"),
        "evals": {},
        "url": f"{BASE}/project/{obs.get('projectId')}/traces/{obs['traceId']}",
    }


def main() -> None:
    turns: dict[str, dict] = {}
    for env, source in SOURCES.items():
        print(f"Fetching '{TURN_NAME}' turns from environment '{env}'...")
        rows = _paged("/api/public/v2/observations", name=TURN_NAME, environment=env,
                      fields="core,basic,metadata")
        for obs in rows:
            turns[obs["traceId"]] = build_turn(obs, source)
        print(f"  {len(rows)} turns.")

    print("Fetching quality-check scores ('eval: ...')...")
    eval_count = 0
    for env in SOURCES:
        for score in _paged("/api/public/v3/scores", environment=env, fields="core,subject"):
            if not score["name"].startswith("eval: ") or score.get("dataType") != "BOOLEAN":
                continue
            turn = turns.get((score.get("subject") or {}).get("traceId"))
            if turn is not None:
                turn["evals"][score["name"][len("eval: "):]] = bool(score["value"])
                eval_count += 1
    print(f"  {eval_count} quality-check results matched to a turn.")

    by_source = collections.Counter(t["source"] for t in turns.values())
    out = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "turns": sorted(turns.values(), key=lambda t: t["time"] or "", reverse=True)}
    out_path = Path(__file__).with_name("guardrails-data.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}: {by_source['course']} course turns, {by_source['experiment']} experiment turns.")


if __name__ == "__main__":
    main()
