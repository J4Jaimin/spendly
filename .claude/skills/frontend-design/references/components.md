# Spendly Component Recipes

Recipes for components Spendly needs but doesn't have yet. Everything already in `style.css` is listed first — **reuse those before writing anything new**.

## Contents

1. [What already exists](#what-already-exists)
2. [Summary stat card](#summary-stat-card)
3. [Data table](#data-table)
4. [Category tag](#category-tag)
5. [Status pill](#status-pill)
6. [Empty state](#empty-state)
7. [Flash messages](#flash-messages)
8. [Confirm dialog](#confirm-dialog)
9. [Progress bar](#progress-bar)
10. [Form extras](#form-extras)
11. [Page header](#page-header)

---

## What already exists

Don't rebuild these — import them by using the class.

| Class | What it is |
|---|---|
| `.btn-primary` | Solid ink button, hovers to forest. Inline-block, works on `<a>` and `<button>` |
| `.btn-ghost` | Bordered transparent button for secondary actions |
| `.btn-submit` | Full-width form submit |
| `.form-group` / `label` / `.form-input` | The standard labelled field |
| `.auth-error` | Danger-tinted error banner |
| `.auth-card` | White card, `--radius-md`, 2rem padding |
| `.auth-section` / `.auth-container` | Centered 440px column |
| `.auth-header` / `.auth-title` / `.auth-subtitle` | Serif title + muted subtitle |
| `.feature-card` / `.feature-icon` / `.feature-title` / `.feature-body` | Bordered white card with accent icon |
| `.legal-section` / `.legal-container` | 720px reading column |
| `.mock-stat*` / `.mock-bar*` | Landing-page preview only — read for reference, don't reuse on real pages |

A new expense form is `.auth-section` + `.auth-card` + `.form-group` with a wider container. That's the whole page.

---

## Summary stat card

The dashboard's headline numbers. Serif on the value is what makes this look designed rather than generic.

```html
<div class="stat-grid">
    <div class="stat-card">
        <span class="stat-label">Spent this month</span>
        <span class="stat-value">₹24,850</span>
        <span class="stat-delta stat-delta-up">{{ icon('arrow-up') }} 12% vs last month</span>
    </div>
</div>
```

```css
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 2.5rem;
}

.stat-card {
    background: var(--paper-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}

.stat-label {
    font-size: 0.8rem;
    color: var(--ink-muted);
}

.stat-value {
    font-family: var(--font-display);
    font-size: 2rem;
    line-height: 1.15;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
}

.stat-delta {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.8rem;
    font-weight: 500;
}

.stat-delta-up   { color: var(--danger); }  /* spending more is bad news here */
.stat-delta-down { color: var(--accent); }
.stat-delta-flat { color: var(--ink-faint); }
```

Note the inverted semantics: on a spend tracker, up is red. Getting this backwards is a real mistake reviewers notice.

---

## Data table

Desktop table, mobile stacked cards. The container carries the border so rows can be flush.

```html
<div class="table-wrap">
    <table class="data-table">
        <thead>
            <tr>
                <th>Date</th><th>Description</th><th>Category</th>
                <th class="num">Amount</th><th><span class="sr-only">Actions</span></th>
            </tr>
        </thead>
        <tbody>
            {% for e in expenses %}
            <tr>
                <td data-label="Date">{{ e.date_display }}</td>
                <td data-label="Description">{{ e.description }}</td>
                <td data-label="Category">…category tag…</td>
                <td data-label="Amount" class="num">₹{{ e.amount_display }}</td>
                <td class="row-actions">
                    <a href="{{ url_for('edit_expense', id=e.id) }}" aria-label="Edit">{{ icon('pencil') }}</a>
                    <a href="{{ url_for('delete_expense', id=e.id) }}" aria-label="Delete" class="danger">{{ icon('trash') }}</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

```css
.table-wrap {
    background: var(--paper-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
}

.data-table { width: 100%; border-collapse: collapse; }

.data-table th {
    text-align: left;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink-muted);
    padding: 0.9rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: var(--paper);
}

.data-table td {
    padding: 1rem 1.25rem;
    font-size: 0.9rem;
    color: var(--ink-soft);
    border-bottom: 1px solid var(--border-soft);
}

.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: var(--paper); }

.data-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: var(--ink);
    font-weight: 500;
}

.row-actions { display: flex; gap: 0.75rem; justify-content: flex-end; }
.row-actions a { color: var(--ink-faint); transition: color 0.2s; }
.row-actions a:hover { color: var(--ink); }
.row-actions a.danger:hover { color: var(--danger); }

.sr-only {
    position: absolute; width: 1px; height: 1px;
    padding: 0; margin: -1px; overflow: hidden;
    clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

@media (max-width: 600px) {
    .data-table thead { display: none; }
    .data-table tr {
        display: block;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--border-soft);
    }
    .data-table td {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.3rem 0;
        border: none;
    }
    .data-table td::before {
        content: attr(data-label);
        font-size: 0.8rem;
        color: var(--ink-muted);
    }
    .data-table .num { text-align: right; }
    .row-actions { justify-content: flex-start; padding-top: 0.5rem; }
}
```

The `data-label` attributes are what make the mobile view readable — set them on every cell or the stacked card loses its field names.

---

## Category tag

```css
.cat-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.85rem;
    color: var(--ink-soft);
    white-space: nowrap;
}
.cat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
```

Generate the dot class from the category name so the template stays clean:

```jinja
<span class="cat-tag">
    <span class="cat-dot cat-dot-{{ e.category | lower }}"></span>{{ e.category }}
</span>
```

Then one `.cat-dot-<name>` rule per category using the `--cat-*` tokens from `design-system.md`.

---

## Status pill

```css
.pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 500;
}
.pill-accent  { background: var(--accent-light);   color: var(--accent); }
.pill-warn    { background: var(--accent-2-light); color: var(--accent-2); }
.pill-danger  { background: var(--danger-light);   color: var(--danger); }
.pill-neutral { background: var(--paper-warm);     color: var(--ink-muted); }
```

Same shape as the existing `.hero-badge`, which is the reference for pill proportions.

---

## Empty state

Every list, table, and chart needs one. This is the single highest-leverage detail separating a polished page from a student project.

```html
<div class="empty-state">
    <span class="empty-icon">{{ icon('receipt') }}</span>
    <h2 class="empty-title">No expenses yet</h2>
    <p class="empty-body">Add your first expense and it'll show up here, sorted by date.</p>
    <a href="{{ url_for('add_expense') }}" class="btn-primary">Add your first expense</a>
</div>
```

```css
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 4rem 2rem;
    background: var(--paper-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
}

.empty-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 50%;
    background: var(--accent-light);
    color: var(--accent);
    margin-bottom: 1.25rem;
}

.empty-title {
    font-family: var(--font-display);
    font-size: 1.35rem;
    color: var(--ink);
    margin-bottom: 0.5rem;
}

.empty-body {
    font-size: 0.9rem;
    color: var(--ink-muted);
    max-width: 380px;
    margin-bottom: 1.75rem;
}
```

Write the copy for the situation. "No expenses yet" on a fresh account and "No expenses in July" after a filter are different states and deserve different sentences — the second one should offer to clear the filter, not to create the first expense.

---

## Flash messages

`app.py` already imports `session`; if the project adds `flash()`, render messages in `base.html` above `{% block content %}` so every page gets them.

```jinja
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <div class="flash-stack">
      {% for category, message in messages %}
        <div class="flash flash-{{ category }}" role="status">{{ message }}</div>
      {% endfor %}
    </div>
  {% endif %}
{% endwith %}
```

```css
.flash-stack {
    max-width: var(--max-width);
    margin: 1.25rem auto 0;
    padding: 0 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.flash {
    padding: 0.75rem 1rem;
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    border: 1px solid transparent;
}
.flash-success { background: var(--accent-light);   color: var(--accent);   border-color: #c9dfd2; }
.flash-error   { background: var(--danger-light);   color: var(--danger);   border-color: #f5c6c2; }
.flash-info    { background: var(--accent-2-light); color: var(--accent-2); border-color: #f0dcb8; }
```

`role="status"` matters — otherwise a screen reader user never learns the save succeeded.

---

## Confirm dialog

For destructive actions like delete. Two options, in order of preference:

**A full confirmation page** is the better fit for this codebase — it needs no JS, survives a page refresh, and matches the "one responsibility per route" style. Route renders `confirm_delete.html`; the page states exactly what will be deleted, offers a `<form method="POST">` with a danger button, and a ghost "Cancel" link back to the list.

```css
.btn-danger {
    display: inline-block;
    background: var(--danger);
    color: #fff;
    padding: 0.65rem 1.5rem;
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: 0.9rem;
    font-weight: 500;
    border: none;
    cursor: pointer;
    transition: background 0.2s;
}
.btn-danger:hover { background: #a5322a; }
```

**A modal** only if the user asks for one. `landing.html` has a working overlay pattern to copy — fixed inset-0 overlay at `rgba(15,15,15,0.6)`, `.is-open` toggling `display: flex`, white `--radius-md` panel. If you build one, close on Escape and on overlay click, and move focus into the dialog.

Always name the thing being deleted in the confirmation text: "Delete ₹1,240 — Groceries, 25 Jul?" not "Are you sure?"

---

## Progress bar

For budget usage or category share. `style.css` already has the track pattern in `.mock-bar-track`.

```css
.bar-track {
    height: 10px;
    background: var(--border-soft);
    border-radius: 999px;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--accent);
    transition: width 0.6s ease;
}
.bar-fill-over { background: var(--danger); }
```

Set the width inline from the route's value (`style="width: {{ pct }}%"`) — that's data, not styling, and it's the one acceptable inline style. Clamp at 100% so an over-budget bar doesn't overflow, and put the real number in text beside it.

---

## Form extras

The base field is `.form-group` + `.form-input`. Additions Spendly will need:

```css
/* select — strip the native chrome, keep the field identical to .form-input */
select.form-input {
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b6b6b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    padding-right: 2.25rem;
}

/* amount field with a rupee prefix */
.input-prefix { position: relative; }
.input-prefix > span {
    position: absolute;
    left: 0.875rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--ink-muted);
    font-size: 0.95rem;
    pointer-events: none;
}
.input-prefix .form-input { padding-left: 1.9rem; }

/* two fields on one row, stacking on mobile */
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 600px) { .form-row { grid-template-columns: 1fr; } }

/* helper and inline error text under a field */
.form-hint  { font-size: 0.8rem; color: var(--ink-muted); margin-top: 0.35rem; }
.form-error { font-size: 0.8rem; color: var(--danger);    margin-top: 0.35rem; }

/* invalid field */
.form-input.is-invalid { border-color: var(--danger); }
.form-input.is-invalid:focus { border-color: var(--danger); }
```

Use `type="number" step="0.01" min="0" inputmode="decimal"` for amounts and `type="date"` for dates — native controls beat any JS datepicker here, and they cost nothing.

When a field is invalid, mark it with `aria-invalid="true"` and point `aria-describedby` at the `.form-error` id. The existing `.auth-error` banner stays for form-level errors; field-level errors go under the field.

---

## Page header

The title row most inner pages open with.

```html
<header class="page-header">
    <div>
        <h1 class="page-title">Expenses</h1>
        <p class="page-subtitle">32 expenses · ₹24,850 this month</p>
    </div>
    <a href="{{ url_for('add_expense') }}" class="btn-primary">{{ icon('plus') }} Add expense</a>
</header>
```

```css
.page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1.5rem;
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.page-title {
    font-family: var(--font-display);
    font-size: clamp(1.75rem, 3vw, 2.25rem);
    color: var(--ink);
    line-height: 1.15;
}
.page-subtitle { font-size: 0.9rem; color: var(--ink-muted); margin-top: 0.35rem; }

.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; }

@media (max-width: 600px) {
    .page-header { flex-direction: column; align-items: stretch; }
    .page-header .btn-primary { text-align: center; justify-content: center; }
}
```

Putting live numbers in the subtitle costs one line in the route and makes the page feel like it knows something. Prefer it to a static tagline.