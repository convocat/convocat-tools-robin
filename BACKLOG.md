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
- **Give Robin a real escalation path.** When a customer insists on a human (seen for real in the
  traces — "I need to talk with a human agent" x3), Robin has no contact info to offer: the
  default system prompt only injects `RETURN_POLICY`, not Customer Care's hours/channel.
- **Add English language to the PO/CxD dashboard** (`dashboard-kit/`, currently Dutch-only UI).
  Planned as a live-coding demo.
- **Add an evals dashboard to the PO/CxD dashboard** (`dashboard-kit/`) — per-evaluator pass rate
  across experiment runs, filterable by model and guardrail setting.
- **Migrate `dashboard-kit/robin_adapter.py` off the deprecated Langfuse endpoints**
  (`/api/public/traces`, `/api/public/scores`) to `/api/public/v2/observations` and
  `/api/public/v3/scores` before Langfuse actually removes the old ones.
- **Decide what happens to the Beoordeling (review) panel in `thread-view/`.** It's UI-only right
  now — toggles don't persist. Either wire it to something, or keep it as a teaching mockup and
  say so clearly.

## In progress

- *(nothing right now)*

## Done

- Cloned the repo locally, wired up `.env`, confirmed Langfuse tracing end to end.
- Connected the real Render Postgres for look-up (RAG); ran the ingestion pipeline.
- Ran the 51-item experiment set with look-up on, guardrails on and off.
- Built `dashboard-kit/`: Product Owner + conversation-log dashboard adapted from the Montferland
  dashboard-kit, with inline-expanding rows, an `@assistant-ui/react` thread view, and a
  Bronnen/Beoordeling panel matching the Waddinxveen reference.
- Added the `robin-dashboard` skill to launch it on demand.
