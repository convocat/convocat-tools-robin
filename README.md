# Robin – a chatbot with guardrails, traces and evals

Robin is the customer service assistant of Nest & Co, an invented online homeware shop. It's built for the course *GenAI design for conversations and content*, to show today's architecture in one working bot:

- **A real chatbot widget** on a demo shop page: a chat bubble bottom right, built with [assistant-ui](https://www.assistant-ui.com).
- **System prompt:** Robin's behavior, written upfront (in `prompts.py`).
- **Input guardrails:** bank account numbers are removed by a pattern check (no LLM), and prompt injection is caught by a small model.
- **The LLM call:** GPT-6 Sol, with a switch to GPT-4.1 mini for comparison, and a reasoning effort setting.
- **Output guardrail:** a small model checks that every fact is in the return policy. If not, Robin tries once more, and otherwise gives a fixed, honest answer.
- **Observability:** every message becomes a readable trace in Langfuse.
- **Evals:** ready-made LLM-as-a-Judge prompts in `instructor/EVALUATORS.md`.

Robin runs on **Render**.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/convocat/convocat-tools-robin)

*(This button deploys the course version from `convocat/convocat-tools-robin`. In your own copy, change that name in the link to your own GitHub name and repository.)*

## What you need

- An **OpenAI API key** with access to GPT-6 Sol, GPT-6 Luna and GPT-4.1 mini. Set a monthly spending limit in your OpenAI account.
- A **Langfuse project** and its API keys (Settings > API Keys). Langfuse Cloud has a free tier.
- A free **GitHub** account and a free **Render** account.

The button asks for: your OpenAI key, your two Langfuse keys, the Langfuse URL (`https://cloud.langfuse.com` for the EU region) and a course passcode, a word you give participants in the session.

## Deploy to Render

1. Click **Deploy to Render** and sign in (you can sign in with GitHub).
2. Fill in the values Render asks for. The other settings are already filled in by `render.yaml`.
3. Click **Deploy**. After a few minutes, Render shows a link like `https://robin-xxxx.onrender.com`.

Good to know:
- **On the free plan, Robin falls asleep after 15 minutes without visitors.** The next visitor waits about a minute. Open Robin yourself a few minutes before a session, or switch to the paid **Starter** plan (about $7 a month at the time of writing) to keep it awake.
- **Updating:** Render doesn't pick up changes on GitHub automatically. Click **Manual Deploy > Deploy latest commit**.
- Robin runs in Render's EU region (Frankfurt).

## For students who want their own Robin

**To run your own Robin on Render, you don't need a copy of the code.** Click **Deploy to Render** at the top of this page, sign in, and fill in your own keys and passcode. Render builds Robin straight from this public repository. Robin's prompts live in your own Langfuse project, so you can still change them.

**To change the code as well**, make your own copy first:

1. On GitHub, click **Fork** at the top of this repository.
2. In **your** copy's README, change `convocat/convocat-tools-robin` in the button link to your GitHub name and repository.
3. Click the button and follow the steps above, with your own keys.

## Using Robin

Open the link, click **Course settings** (bottom left) to open the panel, and fill in your first name or a nickname, the passcode, Robin's model and the reasoning effort. Then click the chat bubble (bottom right). The settings panel sits outside the chatbot on purpose, so the widget looks and works like a real customer service widget.

### Switching guardrails off

Under **Guardrails** in the same panel, you can switch off each guardrail separately: bank account numbers, the prompt injection check and the facts check. With all three off, Robin runs on the system prompt alone. That's useful for an exercise: send the same messages with and without guardrails, and compare the answers and the traces.

What changes:

- A switched-off guardrail doesn't appear in the trace tree. With all three off, the tree shows only `3. Robin writes the answer` (the step numbers stay the same, so traces are easy to compare).
- It gets no score, and the turn's metadata lists it under `guardrails_switched_off`.
- Each trace gets one of the tags `guardrails: all on`, `guardrails: some off` or `guardrails: all off`, so you can filter on them.
- With bank account numbers off, a bank account number goes to OpenAI and Langfuse exactly as typed. Use made-up numbers only.

**On a first visit, all three guardrails are off**, so participants first see Robin with the system prompt alone, and then switch guardrails on. The browser remembers each person's switches after that. (The API itself treats any guardrail the browser doesn't mention as on.)

### Your own version of the system prompt (prompt labels)

Several people can try their own version of Robin's system prompt at the same time, on the same Robin:

1. In Langfuse, open `robin/system-prompt` (or `robin/system-prompt-lookup` when the look-up is on), change it, and save it as a new version with your own label, for example `leela`. Don't move the `production` label.
2. In Robin's course panel, type the same label under **Prompt label**.

Your chats now use your version; everyone else still gets `production`. If your label doesn't exist on that prompt, Robin uses `production`. The turn's metadata shows which version was used (`system_prompt_used`), and the trace gets the tag `prompt label: leela`. Only the system prompt follows the label: the guardrails always use `production`.

### Look-up (RAG)

Under **Look-up (RAG)** in the course panel, you can switch on **Look things up in the handbook**. Robin then works like a RAG bot: instead of the return policy in its system prompt, it searches the Nest & Co customer handbook in a **content database** and answers from the chunks it finds. **Max results** sets how many chunks Robin gets for each question: 1, 3 or 5.

It's off by default, so Robin behaves as before until you switch it on.

It works in two separate parts, like the course slide "DocBot: from question to answer":

**The ingestion pipeline** (`ingestion/ingest_handbook.py`) puts the handbook into the database. It runs separately from Robin, whenever the handbook changes:

1. **Get the handbook:** the `production` version of the prompt `robin/handbook` in Langfuse. The handbook lives there like any other prompt, with its version history. (The starting version is `source-docs/handbook.md`.)
2. **Preprocess:** tidy the text.
3. **Chunk:** cut it into chunks, one per section.
4. **Embed:** turn every chunk into an embedding, a list of numbers that captures its meaning (OpenAI `text-embedding-3-small`).
5. **Store:** replace the old chunks in the table `handbook_chunks` in the content database (Postgres with pgvector).

Each run shows up in Langfuse as the trace "Ingestion – customer handbook", in the environment `ingestion`.

**Robin's look-up** only searches the database. With the look-up on, a turn shows two extra steps before `3. Robin writes the answer`:

- `Look-up 1 – rewrite the question into a search query`: a small model turns the message, plus the conversation so far, into a search query (prompt `robin/query-rewrite`).
- `Look-up 2 – search the content database`: the query becomes an embedding, and the database returns the closest chunks. Open it to see the query, the chunks found and how similar each one was (1 is the same meaning, 0 is unrelated), plus the handbook version and when it was ingested.

**To see every chunk in the database,** open `/chunks` on Robin's site (for example `https://robin-xxxx.onrender.com/chunks`), or click "See the chunks in the content database" in the course panel. It shows each chunk's text and the first numbers of its embedding, behind the course passcode. The ingestion trace in Langfuse shows the chunks too, under step "3. Chunk".

Robin then answers with those chunks in its system prompt (`robin/system-prompt-lookup`), and the facts check compares the answer with the same chunks (`robin/facts-check-lookup`). Every trace gets the tag `look-up: on` or `look-up: off`.

#### Setting up the content database (once)

1. In the Render dashboard, click **New > Postgres**. Pick the same region as Robin (Frankfurt) and a paid plan, so the database doesn't expire. pgvector is included; the ingestion switches it on.
2. In Robin's web service, under **Environment**, add `DATABASE_URL` with the database's **Internal Database URL** (from the database's **Info** page). Save; Render redeploys Robin.
3. In GitHub, under **Settings > Secrets and variables > Actions**, add the secret `DATABASE_URL` with the database's **External Database URL**.
4. Under **Actions > Ingest the handbook**, click **Run workflow**.

Repeat step 4 after every change to the handbook in Langfuse: Robin only knows the version that was last ingested.

## Run Robin on your own computer

You need Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in your keys in .env
python app.py
```

Open http://127.0.0.1:3000 in your browser.

## Reading a trace in Langfuse

Every message a participant sends becomes **one trace**, named `Robin – chat turn`. Inside it, the steps are numbered in the order they happen. The step names never change, whichever model you pick, so the trace tree and the graph always look the same:

```
Robin – chat turn                                      input: the customer's message · output: Robin's final answer
├── 1. Input guardrail – bank account numbers          no LLM: a pattern check
├── 2. Input guardrail – prompt injection               small model
│   └── Injection check (small model)
├── 3. Robin writes the answer                          Robin's model, with the system prompt
├── 4. Output guardrail – facts check                   small model
│   └── Facts check (small model)
├── 5. Robin rewrites the answer                        only if step 4 blocked the answer
└── 6. Output guardrail – facts check on the rewrite    only if step 4 blocked the answer
```

Because the trace contains guardrail and agent steps, Langfuse also draws it as a **graph**. You'll find it in the trace view.

**Every step explains itself.** Click a step and look at its **metadata**:

| Metadata | What it says |
| --- | --- |
| `layer` | Input guardrail, LLM call, or output guardrail |
| `uses_llm` | Whether the step uses a model, and which kind ("no: a pattern check in code", "yes: the small model") |
| `what_it_does` | One sentence about the step |
| `if_it_fails` | Fail open or fail closed, for the guardrails |
| `result` | PASS, BLOCK, MASKED or ERROR, for the guardrails |
| `explanation` | Why, in plain words, for the guardrails, such as "Not in the return policy: a €20 voucher" |

**A guardrail step's output is just its result:** PASS, BLOCK, MASKED or ERROR. So in a table of steps, the Output column shows at a glance which guardrail fired. The small-model call inside it (`Injection check (small model)`, `Facts check (small model)`) shows what the model actually answered.

**The turn itself carries a summary** in its metadata, starting with `outcome` and `what_happened` (one sentence), then `step_1_bank_account_check`, `step_2_injection_check`, `step_4_facts_check`, `rewrite_needed`, `guardrails_switched_off`, and the settings: `robin_model`, `reasoning_effort` and `guardrail_model`. These sit on the turn only, not on every step.

The model calls (steps 3 and 5, and the small-model checks) are **linked to their prompt** in Langfuse, with its version number. Click the prompt name to open it.

## Seeing when a guardrail hits

There are three ways, from quickest to most complete:

1. **Warnings in the trace.** Every guardrail that blocks, masks or fails is marked as a **warning**, with the reason as its status message. So is the whole turn, when Robin didn't send its own answer. In the trace tree, these steps stand out, and in the traces table you can filter on level = WARNING to see every turn where something was caught.
2. **Scores.** Each guardrail step has its own score: `guardrail: bank account` (PASS or MASKED), `guardrail: prompt injection` (PASS, BLOCK or ERROR) and `guardrail: facts check` (PASS, BLOCK or ERROR). Click a guardrail step and open its Scores tab to see it. The whole turn has the scores `outcome` and, after a thumbs up or down, `user feedback`. Under Evaluation > Scores you can filter all of them, for example `guardrail: prompt injection` = BLOCK for every injection attempt. A guardrail that didn't run (switched off, or skipped because the message was already blocked) has no score.
3. **A dashboard.** In Langfuse's dashboards, chart the count of each guardrail score by value over time. That shows how often each guardrail fires across the whole cohort.

Note: when the facts check blocks the first answer, there are two facts check steps, each with its own score: BLOCK on step 4, and the result of the second check on step 6. The turn's metadata says `rewrite_needed: yes`.

## Prompts in Langfuse

Robin's prompts live in Langfuse's **Prompt Management**, in the folder `robin/`:

| Prompt | Used by | Variables |
| --- | --- | --- |
| `robin/system-prompt` | Step 3 and 5: Robin's answer | `{{return_policy}}` |
| `robin/return-policy` | Filled into the system prompt and the facts check | none |
| `robin/injection-check` | Step 2: the input guardrail | none |
| `robin/facts-check` | Step 4 and 6: the output guardrail | `{{return_policy}}` |
| `robin/retry-note` | Step 5: tells Robin what to fix | `{{unsupported}}` |

- **The first time Robin runs, it creates these prompts in your Langfuse project** from the texts in `prompts.py`, with the label `production`. It never overwrites prompts that already exist.
- **To change a prompt, edit it in Langfuse** and give the new version the label `production`. Robin picks it up within a minute, without a redeploy. To go back, move the `production` label to an older version.
- **The return policy is one prompt, used in two places.** Change it once, and Robin and the facts check both use the new policy. That's the "context" layer from the course, made visible.
- **If Langfuse can't be reached,** Robin falls back to the texts in `prompts.py`. Those model calls then have no prompt link in the trace.

**What to show in the traces table.** For one row per chat turn, filter on **Is Root Observation = true** (Langfuse often sets this filter for you). Without it, the table lists every step as its own row. Use the column settings to show these, and save it as a view for participants:

| Column | What it shows |
| --- | --- |
| Input / Output | The customer's message and Robin's final answer, as plain text |
| User | The name or nickname the participant typed, so everyone can find their own chats |
| Session | One ID per chat window. Open the **Sessions** view to read a whole conversation |
| Tags | `robin` and the model, such as `model: gpt-6-sol`. Filter on this to compare models |
| Scores | `outcome` and `user feedback` on the turn; each `guardrail:` score on its own guardrail step; your `eval:` scores |
| Metadata | On the turn: `outcome` first, then the step results and settings. On a guardrail step: `result` first |
| Latency / Cost | How long a turn took, and its token cost (cost only appears once Langfuse knows the model's price) |

All traces are sent with the environment `course`, so they're easy to keep apart from other work in the same Langfuse project.

## Privacy and costs

- Bank account numbers are removed **before** anything is sent to OpenAI or Langfuse. Other personal data is not. Ask participants not to type real personal details.
- The participant's nickname is stored in Langfuse as the user. Tell participants this, as the course settings panel does.
- Robin runs in the EU (Render's Frankfurt region), but conversations are sent to OpenAI and to Langfuse. Choose Langfuse's EU region (`https://cloud.langfuse.com`) to keep traces in the EU.
- Each chat is limited to 40 messages (`MAX_MESSAGES_PER_CHAT`). The conversation is kept in the browser, so a determined participant could get around this limit: set spending limits at OpenAI rather than relying on it. Most messages make three model calls: two on the small Luna model and one on Robin's model. A retry after a blocked answer adds two more. A blocked injection attempt costs only one small call.

## Design choices you can discuss with participants

These are deliberate, so participants can find and improve them:

- **No handover path.** Robin's system prompt doesn't say what to do when the policy has no answer. Only the facts check fallback offers a colleague.
- **No date.** Robin doesn't know today's date, so it can't really check the 30-day window. A better design passes the date in, or lets code calculate it.
- **Gaps in the policy.** Does a return with one damaged and one unused item cost €4.95? The policy doesn't say.
- **The source documents contradict each other.** The free-shipping threshold is €50 in two places and €75 in two others, and the handbook's own changelog shows why: it was raised from €50 to €75 and the update was only half applied. This is deliberate. Contradictory information across documents is what happens in real life, and different people work from different handbooks — so a look-up answer depends on which chunk came back, and no amount of prompt engineering fixes an unreliable source. Ask participants which document they would trust, how they would notice that two chunks disagree, and whose job it is to fix it.
- **Fail open vs fail closed.** If the injection check fails, the message is let through. If the facts check fails, the answer is not sent. Which is right for which guardrail?

## Changing Robin

- **Prompts:** edit them in Langfuse (see "Prompts in Langfuse" above). The fixed fallback messages, and the starting versions of the prompts, are in `prompts.py`.
- **Models:** the environment variables `ROBIN_MODEL`, `COMPARE_MODEL`, `GUARDRAIL_MODEL` and `GUARDRAIL_EFFORT`, in your Render project settings (redeploy afterwards). Check the exact model names in your OpenAI account: the defaults are `gpt-6-sol`, `gpt-4.1-mini` and `gpt-6-luna`. GPT-4.1 mini leaves the OpenAI API on January 14, 2027.
- **The chat widget:** you don't need to. `public/index.html` is the built widget, committed and ready to deploy. To restyle it, the source is in `instructor/widget/` (React with assistant-ui): run `npm install` and `npm run build` there. That rebuilds `public/index.html`, the single page Render serves. `npm run build:preview` makes a version with scripted answers, for showing the design without keys.
- **Logic and tracing:** `robin.py`.

## Files

New to the code? [`REPO_GUIDE.md`](REPO_GUIDE.md) is a fuller map of the repo, written for conversation designers: where each part lives, where to change what, and the code words explained.

| File | What it does |
| --- | --- |
| `app.py` | Robin's API: `/api/chat` and `/api/feedback`. Also serves the chat page |
| `robin.py` | One chat turn: guardrails, the LLM call, and the Langfuse trace |
| `prompts.py` | All the text: system prompt, guardrail prompts, fallback messages |
| `public/index.html` | The demo shop page with the chat widget. Committed pre-built, so deploying needs no Node |
| `source-docs/` | The documents Robin can look things up in, and the help centre's pages |
| `render.yaml` | Tells Render how to run Robin |
| `requirements.txt` | Python packages |
| `.env.example` | Template for your keys when running locally |
| `instructor/` | Everything a student never needs: the widget source, the experiment set and runner, the judge prompts and the offline tests. Kept out of the way on purpose |
| `instructor/tests/bank_account_cases.csv` | The bank account test set: 17 messages that must be masked, must stay, or are known gaps. Paste them into Robin, or run them with `python -m pytest instructor/tests/test_bank_accounts.py` |
