---
description: One-shot git/GitHub lifecycle for the current feature branch — commit, push, PR, merge, and cleanup
argument-hint: "[optional commit message]"
allowed-tools: Read, Grep, Glob, Bash(git:*), mcp__github__get_me, mcp__github__list_pull_requests, mcp__github__search_pull_requests, mcp__github__create_pull_request, mcp__github__pull_request_read, mcp__github__merge_pull_request
---

# Ship Feature

Take the current feature branch all the way to `main` in one command: commit any pending changes, push, open a pull request, merge it, delete the remote branch, then come home — checkout `main`, pull the merged result, and delete the local feature branch.

**Scope of standing authorization**: invoking this command is the user's explicit, standing authorization for this exact sequence (commit → push → PR → merge → delete remote branch → checkout `main` → pull → delete local branch) on the **current branch only**. No confirmation prompt is needed between phases — that defeats the point of a one-shot command. What is *not* authorized: touching any branch other than the current one and `main`, force-pushing, force-merging, skipping hooks, or any destructive action beyond this exact list. On any anomaly (see "Stop conditions" below), stop and report instead of forcing through.

Optional argument `$ARGUMENTS`: a commit message to use verbatim instead of an auto-drafted one. If omitted, draft one from the diff (§2).

---

## 0. Detect current state first — this command must be idempotent

Different invocations can start from different points (fresh changes, already pushed, PR already open, PR already merged manually). Detect where things stand before doing anything, so re-running this command after it stopped partway — or after the user did a step manually — resumes correctly instead of erroring or redoing work.

1. `current_branch = git branch --show-current`.
   - Empty output (detached HEAD) → **stop**, report, do not proceed.
   - `current_branch == main` (or `master`) → **stop**: nothing to ship, this command only operates on a feature branch.
2. `git fetch origin` (safe, read-only against the remote).
3. Check whether this branch's work is already on `main`: `git merge-base --is-ancestor <current_branch> origin/main`.
   - If **true** — someone already merged this branch's work (e.g. manually via the GitHub web UI, which is the documented fallback in §5 if PR creation fails). Skip straight to **§7 (remote branch cleanup)** and **§8 (local cleanup)**. Do not attempt to commit, push, or open a PR for work that's already merged.
4. Otherwise, proceed through §1–§6 in order.

---

## 1. Safety gate — run the test suite before touching git

Run the project's test suite (`pytest -q`, see `CLAUDE.md`'s Commands section) before committing or pushing anything.

- Any failure or error → **stop immediately**. Do not commit, push, create a PR, or merge. Report the failing tests and let the user decide whether to fix or override — never ship red tests to `main` silently.
- All green → proceed.

---

## 2. Commit pending changes (only if there are any)

`git status --porcelain`:

- **Empty** → nothing to commit, skip to §3.
- **Non-empty** →
  1. Review what's changed: `git status`, `git diff` (unstaged), `git diff --cached` (already staged). Flag anything that looks like a secret or credential (`.env`, `*.pem`, `credentials*`, API keys embedded in a diff) even if the filename looks innocuous — if found, **stop** and tell the user, don't commit it.
  2. Stage explicitly by path (`git add <file> <file> ...`) — never `git add -A` / `git add .` blindly, per this repo's git safety conventions.
  3. If `$ARGUMENTS` was given, use it verbatim as the commit message. Otherwise draft one: read `git log -5 --oneline` to match this repo's existing style (`feat:`/`fix:`/`style:`/`docs:` prefixes, imperative mood, short), then write a 1–2 sentence message focused on *why*, not a restatement of the diff.
  4. Commit with the standard footer:
     ```
     git commit -m "$(cat <<'EOF'
     <type>: <short message>

     Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
     EOF
     )"
     ```
  5. Never `--amend` (unless the user explicitly asked), never `--no-verify`, never skip hooks. If a pre-commit hook fails, fix the underlying issue and commit again — don't bypass it.

---

## 3. Push the branch

- No upstream yet (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` errors) → `git push -u origin <current_branch>`.
- Upstream already set → `git push`.
- Push rejected (non-fast-forward — someone else pushed to this branch) → **stop**, report the exact error. Never force-push.

---

## 4. Find or create the pull request

1. Determine `owner`/`repo` by parsing `git remote get-url origin` (handles both `https://github.com/OWNER/REPO.git` and `git@github.com:OWNER/REPO.git`).
2. Call `mcp__github__get_me` once, per the GitHub MCP server's own usage guidance, to confirm the token's identity/context before doing anything else with it.
3. Check for an existing PR for this branch before creating a new one — `mcp__github__list_pull_requests(owner, repo, head="<owner>:<current_branch>", state="all")`:
   - An **open** PR already exists → reuse it, skip to §5.
   - A **merged** PR already exists (e.g. merged manually) → nothing left to merge, skip straight to §7.
   - **None** → create one:
     - Look for a PR template (`.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE/`) and follow it if present; otherwise build a body from `git log main..HEAD --oneline` plus a short Summary and Test plan section, matching this repo's existing PR style.
     - Title: under 70 chars, derived from the branch's commit(s).
     - `mcp__github__create_pull_request(owner, repo, title, head=current_branch, base="main", body=...)`.

**Known failure mode in this environment**: the connected GitHub token has previously returned `403 Resource not accessible by personal access token` on PR creation despite `get_me` succeeding — the token authenticates but lacks `Pull requests: write` scope. If this happens:
- **Stop.** Do not fall back to the `gh` CLI (not installed in this environment) and do not attempt any other workaround.
- Report the exact error and tell the user either to (a) create the PR manually via the GitHub web UI and re-run this command — §0's detection will find the open PR and resume from §5, or (b) grant the token `Pull requests: write` and re-run.

---

## 5. Merge the pull request

Only reached once an open PR is confirmed (just-created or found in §4).

1. `mcp__github__pull_request_read(method="get")` on the PR — check `mergeable`/`mergeable_state`. Not cleanly mergeable (conflicts, "dirty"/"blocked" state) → **stop**, report the conflict. Never auto-resolve conflicts or force-merge.
2. `mcp__github__pull_request_read(method="get_check_runs")` — if this repo has no CI configured (true as of this writing — no `.github/workflows/`), there's nothing to gate on, proceed. If checks exist and any is failing or still pending → **stop**, report which one; never merge over a red or in-flight check.
3. Clean → `mcp__github__merge_pull_request(owner, repo, pullNumber, merge_method="merge")`. Use `"merge"` specifically (a real merge commit), matching every prior merge in this repo's history (`git log` shows "Merge pull request #N from ..." — never squash or rebase here unless explicitly told otherwise).
4. Merge call fails (already merged by someone else, branch protection, etc.) → report the exact error, stop.

---

## 6. Delete the remote branch

`git push origin --delete <current_branch>`.

- **"remote ref does not exist" is a success, not a failure** — this repo has GitHub's "automatically delete head branches" enabled, so by the time this step runs the branch is very likely already gone (directly observed behavior in this repo). Treat that specific error as done, move on.
- Any other error → report it, don't retry blindly.

---

## 7. Come home to `main`

1. `git status --porcelain` — re-verify the tree is clean before switching branches (per the standing rule: never `checkout` over uncommitted work without checking first). Dirty here would be unexpected at this point — if it happens, **stop** and report rather than switching over it.
2. `git checkout main`.
3. `git pull` — fails (diverged, conflict, network) → **stop**, report the exact error; never force.

---

## 8. Delete the local feature branch

`git branch -d <current_branch>` — **safe delete only, never `-D`**. This also acts as a final safety net: `-d` refuses to delete a branch that isn't actually fully merged into the current `HEAD`, so if something upstream went wrong, this fails loudly instead of silently losing work. If it fails, stop and report rather than forcing.

---

## 9. Report

Summarize what happened, phase by phase: commit made (or "nothing to commit"), push result, PR created/reused/already-merged (with URL and number), merge result, remote branch deletion result, final state (`main`, up to date with origin), local branch deletion confirmation. If any phase stopped early, say exactly which phase, why, and what the user needs to do before re-running the command.

---

## Non-negotiables

- Never force-push, never `git reset --hard`, never `git branch -D`, never `--no-verify` / skip hooks, never `--amend` an existing commit (unless explicitly asked).
- Never touch any branch other than the current feature branch and `main`.
- Never use a merge strategy other than `"merge"` unless the user says otherwise.
- Never fall back to the `gh` CLI — it is not installed in this environment; use only the connected GitHub MCP tools.
- **Stop and report, never guess or force through**, on: failing tests, a dirty tree where one isn't expected, a rejected (non-fast-forward) push, PR-creation permission errors, merge conflicts, failing/pending CI checks, a branch-deletion failure for any reason other than "already gone", or a failed final `git pull`.
- Re-running this command after it stops partway — or after the user finished a step manually — is safe: §0's state detection resumes from the right phase instead of redoing completed work or erroring on "already exists" conditions.
