---
description: Generate a spec document for a given implementation step/feature, following CLAUDE.md and the existing spec format
argument-hint: "<step_number> <feature_name>"
allowed-tools: Read, Write, Glob, Grep, Task
---

# Create Spec Document

Generate a new spec doc for one feature/step of the Spendly roadmap. This command only **writes a planning document** — it must never implement the feature, and must never touch `app.py`, `database/db.py`, templates, or static files.

Arguments (parse from: $ARGUMENTS), in this order: `<step_number> <feature_name>`
- `step_number` — the implementation step this feature corresponds to (see the route table in CLAUDE.md)
- `feature_name` — short name of the feature, may be multiple words (e.g. "expenses add", "logout")

## 0. Validate arguments

- Require both arguments. If either is missing, stop and print usage: `/create-spec <step_number> <feature_name>` — don't guess a default.
- `step_number` must parse as a positive integer.
- `feature_name` must be non-empty after trimming. Slugify it for the filename: lowercase, spaces/underscores → hyphens, strip anything else that isn't `a-z0-9-`.

## 1. Ground the spec in current project state — delegate to the Explore subagent, don't assume

Before writing anything, use the Explore subagent to gather, in this order:

1. Read `CLAUDE.md` in full — architecture, code style, tech constraints, the "Implemented vs stub routes" table, and the "Warnings and things to avoid" section.
2. Cross-check `step_number` against CLAUDE.md's route table: find which route(s), if any, are tagged "Step `<step_number>`". If `feature_name` doesn't match what CLAUDE.md lists for that step number (or nothing is tagged with that step at all), this is a **mismatch** — surface it clearly in the final report instead of silently proceeding as if they agree. Never edit CLAUDE.md yourself to "fix" the discrepancy.
3. Read `.claude/specs/01_database-setup.md` in full — this is the existing spec and the canonical formatting template. The new spec must follow the same structure: numbered `##` sections separated by `---` rules, markdown tables for schema, a checklist for "Definition of Done".
4. Read the current state of whatever the feature will actually touch — the relevant route stub in `app.py`, any existing template in `templates/`, relevant helpers in `database/db.py` — so the spec reflects what's really there today, not stale assumptions (CLAUDE.md itself can drift, as seen before).

## 2. Analyse edge cases for the feature

Based on what the feature actually is, think through and document the edge cases relevant to it. Adapt to the real feature — don't copy this list blindly, use it as a prompt:

- **Auth/session features** (login, logout, profile): no session / expired session, accessing while already logged in or already logged out, correct redirect target after the action, no CSRF protection exists yet in this codebase, session cookie behavior.
- **Expense mutation features** (add/edit/delete): ownership checks (a user must only ever edit/delete expenses where `user_id` matches their own session — never another user's by guessing an id), missing/invalid `amount` (negative, zero, non-numeric), invalid/unknown `category` (must be one of the fixed 7 in `CATEGORIES`), invalid `date` format, missing required fields, editing/deleting a non-existent expense id, GET-only stub today vs the POST/mutation handling the real feature needs.
- **Any DB-touching feature**: parameterized queries only, `PRAGMA foreign_keys = ON` implications, uniqueness constraints, matching the exact existing schema — call out explicitly if the feature requires a schema change rather than quietly assuming new columns.
- **Any route feature**: `url_for()` for every internal link in templates, `abort()` for HTTP errors instead of raw string returns, one-responsibility route functions per CLAUDE.md's code style section.

## 3. Write the spec file

- Path: `.claude/specs/<NN>_<feature-slug>.md`, where `<NN>` is `step_number` zero-padded to 2 digits (e.g. `03_logout.md`, `07_expenses-add.md`) — matches the existing `01_database-setup.md` naming convention.
- **If a spec file already exists at that path**, do not silently overwrite it. Show the user a summary of what exists vs. what the new content would be, and ask for confirmation before replacing it.
- Match the section structure of `01_database-setup.md`:
  1. Overview
  2. Depends on
  3. Routes
  4. Database Schema (only if this feature touches the DB — write "No schema changes" otherwise)
  5. Functions to Implement
  6. Changes to `app.py`
  7. Files to Change
  8. Files to Create
  9. Dependencies
  10. Rules for Implementation
  11. Expected Behavior
  12. Error Handling Expectations
  13. Definition of Done
- In the **Overview** section, include this line near the top: **"Reference: see `CLAUDE.md` for full project architecture, code style, and tech constraints — this spec must stay consistent with it."**
- In **Rules for Implementation**, restate only the specific CLAUDE.md constraints that actually apply to this feature (e.g. Flask-only, SQLite-only via `database/db.py`, vanilla JS only, no new pip packages, parameterized queries, `url_for()` everywhere, `abort()` for errors, port 5001) — don't paste the whole file, just what's relevant to this feature.
- Populate **Error Handling Expectations** and **Definition of Done** using the edge cases identified in step 2.

## 4. Report

Tell the user: the file path written, the step-number ↔ CLAUDE.md cross-check result (match or mismatch, and what the mismatch was if any), and a short bullet list of the key edge cases the spec captures. Do not implement any part of the feature, and do not modify `app.py`, `database/db.py`, templates, or CLAUDE.md as a side effect — this command only produces the spec document.
