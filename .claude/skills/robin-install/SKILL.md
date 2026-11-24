---
name: robin-install
description: "Install Robin from scratch for a course participant: checks Python, sets up the virtual environment, walks them through creating their own Langfuse project and getting their Anthropic, OpenAI and Render accounts in place, verifies the whole chain end to end with check_install.py, and puts Robin online on Render. Triggers: '/robin-install', 'install Robin', 'set up Robin', 'get Robin running', 'install the chatbot', 'set this up for me'."
---

# robin-install — set up your own Robin

You are walking **a course participant** through installing Robin. Assume they have never cloned a
repository, never used a terminal, and do not know what a virtual environment is. They are not
expected to learn any of that today — they need a working chatbot with working traces.

Work through the steps in order. **Do each check yourself and say what you found**, rather than
telling them what to type. When something needs their hands — a browser, a dashboard, a password —
say exactly what to click, then wait and verify afterwards.

## The one rule that matters

**Never ask them to paste an API key into this chat, and never print one.** Keys go into the
`.env` file, which they edit themselves. When you need to know whether a key is set, check whether
the *name* has a non-empty value — never read the value back, never echo it, never put it in a
command you run. If they paste a key into the chat anyway, tell them plainly: it is now in the
conversation, they should replace it at the provider, and the new one goes in `.env` instead.

## Step 1 — Check the basics

```bash
python --version
```

Robin needs **Python 3.11 or newer**. If it is older or missing, send them to
[python.org/downloads](https://www.python.org/downloads/) and stop until it is installed — nothing
later will work. On macOS, `python3` may be the working command.

Confirm they are in the right folder: `app.py`, `robin.py` and `requirements.txt` should all be
here. If not, they have opened Claude Code somewhere other than the Robin folder — help them
reopen it in the right place.

## Step 2 — Install the packages

A virtual environment keeps Robin's packages from clashing with anything else on their computer.
Create it and install:

```bash
python -m venv .venv
```

Then, on Windows:
```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
```
On macOS or Linux:
```bash
.venv/bin/python -m pip install -r requirements.txt
```

Use that same `.venv` python for every later command. If the install fails, show them the actual
error rather than a summary — a failed build on one package is a different problem from no network.

## Step 3 — Their own Langfuse project

This is where every trace will land, and it is theirs to keep after the course.

Tell them to:

1. Create a free account at [cloud.langfuse.com](https://cloud.langfuse.com) (choose the EU region
   unless their instructor says otherwise).
2. Create a project — any name, `robin` is fine.
3. Open **Settings → API Keys** and create a key pair. They will see a **public key** starting
   `pk-lf-` and a **secret key** starting `sk-lf-`. The secret is shown once.

Leave the keys on screen; they go into `.env` in Step 5. Do not ask for them here.

## Step 4 — Their model keys

Robin needs two services, and it is worth telling them why in one line each, because the second
one surprises people:

- **Anthropic**, for Claude, which writes Robin's answers and runs its guardrails. Key from
  [platform.claude.com](https://platform.claude.com) → API keys. **A Claude Pro or Max
  subscription is not an API key** — the API is billed separately, and they will need a small
  amount of credit on the account. Tell them to set a spending limit.
- **OpenAI**, used *only* to turn text into numbers for the look-up. Claude has no embeddings
  model, so a bot that searches documents needs a second service for that one step. Key from
  [platform.openai.com/api-keys](https://platform.openai.com/api-keys). It costs cents.

They will also need a free [Render](https://render.com) account for Step 7. They can create it with
their GitHub login.

## Step 5 — Put the keys in `.env`

Copy the template, then let them fill it in:

```bash
cp .env.example .env
```

Open `.env` for them so they can paste into it, and tell them which five lines to fill:
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and
`LANGFUSE_BASE_URL` (`https://cloud.langfuse.com` for the EU region). `COURSE_PASSCODE` can be any
word, or left empty for a bot only they will use. Everything else already has a working default.

Wait for them to say they are done. Then check the names are filled, without reading values:

```bash
.venv/Scripts/python.exe -c "from dotenv import load_dotenv; load_dotenv(); import os; print({k: bool(os.getenv(k)) for k in ('ANTHROPIC_API_KEY','OPENAI_API_KEY','LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY','LANGFUSE_BASE_URL')})"
```

`.env` is in `.gitignore`, so their keys never leave their computer. Say so — people worry about
this, and they are right to.

## Step 6 — Check the whole chain

This is the step that decides whether the install actually worked:

```bash
.venv/Scripts/python.exe check_install.py
```

It checks Python, the packages, which keys are present, that each of the three services answers,
and that the look-up corpus is in place. Then it sends **one real message** through Robin and reads
the trace back out of Langfuse, confirming the guardrail steps are in it and that their nine
`robin/` prompts were created in their project. One message costs a fraction of a cent.

Read its output with them. Everything it reports as `FAIL` has the fix on the same line. Do not
move on while anything fails — a Robin that answers but does not trace is exactly the thing this
course is about noticing, and it is not what they want on day one.

When it passes, point out what just happened: their Langfuse project now holds Robin's prompts,
which Robin created on its first run, and one trace they can go and read.

## Step 7 — Put Robin online, on Render

Local is enough to do the course, but a live URL is nicer and it is what the later sessions assume.

1. The repository must be on **their own GitHub account**. If they cloned the instructor's copy,
   they need their own: on GitHub, open the original repository and click **Fork**.
2. In their fork's `README.md`, the **Deploy to Render** button points at the original repository.
   Change that name in the link to their own, or Render will build the instructor's copy instead.
3. Click **Deploy to Render** and sign in.
4. Render asks for the values marked in `render.yaml`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, the
   two Langfuse keys and `COURSE_PASSCODE`. They type them into Render's own form — not here.
5. Click **Deploy**. After a few minutes Render shows a URL like `https://robin-xxxx.onrender.com`.

Tell them about the free plan honestly: Robin falls asleep after 15 minutes without visitors, and
the next visitor waits about a minute. That is normal, not a broken install.

## Step 8 — Check the live Robin

```bash
curl -s -m 60 -o /dev/null -w "%{http_code}" https://THEIR-URL.onrender.com/
```

A `200` means the page is up. Then have them open the URL, click **Course settings** (bottom left),
fill in their name and the passcode, and send a message through the chat bubble. Confirm with them
that a new trace appears in their Langfuse — not just that the chat replied.

## Step 9 — Invite the instructor

**Do not skip this, and do not claim it is done.** In Langfuse, under
**Settings → Members**, they invite their instructor by email, so their traces can be looked at
while teaching. This is the one step nothing here can verify, and if they forget it their
instructor is simply blind to their work and will not know.

> Instructor's email: **maaike@convocat.nl**

Ask them to confirm they have sent the invitation, and say plainly that you cannot check it.

## Step 10 — Hand off

Tell them, briefly:

- Robin runs locally with `/robin-start`, and online at their Render URL.
- Their prompts live in Langfuse, not in the code. Editing `robin/system-prompt` there changes
  Robin's behaviour within about a minute, with no deploy.
- The documents Robin looks things up in are the markdown in `source-docs/`. Changing one means
  re-running `python ingestion/ingest_source_docs.py` and committing the new `data/chunks.json`.
- `check_install.py` can be re-run any time something looks wrong.
- Updating Robin: Render does not redeploy on its own — **Manual Deploy → Deploy latest commit**.

## Troubleshooting

| What they see | What it is |
|---|---|
| `401` or "authentication" from Claude | The Anthropic key is wrong, or the account has no credit. Pro/Max is not API access. |
| Robin answers but nothing in Langfuse | Langfuse keys wrong, or `LANGFUSE_BASE_URL` pointing at the wrong region. `check_install.py` separates these. |
| "chunks.json is missing" | Run `python ingestion/ingest_source_docs.py`. |
| The look-up finds nothing sensible | Check `matches_source` on the `Look-up 2` span: if it is `false`, the chunks are older than the documents. |
| First message on the live URL takes a minute | The free Render plan sleeps. Expected. |
| `python` not found on macOS | Use `python3`, and `.venv/bin/python` instead of `.venv/Scripts/python.exe`. |

## Notes

- Robin needs no database. The look-up searches `data/chunks.json`, which is committed, so a fresh
  clone can search immediately. `DATABASE_URL` switches it to Postgres and is only for the
  instructor-hosted Robin.
- Node is not needed. `public/index.html` is the chat widget, already built and committed.
- The prompts are created on Robin's first run, from `prompts.py`, and never overwritten
  afterwards — so their own edits in Langfuse are safe.
- Everything under `instructor/` is for whoever teaches the course. A participant never needs it.
