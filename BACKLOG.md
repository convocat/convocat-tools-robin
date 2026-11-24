# Robin — backlog

Simple backlog for this repo: Open → In progress → Done. Edit by hand or via the
`robin-backlog` skill (`/robin-backlog`).

## Deliberate — do not fix

Things that look like bugs and are course material. Leave them in.

- **The free-shipping threshold contradicts itself across three documents.**
  `content/handbook.md` says "Free shipping on all orders from €50!" in Ordering and payment but
  €75 in Delivery; `content/product-guide.md` says €50; `content/faq.md` says €75. The handbook's
  own changelog records why: v3.2 (15 Sep 2026) raised the threshold from €50 to €75 and claims
  "Delivery section updated" — the Ordering teaser was missed. Robin found the conflict itself in
  a look-up test on 16 Nov 2026.

  **This was listed as a bug to fix until 2026-11-24, when Maaike decided it is the point.** Her
  reasoning: contradictory information across documents is what happens in real life all the time,
  and different people adhere to different handbooks — the lesson is that your source information
  is not reliable. Fixing it would remove a genuine cross-document retrieval failure, where the
  answer a student gets depends on which chunk came back, and the changelog explains how the
  inconsistency arose. Treat it like the other entries under "Design choices you can discuss with
  participants" in `README.md`.

  The same premise is already in `.claude/skills/robin-usecase-discovery/examples/nest-and-co-customer-care-interviews.md`,
  where an agent says the handbook is out of date and they follow the playbook instead. The
  look-up corpus currently holds only the handbook, so that disagreement is not yet observable.

## Open

- **Move the look-up corpus into editable source documents in the repo.** Maaike's direction
  (2026-11-24): the content should live in the repo in a folder such as `source-docs/`, editable
  there, rather than having Langfuse's `robin/handbook` prompt as the source of truth. Pairs with
  dropping Postgres for a committed chunks-and-embeddings file.

  **Decided 2026-11-24: two backends, one codebase.** The instructor-hosted central Robin keeps
  the real Render Postgres with pgvector, because "the parts of a bot" in Session 1 includes a
  vector database and a committed JSON file is not one. Student copies run file-based: no
  Postgres, no `DATABASE_URL`, no ingest Action, no cost. `lookup.py` picks the backend by whether
  `DATABASE_URL` is set, so there is one code path to maintain and the retrieval span looks the
  same in both. Content edits need a redeploy on the student path; acceptable, because students
  are working in Claude Code anyway.
- **Add an Anthropic LLM connection in Langfuse, for the judges.** The evaluators now default to
  `claude-haiku-5-5` (`JUDGE_MODEL`), but an LLM-as-a-judge evaluator runs on a connection
  configured in the Langfuse UI under Settings > LLM Connections. Until an Anthropic connection
  exists there, the judges will fail. This is deliberately a by-hand step: nothing in this repo
  creates Langfuse connections.
- **Put `ANTHROPIC_API_KEY` where Robin runs.** Needed in `.env` locally, in Render's environment,
  and as a GitHub Actions secret for the experiment workflow. Robin still starts without it and
  fails on the first message, so the symptom is a broken chat rather than a boot failure.
- **Give Robin a real escalation path.** When a customer insists on a human (seen for real in the
  traces — "I need to talk with a human agent" x3), Robin has no contact info to offer: the
  default system prompt only injects `RETURN_POLICY`, not Customer Care's hours/channel.
- **`pytest` is not a declared dependency.** `REPO_GUIDE.md` documents
  `python -m pytest instructor/tests` as a command, but `requirements.txt` doesn't list pytest, so
  the documented command fails in a fresh venv. Found on 2026-11-24 when the suite had to be run
  against a system Python that had langfuse 3.14.5 instead of the pinned 5.0.4, which failed one
  test for environment reasons alone. Wants a `requirements-dev.txt`.
- **Add an evals dashboard to the PO/CxD dashboard** (`instructor/dashboard-kit/`) — per-evaluator
  pass rate across experiment runs, filterable by model and guardrail setting. Partly served now:
  the RAG & Guardrails tab shows the `eval:` scores per chat turn, but not a pass rate aggregated
  per evaluator, and not filterable by model or guardrail setting.
- **Migrate `instructor/dashboard-kit/robin_adapter.py` off the deprecated Langfuse endpoints**
  (`/api/public/traces`, `/api/public/scores`) to `/api/public/v2/observations` and
  `/api/public/v3/scores` before Langfuse actually removes the old ones.
  `instructor/dashboard-kit/guardrails_adapter.py` already uses the newer endpoints, so it is the
  worked example to copy from.
- **Decide what happens to the Beoordeling (review) panel in `thread-view/`.** It's UI-only right
  now — toggles don't persist. Either wire it to something, or keep it as a teaching mockup and
  say so clearly.

## In progress

- *(nothing right now)*

## Done

- 2026-11-24 — Robin runs on Claude. Claude Sonnet 5.5 writes the answers; Claude Haiku 5.5 runs
  the guardrails, the query rewrite, the comparison model and the judges, at about a twentieth of
  Sonnet's per-token price - so the course's "big model answers, small model checks" distinction
  stays visible and a cohort costs a few euros. OpenAI stays, for embeddings only: Anthropic has no
  embeddings model, and the look-up has to embed the customer's question on every turn.
  Maaike's reason for switching was that students need an API key either way, and a course taught
  in Claude Code may as well run on Claude. Worth remembering: a Claude Pro or Max subscription is
  NOT API access, so this did not shorten the prerequisites - it changed vendor and added a line.
  The port went through one seam, `_chat` in `robin.py`, which also now splits the system prompt
  out of the message list the way Claude's API wants it - the trace still records the whole list,
  so a step reads in Langfuse exactly as it did before. `reasoning_effort` became `effort`
  everywhere (code, metadata and docs), mapped onto Claude's `output_config.effort`; every Claude
  model accepts one, so the course panel's effort setting now applies to both models in the switch
  instead of only the big one, and the widget's dropdown is no longer disabled for the second
  model. `MAX_ANSWER_TOKENS` (8192) is new because Claude requires a ceiling and thinking tokens
  count towards it. The widget was rebuilt, since the model labels travel from the browser.
  Verified: 65 offline tests, and the request shape accepted by the SDK as far as authentication.
  NOT verified: a real answer from Claude - there was no `ANTHROPIC_API_KEY` in `.env`.
- 2026-11-24 — Dashboard: a RAG & Guardrails tab (one record per chat turn, for course chats and
  experiment runs: each guardrail's result, the look-up matches, the outcome and the `eval:`
  scores) plus an NL/EN language toggle with a full English string table. Data comes from the new
  `instructor/dashboard-kit/guardrails_adapter.py`, which uses Langfuse's v2/v3 endpoints instead
  of the deprecated ones. Closes the English-language item.
- 2026-11-24 — `dashboard-kit/` moved to `instructor/dashboard-kit/`, so the only folders a
  student meets are Robin's own. Maaike decided it stays in this repo rather than going to a
  course repo. The `.gitignore` entries moved with it — they are anchored at the repo root, so
  without that the generated `dashboard-data.json` and `guardrails-data.json`, which hold real
  participants' messages, would have stopped being ignored.
- 2026-11-24 — Simplified the repo so a student can clone it and get a working Robin: Render is
  the only deploy path (`vercel.json` and the Vercel button gone), both deploy buttons now point at
  `convocat/convocat-tools-robin` instead of relying on the rename redirect from `convocat/Robin`,
  instructor material moved into `instructor/` (widget source, experiments, judge prompts,
  teaching guide, tests), and `content/` renamed `source-docs/`. 64 tests pass.
- Cloned the repo locally, wired up `.env`, confirmed Langfuse tracing end to end.
- Connected the real Render Postgres for look-up (RAG); ran the ingestion pipeline.
- Ran the 51-item experiment set with look-up on, guardrails on and off.
- Built `instructor/dashboard-kit/`: Product Owner + conversation-log dashboard adapted from the Montferland
  dashboard-kit, with inline-expanding rows, an `@assistant-ui/react` thread view, and a
  Bronnen/Beoordeling panel matching the Waddinxveen reference.
- Added the `robin-dashboard` skill to launch it on demand.
