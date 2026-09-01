# CoursePilot

An agent that reads course sites (Canvas, raw course pages, eventually Gradescope) and keeps a single Notion database as the source of truth for what's due.

## Language

**CourseItem**:
The unified record every source's raw data is normalized into before it reaches the sync engine — the one shape assignments, exams, and quizzes take regardless of where they came from.
_Avoid_: item, entry, row (these blur whether you mean the raw source data or the normalized record)

**Source**:
A category of origin for a CourseItem — `canvas`, `raw_site`, or `gradescope` — not an identifier for a specific course site. A specific site is distinguished by its `course` and `source_url`, not by a dedicated enum value.
_Avoid_: using "source" to mean an individual course site

**Run**:
One full end-to-end invocation of the pipeline, from fetch through write, always covering every configured source and course. A run is all-or-nothing — there is no partial/single-course invocation, because disappearance detection (see Archived) depends on every run seeing the full picture.
_Avoid_: sync (see below), sweep

**Sync**:
Specifically the diff-and-write phase of a run — comparing incoming CourseItems against the local store, then applying insert/update/archive to Notion. Not the whole run; fetching and extraction are not sync.
_Avoid_: using "sync" for fetching or extraction

**Extraction Confidence**:
A categorical judgment (`direct`, `llm_high`, `llm_needs_review`) that the LLM emits directly as part of its structured extraction output, flagging specific uncertainty (ambiguous date, missing course context, guessed item type) — not a numeric score thresholded afterward.
_Avoid_: confidence score

**Archived**:
The state of a CourseItem that no longer appeared in its source during the most recent run. Archived CourseItems are retained, not deleted, and return to active automatically if the item reappears in a later run.
_Avoid_: deleted, removed
