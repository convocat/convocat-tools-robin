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

- **Add an Anthropic LLM connection in Langfuse, for the judges — and check the existing one.**
  An LLM-as-a-judge evaluator names both a connection and a model, and the two have to agree.
  Read-only inventory of the project on 2026-11-24 found:

  - **One LLM connection**, whose provider name is `Jev` and adapter `typesafe`. Neither string
    names a vendor, so `create_evaluators.py` cannot match it, and `claude-haiku-5-5` has nothing
    to run on. Re-running the evaluator setup today falls back to the project's default evaluation
    model instead.
  - **The eight existing judges are pinned to `{provider: "OpenAI", model: "gpt-6-luna"}`**, from
    when they were created on 29 Oct. No connection in the project is now named OpenAI. Whether
    they still run depends on how Langfuse resolves that; the UI flags an unavailable model on the
    evaluator, so **open one and look** before trusting any eval scores. This is not something
    today's work caused — it predates it.
  - All eight are `status: active`, not paused, and their variable mappings use the generic
    `input` / `output` / `expected_output` sources rather than span names or metadata keys, so the
    renames of 2026-11-24 do not touch them.

  What to do: add an Anthropic connection (Settings > LLM Connections) if the judges should run on
  Claude, or set `JUDGE_MODEL` to something the existing connection can serve. Either way, check
  what `Jev` actually is first.

- **Put `ANTHROPIC_API_KEY` where Robin runs.** Needed in `.env` locally, in Render's environment,
  and as a GitHub Actions secret for the experiment workflow. Robin still starts without it and
  fails on the first message, so the symptom is a broken chat rather than a boot failure.
- **Check the saved views and filters in Langfuse against the renamed trace fields.** Maaike chose
  on 2026-11-24 to keep the new names rather than restore the old ones, so anything saved in the
  Langfuse UI that refers to the old ones silently stops matching - it does not error, it just
  returns nothing, which is the worst way for a teaching view to break. What changed:

  | Was | Is now | Where |
  | --- | --- | --- |
  | `reasoning_effort` | `effort` | the turn's metadata |
  | `handbook_version`, `ingested_at` | `store`, `corpus_version`, `ingested_at`, `matches_source` | the `Look-up 2` span's metadata |
  | `model: gpt-6-sol`, `model: gpt-4.1-mini` | `model: claude-sonnet-5-5`, `model: claude-haiku-5-5` | the trace tags |
  | "Ingestion – customer handbook" | "Ingestion - source documents" | the ingestion trace name |

  `robin_model` and `guardrail_model` keep their names but their values are Claude model ids now.
  The README's "What to show in the traces table" section describes a saved view for participants,
  which is the first one to re-check. Only Maaike can do this: saved views live in the UI.
- **Two leftovers in the Langfuse project, found by the inventory on 2026-11-24.** Neither breaks
  anything; both are tidying.
  `robin/handbook` still exists with a `production` label but nothing reads it any more - the
  corpus is `source-docs/` in the repo. A student who finds it will reasonably think editing it
  changes what Robin knows. Either delete it or rename it so it reads as an archive.
  The project also holds prompts from other work: `Lea/ashbrooke`, `Lorena / Error UX`,
  `exercise_prompts/Truus`, `PHiipa sample prompt`, `examples/surify`, `maaike/hello-world`,
  `maaike/promptname`, `maaike/surify`. So this is not a Robin-only project. Worth knowing before
  deciding what a collaborator on it can see.

- **Reword two look-up prompts in Langfuse: "handbook" -> "the documents".**
  `robin/system-prompt-lookup` and `robin/facts-check-lookup` both tell Robin it is working from
  "handbook sections". Since 2026-11-24 the corpus is three documents (handbook, product guide,
  FAQ) and each chunk carries the document it came from, so the wording is narrower than the truth
  and will read oddly to a student who notices. Robin works either way: this is wording, not
  behaviour. Maaike said she would do it and asked for it on the board so it doesn't get forgotten.
  In the Langfuse UI: save a new version of each prompt and move the `production` label. Nothing in
  this repo may edit prompt text, so it cannot be done from here.
  While you are there, `robin/query-rewrite` says "a search query for the Nest & Co customer
  handbook" too (`prompts.py` holds the starting version of the same text).
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

- 2026-11-24 — The look-up corpus is the repo, and there are two content stores. `source-docs/`
  is the corpus: every markdown file in it gets chunked per section, which is also the exercise
  (drop in a document that disagrees and watch which chunk wins). The Langfuse `robin/handbook`
  prompt is no longer the source and is no longer seeded. Which store is used depends only on
  `DATABASE_URL`: unset means the committed `data/chunks.json`, so a student clone searches with no
  database, nothing to provision and nothing to pay for; set means Postgres with pgvector, which
  the instructor-hosted Robin keeps so Session 1 can point at a real vector database. Both return
  the same `Hit` objects and the same trace shape.
  Provenance on the retrieval span is now a corpus fingerprint - a short hash of the source
  documents - instead of a handbook prompt version, which answers a question a version number
  can't: `matches_source: false` means somebody edited a document and forgot to re-ingest, so
  Robin is answering from text the repo no longer holds.
  The corpus went from 1 document to 3 (handbook, product guide, FAQ): 39 chunks. That makes the
  free-shipping contradiction cross-document and observable - "when do I get free shipping?"
  returns three chunks within 0.004 similarity of each other, two of which contradict the third.
  Verified for real, not just in tests: ingestion ran (39 chunks, 5447 embedding tokens) and two
  live queries were searched against the committed file.
  Still to do: the Langfuse prompts `robin/system-prompt-lookup` and `robin/facts-check-lookup`
  say "handbook sections" where the corpus is now several documents. That wording lives in
  Langfuse, so it is Maaike's to change in the UI.
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
