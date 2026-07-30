---
description: Run the spec-test-writer and test-runner subagents in sequence for the current feature spec, then report results
argument-hint: "[step_number and/or feature_name — defaults to the current feature branch's spec]"
allowed-tools: Read, Glob, Grep, Task, Bash(git:*)
---

# Test Feature

Orchestrate Spendly's spec-based testing workflow for one feature: generate spec-derived pytest tests, run them, and report. This command does not write or run tests itself — it delegates to the `spec-test-writer` and `test-runner` subagents, strictly in that order, then synthesizes their results into one report. Never skip a step, never run them in parallel (test-runner depends on what test-writer produces), and never write test code or edit `app.py`/`database/db.py` yourself as a shortcut.

Arguments (from `$ARGUMENTS`, both optional): `<step_number> <feature_name>`, same form as `/create-spec`.

## 1. Resolve the target spec

- If `$ARGUMENTS` gives a step number and/or feature name, use `Glob` on `.claude/specs/` to find the matching `<NN>_<feature-slug>.md` file. Match loosely (step number alone, or feature name alone, is enough if unambiguous).
- If no arguments were given, infer "the current feature" from the current git branch: run `git branch --show-current`. `/create-spec` names branches `feature/<feature-slug>`, matching a spec file's slug — find the `.claude/specs/*.md` file whose filename slug matches.
- If nothing matches (branch is `main`, or the slug doesn't correspond to any spec file, or the match is ambiguous), stop and list the available specs in `.claude/specs/` for the user to choose from — do not guess.
- Once resolved, read the spec file's step number and feature slug; you'll pass this identifying info to both subagents so neither has to re-discover it.

## 2. Step one — generate tests (spec-test-writer)

Invoke the `spec-test-writer` subagent (via `Task`), telling it exactly which spec file to work from (path, step number, feature slug). Wait for it to finish before proceeding — do not start the next step early. Capture from its report: which test file(s) it wrote or extended, and how many tests it added.

## 3. Step two — run tests (test-runner)

Only after step one completes, invoke the `test-runner` subagent (via `Task`), telling it which test file(s) step one just produced/touched so it runs that file specifically (per its own instructions, it may also run the full suite). Wait for it to finish. Capture from its report: pass/fail/error counts, and full detail on any failures (test name, assertion/exception, which spec requirement it checks).

## 4. Final report — write this yourself, don't delegate it

Present a single consolidated report directly in this conversation (not another subagent call), covering:

- Which spec was tested (file path, step number, feature name).
- What `spec-test-writer` did: test file(s) written/extended, number of tests added.
- What `test-runner` found: total passed/failed/errored/skipped, and for each failure — the test name and which spec requirement it was verifying.
- A clear verdict: if everything passed, say so plainly. If anything failed, list it as **spec/implementation drift to resolve** — state which side (code or spec) looks wrong based on the failure, but do not fix it yourself; that's a separate, explicit follow-up the user decides on.
- If `test-runner` flagged an environment problem (e.g. missing `tests/conftest.py` isolation, collection errors) rather than a normal test failure, surface that distinctly and first — it blocks trusting any pass/fail numbers.

Do not modify `app.py`, `database/db.py`, templates, or spec docs at any point in this command — it only orchestrates the two subagents and reports.
