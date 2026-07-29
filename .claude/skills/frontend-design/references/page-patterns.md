# Spendly Page Patterns

Layout skeletons for the page types Spendly needs. Pick the closest archetype, then adapt — these are starting structures, not templates to paste verbatim.

## Contents

1. [Every page starts here](#every-page-starts-here)
2. [Dashboard](#dashboard)
3. [Form page](#form-page)
4. [List page](#list-page)
5. [Detail page](#detail-page)
6. [Confirmation page](#confirmation-page)
7. [Settings / profile page](#settings--profile-page)
8. [The route side](#the-route-side)

---

## Every page starts here

```jinja
{% extends "base.html" %}
{% from "_icons.html" import icon %}

{% block title %}Expenses — Spendly{% endblock %}

{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/expenses.css') }}">
{% endblock %}

{% block content %}
<section class="page-section">
    <div class="page-container">
        ...
    </div>
</section>
{% endblock %}
```

Title format is `Page name — Spendly` with an em dash, matching `login.html` and `terms.html`. The stylesheet link goes in `{% block head %}`, never an inline `<style>`.

---

## Dashboard

The route table reserves `/` for the landing page, so a signed-in dashboard is a separate route. Its shape:

```
page-header ................ "Good evening, Jaimin" + month selector
stat-grid .................. 3–4 summary cards (total, biggest category, daily average, vs last month)
two-column ................. category breakdown (bars) | recent expenses (5 rows + "View all")
empty-state ................ replaces everything below the header when there's no data
```

```css
.two-col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    align-items: start;
}
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

.panel {
    background: var(--paper-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.5rem;
}
.panel-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 1.25rem;
}
.panel-title {
    font-family: var(--font-display);
    font-size: 1.2rem;
    color: var(--ink);
}
.panel-link { font-size: 0.85rem; font-weight: 500; color: var(--accent); }
.panel-link:hover { text-decoration: underline; }
```

Design notes that matter more than the CSS. Lead with one number, not four equal ones — "spent this month" is the headline and should be visually largest. Build the category breakdown from the `.bar-track` / `.bar-fill` pattern with `--cat-*` colors; it needs no charting library, which keeps the no-npm rule intact. Show the recent-expenses list at five rows with a "View all" link rather than paginating on the dashboard. And design the zero-data state first — a brand new account hits the dashboard before it has a single expense, and that's most users' first impression.

---

## Form page

Add expense, edit expense, edit profile. This is the `auth-section` pattern with a wider container.

```
page-header (or auth-header for narrow forms) ... title + one-line purpose
error banner (.auth-error) ...................... form-level errors only
card ............................................ the fields
    form-group × n
    form-row for date + category side by side
    button row: submit (primary) + cancel (ghost)
```

```css
.form-container { max-width: 560px; margin: 0 auto; }
.form-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1.75rem;
}
.form-actions .btn-primary { flex: 1; text-align: center; justify-content: center; }
@media (max-width: 600px) {
    .form-actions { flex-direction: column-reverse; }
    .form-actions .btn-ghost { text-align: center; }
}
```

Field order follows how someone actually thinks about an expense: **amount → category → date → description**. Amount first because it's what they came to enter; date defaults to today so most submissions need no edit at all.

Repopulate on error. When validation fails, `app.py` re-renders the template with an `error` string — pass the submitted values back too and set them as `value="{{ form.amount }}"`, or the user retypes everything. The existing auth pages don't do this; do better on new forms.

Note `column-reverse` on mobile: submit ends up on top, cancel below, so the primary action sits under the thumb.

---

## List page

```
page-header ......... title + live count/total in subtitle + primary "Add" button
filter bar .......... category select, month select, search — GET form, no JS needed
table-wrap .......... data table (see components.md), stacks to cards under 600px
empty-state ......... swaps in when the query returns nothing
pagination .......... only past ~50 rows
```

```css
.filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    align-items: center;
}
.filter-bar .form-input { width: auto; min-width: 150px; }
.filter-bar .btn-ghost { padding: 0.6rem 1.1rem; }
@media (max-width: 600px) {
    .filter-bar { flex-direction: column; align-items: stretch; }
    .filter-bar .form-input { width: 100%; }
}
```

Build filters as a plain `<form method="GET">` whose fields become query params — no JS, bookmarkable, back-button-safe, and it fits the vanilla-JS constraint without effort. Reflect the active filter in the empty state and in the header subtitle, and always offer a way to clear it.

Sort newest-first by default. Group by date with a small subheading row if the list is long; a flat list of forty rows is hard to scan.

---

## Detail page

For a single expense or record.

```
back link ("← Expenses")
page-header ........ the amount as the title, in display serif
meta list .......... category, date, description as label/value rows
actions ............ Edit (primary) + Delete (ghost, danger on hover)
```

```css
.back-link {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
    color: var(--ink-muted);
    margin-bottom: 1.5rem;
    transition: color 0.2s;
}
.back-link:hover { color: var(--ink); }

.meta-list { display: flex; flex-direction: column; }
.meta-row {
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 1rem;
    padding: 0.9rem 0;
    border-bottom: 1px solid var(--border-soft);
}
.meta-row:last-child { border-bottom: none; }
.meta-label { font-size: 0.85rem; color: var(--ink-muted); }
.meta-value { font-size: 0.95rem; color: var(--ink); }
@media (max-width: 600px) {
    .meta-row { grid-template-columns: 1fr; gap: 0.2rem; }
}
```

Making the amount the page title — big, serif — is what stops a detail page from reading like a database dump.

---

## Confirmation page

Destructive actions, no JS required.

```
page-header ........ "Delete this expense?"
card ............... a read-only summary of exactly what's about to go
warning line ....... "This can't be undone."
actions ............ POST form with .btn-danger + .btn-ghost cancel link
```

Cancel goes on the left and gets the quiet treatment; delete goes right and is the only red thing on the page. Never make the destructive button the visually easiest target, and never rely on `onclick="return confirm(...)"` — a real page is more accessible and works with JS disabled.

The route must check ownership before rendering: an expense whose `user_id` doesn't match `session['user_id']` gets `abort(404)`, not a confirmation screen.

---

## Settings / profile page

```
page-header ........ "Profile"
card ............... account details form (name, email)
card ............... change password form — separate form, separate submit
card (danger) ...... destructive zone, bordered in --danger, sits last
```

```css
.settings-stack { display: flex; flex-direction: column; gap: 1.5rem; max-width: 640px; }
.card-danger { border-color: #eec4bf; }
.card-danger .panel-title { color: var(--danger); }
```

Separate forms per concern, each with its own submit — one giant save button that mixes a password change with a name change is a worse experience and messier to validate in the route.

---

## The route side

The template is half the work; the route decides whether the page can be good.

Do the formatting in Python, not Jinja. Hand the template `amount_display`, `date_display`, and `pct` rather than making it do arithmetic and string slicing — that's the "one responsibility" style `CLAUDE.md` asks for, and it keeps the markup readable.

```python
@app.route("/expenses")
def list_expenses():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expenses = get_expenses_for_user(session["user_id"])   # from database/db.py
    return render_template(
        "expenses.html",
        expenses=expenses,
        total=sum(e["amount"] for e in expenses),
        categories=CATEGORIES,
    )
```

Three things every authenticated page needs: a session check that redirects to login, an ownership check on anything addressed by id (`abort(404)` if it isn't theirs — never render another user's data because the id was guessable), and real data passed for the empty-state branch so the template can tell "no expenses yet" from "no expenses match this filter."

Keep every SQL call in `database/db.py` with `?` placeholders. If the page needs a query that doesn't exist yet, add the helper there rather than reaching for the connection in the route.