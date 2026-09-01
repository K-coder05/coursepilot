# Local SQLite store is the source of truth; Notion is a read-only mirror

Each run needs to decide, per CourseItem, whether to insert, update, or skip a Notion row — and to do that without re-reading the entire Notion database on every run (slow, and vulnerable to Notion API rate limits). We considered treating Notion itself as the store of record and querying it back each run to detect changes, but rejected that in favor of a local SQLite table that mirrors what's already in Notion, keyed by content hash.

This makes the sync engine fast and idempotent, but it also means Notion must never be treated as queryable state: if the local store and Notion ever diverge (e.g. someone manually deletes a row in Notion), sync has no way to detect or reconcile that from Notion's side — it only ever writes forward from the local store's understanding of the world.
