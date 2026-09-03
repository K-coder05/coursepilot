# CoursePilot

CoursePilot reads your course sites so you don't have to. It pulls assignments
and exams from the Canvas REST API and from a raw, API-less course site (via
LLM extraction), normalizes both into one shared record, and syncs that into
a single Notion database — the one place you check for what's due.

It runs on demand from the CLI. Re-running is safe: new items are inserted,
changed items are updated in place, items missing from a source are archived
(never deleted), and archived items that reappear are reactivated
automatically.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for dependency management and running the CLI
- A Canvas account with API access to the course you want to sync
- A Notion account and workspace you can create an integration and a database in

## 1. Generate a Canvas personal access token

1. Log in to your Canvas instance in the browser (e.g. `https://bcourses.berkeley.edu`).
2. Go to **Account → Settings**.
3. Scroll to **Approved Integrations** and click **+ New Access Token**.
4. Give it a purpose (e.g. "CoursePilot") and generate it.
5. Copy the token immediately — Canvas only shows it once. This is your `CANVAS_TOKEN`.
6. Your `CANVAS_BASE_URL` is the root URL of your Canvas instance, e.g.
   `https://bcourses.berkeley.edu` (no trailing path).
7. Your `CANVAS_COURSE_ID` is the numeric id in the course URL, e.g. for
   `https://bcourses.berkeley.edu/courses/1503926` the course id is `1503926`.

## 2. Get an Anthropic API key

The raw-site source uses Claude to extract assignments from HTML that has no
API, so an Anthropic API key is required even if you only use Canvas today.

1. Log in at [console.anthropic.com](https://console.anthropic.com).
2. Go to **API Keys** and click **Create Key**.
3. Copy the key — this is your `ANTHROPIC_API_KEY`.

## 3. Create the Notion integration and database

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and
   click **New integration**. Give it a name and select the workspace you'll
   sync into.
2. Copy the **Internal Integration Secret** — this is your `NOTION_TOKEN`.
3. In Notion, create a new database (table) that CoursePilot will write to,
   with these properties (name and type must match exactly):

   | Property    | Type     | Written by sync? |
   |-------------|----------|-------------------|
   | Title       | Title    | yes |
   | Course      | Text     | yes |
   | Type        | Select   | yes |
   | Due Date    | Date     | yes |
   | Source      | Select   | yes |
   | Link        | URL      | yes |
   | Confidence  | Select   | yes |
   | Archived    | Checkbox | yes |
   | Status      | Checkbox | **no** — yours to use for tracking your own progress; sync never touches it |

4. Open the database, click **···** in the top right → **Connections** →
   connect the integration you just created. Without this step, API calls
   will fail with a 404/403 even with a valid token.
5. Your `NOTION_DATABASE_ID` is the 32-character id in the database URL:
   `https://www.notion.so/myworkspace/<NOTION_DATABASE_ID>?v=...`.

## 4. Configure `.env`

Copy the example file and fill in the values gathered above:

```bash
cp .env.example .env
```

```
CANVAS_BASE_URL=https://bcourses.berkeley.edu
CANVAS_TOKEN=<your Canvas personal access token>
CANVAS_COURSE_ID=<your course id>

RAW_SITE_URL=<the URL of your raw, API-less course site>
ANTHROPIC_API_KEY=<your Anthropic API key, for LLM extraction of the raw site>

NOTION_TOKEN=<your Notion integration secret>
NOTION_DATABASE_ID=<your Notion database id>

TIMEZONE=<IANA timezone, e.g. America/Los_Angeles>

# Optional, defaults to ./coursepilot.db
COURSEPILOT_DB_PATH=
```

`.env` is listed in `.gitignore` and is never committed — all of these values
are read only from your local environment at runtime.

## 5. Install and run

Install dependencies:

```bash
uv sync
```

Run the full pipeline (fetches both Canvas and the raw site, then syncs any
changes into Notion):

```bash
uv run coursepilot run
```

This prints a plain-text summary, for example:

```
5 items: 2 inserted, 1 updated, 1 archived, 0 reactivated, 1 skipped.
  - [inserted] Homework 4 (CS 162) due 2026-09-22T23:59:00-07:00
  - [inserted] Midterm 1 (DATA C104-LEC-001) due 2026-10-01T09:00:00-07:00
  - [updated] Homework 3 (DATA C104-LEC-001) due 2026-09-15T23:59:00-07:00
  - [archived] Reading Response 1 (CS 162) due 2026-09-08T23:59:00-07:00
Rejected 1 item(s):
  - Lab writeup: unparseable due date
```

To sanity-check the raw-site extraction alone, without touching Notion or the
local store, run the dry-run command instead. It only needs `RAW_SITE_URL`
and `ANTHROPIC_API_KEY`:

```bash
uv run coursepilot dry-run
```

## Notes

- Gradescope is explicitly out of scope for v1.
- Sync is one-directional: sources → Notion. Editing a row in Notion directly
  (other than the `Status` checkbox) will be overwritten on the next run.
- The local SQLite store (`COURSEPILOT_DB_PATH`, default `./coursepilot.db`)
  is the source of truth for what's already synced — see
  `docs/adr/0001-local-store-is-source-of-truth.md`.
