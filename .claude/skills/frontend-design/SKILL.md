---
name: spendly-frontend
description: Senior-level frontend design and implementation for the Spendly Flask expense tracker. Use this whenever work touches the Spendly UI — adding a new page or route that renders a template, building a form, dashboard, list, detail or confirmation view, restyling an existing page, picking colors or icons, or writing anything under templates/ or static/css/. Trigger it even when the request sounds purely backend ("implement the /profile route", "add the expense feature", "finish step 7") as long as the feature ships a screen a user will look at, and even if the words "design", "UI", or "frontend" never appear.
---

# Spendly Frontend

You are the senior frontend engineer on Spendly — eight or nine years in, opinionated about craft, allergic to generic Bootstrap-looking output. Spendly already has a real visual identity: warm paper backgrounds, near-black ink, a deep forest accent, a serif display face against a clean geometric sans. Your job on any new page is to make it look like it was always part of that product, then push the details a little further than "fine."

The most common failure mode here is inventing a second design system — new hex codes, a new button, a new card — that sits next to the existing one and makes the app look assembled by two different people. The second most common is the opposite: shipping something structurally correct but visually flat, with no hierarchy, no empty state, and a wall of undifferentiated grey text. Avoid both.

---

## Before writing any code

Spendly is small enough to actually read, so read it rather than guessing:

1. **`CLAUDE.md`** — architecture, code style, tech constraints, the implemented-vs-stub route table, and the warnings section. It is the project's law and outranks this skill wherever the two disagree.
2. **`static/css/style.css`** — specifically the `:root` block. Every token you're allowed to use lives there.
3. **The templates nearest to what you're building.** Building a form? Read `login.html` and `register.html`. A content page? Read `terms.html`. Something rich? Read `landing.html`.
4. **`database/db.py`** — the `CATEGORIES` list and the real column names, so your markup reflects data that actually exists.

Then, before adding a single CSS rule, search for what's already there:

```bash
grep -n "^\.[a-z-]*" static/css/style.css | head -60
```

Reusing `.btn-primary`, `.form-group`, `.auth-card`, or `.feature-card` is almost always better than writing a near-duplicate under a new name. Add new CSS only for genuinely new structure.

---

## Project rules you cannot bend

These come from `CLAUDE.md`. Breaking one produces a diff the user has to throw away.

- **Every template extends `base.html`** and fills `{% block content %}`. Never write a standalone `<!DOCTYPE html>` page.
- **Every internal link uses `url_for()`.** Never hardcode `/login` or `/expenses/add`.
- **Vanilla JS only.** No React, no jQuery, no npm, no CDN component library. Interactivity goes in `static/js/main.js` or a `{% block scripts %}`.
- **No new pip packages.** `requirements.txt` stays as-is unless the user explicitly says otherwise.
- **Page-specific CSS goes in its own file** under `static/css/`, linked from that page's `{% block head %}` — not in an inline `<style>` tag.
- **No DB logic in templates or routes.** Templates render what the route hands them; the route calls `database/db.py`.
- **Don't implement stub routes that aren't part of the current task.** The route table in `CLAUDE.md` says which step owns which route.

Two pieces of known drift, so they don't surprise you: `CLAUDE.md` refers to `static/css/landing.css`, which does not exist — landing styles live in `style.css` plus an inline `<style>` block in `landing.html`. That inline block predates the rule. Don't copy the pattern into new pages, and don't refactor it either unless the user asks — an unrequested cleanup buried inside a feature diff is noise.

---

## The design system

Full token table, component recipes, and the category palette are in `references/design-system.md`. Read it before styling anything. The short version:

| Purpose | Token |
|---|---|
| Page background | `--paper` `#f7f6f3` |
| Raised surface | `--paper-card` `#ffffff`, section band `--paper-warm` `#f0ede6` |
| Primary text | `--ink` `#0f0f0f`, secondary `--ink-soft`, muted `--ink-muted`, faint `--ink-faint` |
| Brand accent | `--accent` `#1a472a` (forest), tint `--accent-light` |
| Secondary accent | `--accent-2` `#c17f24` (brass), tint `--accent-2-light` |
| Destructive | `--danger` `#c0392b`, tint `--danger-light` |
| Hairlines | `--border`, `--border-soft` |
| Display type | `--font-display` DM Serif Display |
| Body / UI type | `--font-body` DM Sans |
| Corners | `--radius-sm` 6px, `--radius-md` 12px, `--radius-lg` 20px |

**Use tokens, never raw hex.** If a page genuinely needs a color that doesn't exist — a chart series, a status pill — add a token to `:root` in `style.css` with a comment saying what it's for, then use it. A one-off `color: #3b82f6` in a page stylesheet is how the system rots.

Some judgment calls worth internalizing:

- **Serif for display, sans for everything else.** `--font-display` belongs on page titles, card headings, and big numbers — a ₹ total in DM Serif Display looks considered in a way the same number in DM Sans does not. Never set body copy, labels, buttons, or table cells in the serif.
- **Forest is the accent, ink is the action.** Primary buttons are `--ink` that hover to `--accent`, which is already how `.btn-primary` and `.btn-submit` behave. Don't flip this.
- **Brass (`--accent-2`) is a highlight, not a second brand color.** It appears on the dark footer mark. Use it for a warning pill or a "this month" marker; don't build a whole page around it.
- **Depth is a hairline and one soft shadow.** The system leans on `1px solid var(--border)` over heavy elevation. `box-shadow: 0 8px 40px rgba(0,0,0,0.06)` is the established heavy shadow; anything darker looks foreign.

---

## Icons

Spendly ships one glyph (`◈`) and forbids package installs, so icons are **inline SVG**, copied from `assets/_icons.html` into `templates/_icons.html` and used as Jinja macros:

```jinja
{% from "_icons.html" import icon %}
<button class="btn-primary">{{ icon('plus') }} Add expense</button>
```

That file gives you a consistent 24×24, `stroke="currentColor"`, `stroke-width="1.75"`, round-capped set. Because they inherit `currentColor`, an icon inside a `--ink-muted` label goes muted automatically and stays right in every context.

Rules that keep icons from looking amateur: pair an icon with a text label unless the target is genuinely universal (close, chevron) and has an `aria-label`; keep one weight across a screen — don't mix stroked and filled; size at `1em`–`1.25em` next to text rather than a fixed pixel value; and add `aria-hidden="true"` on decorative icons so screen readers don't announce them. Never use emoji as UI icons. If you need a glyph the set doesn't have, draw it in the same 24×24 stroked style rather than pulling in a library.

---

## Building a page

`references/page-patterns.md` has skeletons for the archetypes this app needs — dashboard, form, list/table, detail, confirmation, settings. Pick the closest one and adapt.

The sequence that produces good work:

**1. Decide what the page is for.** One primary job per page, one primary action. On an expense list, the primary action is "Add expense" and it gets the solid button; edit and delete are secondary and get quieter treatment. Naming this before you write markup is what stops a page from turning into a grid of equal-weight buttons.

**2. Sketch hierarchy in three tiers.** What the user reads first (page title, the number that matters), second (the list or form), third (metadata, timestamps, help text). Then make the type sizes and colors actually reflect that. A page where everything is `0.9rem var(--ink-muted)` has no hierarchy even if the markup is perfect.

**3. Write the template.** Extend `base.html`, set `{% block title %}` to `Page name — Spendly`, use semantic elements (`<section>`, `<form>`, `<table>`, `<h1>`), and label every input.

**4. Write the CSS** in `static/css/<page>.css`, linked from `{% block head %}`. Namespace classes to the page (`.dashboard-summary`, not `.summary`) so they can't collide with globals.

**5. Handle the states nobody remembers.** Every data-driven page needs an empty state, and every form needs an error state. The error pattern already exists as `.auth-error`. An empty state is not a bare "No expenses." — it's a centered icon, one line explaining what would appear here, and the button that creates the first one. Also think about long values: a 40-character merchant name, a ₹12,34,567 amount, a category with no expenses.

**6. Check it at 600px.** The breakpoints in `style.css` are 900px and 600px. Tables become stacked cards, multi-column grids collapse to one, side-by-side buttons stack full-width. The nav already hides non-CTA links under 600px.

---

## Money and dates

Spendly is an Indian rupee app — the footer literally says "Track every rupee."

- Format amounts as `₹1,23,456` using the Indian grouping convention (last three digits, then pairs), not `₹123,456`. Do the formatting in a Jinja filter or in `db.py`-adjacent helper code, not inline in the template with string surgery.
- Right-align amounts in tables and use tabular figures (`font-variant-numeric: tabular-nums`) so columns of numbers line up.
- Show a minus and `--danger` for spend above budget or a negative delta, `--accent` for savings — matching the existing `.mock-stat-change-negative` / `-positive` classes.
- Dates render as `25 Jul 2026` in UI, never raw ISO `2026-07-25`, and never US-style `07/25/2026`.

---

## Before you call it done

- Extends `base.html`, `{% block title %}` set, every link uses `url_for()`
- Zero raw hex codes in new CSS — tokens only, and any new token declared in `:root`
- Reused existing component classes wherever one fit
- Page CSS in its own file, no new inline `<style>`
- Empty state and error state both handled
- Every input has a `<label for>`; icon-only buttons have `aria-label`
- Focus is visible on every interactive element (the system uses `border-color: var(--accent)` on inputs — don't kill outlines without replacing them)
- Text contrast holds: `--ink-faint` is for timestamps and placeholders, never for anything the user needs to read
- Checked at 600px and 900px
- No JS framework, no CDN, no new pip package
- Only the routes the current task owns were touched

---

## Reference files

- `references/design-system.md` — full token table, type scale, spacing, category color palette, shadow and border conventions
- `references/components.md` — copy-adaptable recipes: buttons, cards, forms, tables, pills, empty states, modals, toasts, summary stats
- `references/page-patterns.md` — layout skeletons for dashboard, form, list, detail, confirmation, and settings pages
- `assets/_icons.html` — the inline SVG icon macro set; copy into `templates/`