# Spendly Design System

Everything here is derived from the actual `:root` block in `static/css/style.css`. If that file changes, it wins — re-read it rather than trusting this document.

## Contents

1. [Color tokens](#color-tokens)
2. [Category palette](#category-palette)
3. [Typography](#typography)
4. [Spacing and layout](#spacing-and-layout)
5. [Borders, radii, shadows](#borders-radii-shadows)
6. [Motion](#motion)
7. [Responsive breakpoints](#responsive-breakpoints)
8. [Adding new tokens](#adding-new-tokens)

---

## Color tokens

```css
--ink: #0f0f0f;          /* primary text, primary button fill, footer background */
--ink-soft: #2d2d2d;     /* body copy inside content blocks, form labels */
--ink-muted: #6b6b6b;    /* secondary text, nav links at rest, captions */
--ink-faint: #a0a0a0;    /* timestamps, placeholders, disabled — never load-bearing text */

--paper: #f7f6f3;        /* page background, and text color on dark surfaces */
--paper-warm: #f0ede6;   /* alternating section band, mock/preview surfaces */
--paper-card: #ffffff;   /* raised cards sitting on paper or paper-warm */

--accent: #1a472a;       /* forest green — brand accent, hover state of primary buttons */
--accent-light: #e8f0eb; /* tinted background for accent pills and badges */

--accent-2: #c17f24;     /* brass — secondary highlight, footer mark */
--accent-2-light: #fdf3e3;

--danger: #c0392b;
--danger-light: #fdecea;

--border: #e4e1da;       /* standard hairline */
--border-soft: #eeebe4;  /* internal dividers, progress track fill */
```

**Pairings that work.** Ink on paper for everything default. Accent on accent-light for positive pills and category tags. Danger on danger-light for errors — this is exactly what `.auth-error` does. Paper on ink for the footer and any inverted band.

**Pairings to avoid.** Accent text directly on `--paper-warm` (contrast is passable but muddy — use `--accent-light` as the pill background instead). Brass as body text at any size; it's a fill and a mark color, not a reading color. `--ink-faint` on `--paper-warm`, which drops below comfortable contrast.

**There is no success token.** `--accent` doubles as the positive/success color, which is why `.mock-stat-change-positive` uses it. Don't add a separate green.

---

## Category palette

`database/db.py` defines exactly seven categories:

```python
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
```

`style.css` already colors three of them on the landing mock: `.mock-bar-food #e0a44a`, `.mock-bar-travel #4d7fc2`, `.mock-bar-bills #7b6fc4`. Any real chart, category tag, or legend needs all seven and they must agree with those three. Add this block to `:root`, keeping the existing values so the landing page stays consistent:

```css
/* Category colors — muted, desaturated to sit on warm paper without shouting */
--cat-food:          #e0a44a;
--cat-transport:     #4d7fc2;
--cat-bills:         #7b6fc4;
--cat-health:        #4fa08b;
--cat-entertainment: #d4749a;
--cat-shopping:      #c98b5e;
--cat-other:         #8a8a8a;
```

They're deliberately mid-tone and slightly desaturated — saturated primaries look cheap against `#f7f6f3` and fight the forest accent. Note the naming: the CSS class is `.mock-bar-travel` but the category is `Transport`. Use the category name (`--cat-transport`) for new tokens and don't rename the existing class.

For a category tag, use the color at low opacity as the background with the solid color as text, or a solid dot beside `--ink-soft` text:

```css
.cat-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--ink-soft);
}
.cat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cat-dot-food { background: var(--cat-food); }
/* ...one per category */
```

Never encode meaning in color alone — the dot always sits next to the category name, so a colorblind user loses nothing.

---

## Typography

```css
--font-display: 'DM Serif Display', Georgia, serif;
--font-body: 'DM Sans', system-ui, sans-serif;
```

Both are already loaded in `base.html` at weights 300/400/500/600 for DM Sans. **Don't add a third family and don't add a Google Fonts link** — if you need a weight that isn't loaded, use one that is.

### Scale in use

| Role | Size | Family | Weight | Color |
|---|---|---|---|---|
| Hero title | `clamp(2.75rem, 5.5vw, 4.25rem)` | body | 700 | `--ink` |
| Page title | `2rem` / `clamp(2rem, 4vw, 2.75rem)` | display | 400 | `--ink` |
| Section heading | `1.35rem` | display | 400 | `--ink` |
| Card heading | `1.2rem` | display | 400 | `--ink` |
| Big number / stat | `1.5rem`–`2rem` | display | 400 | `--ink` |
| Body | `0.95rem`–`1rem`, line-height 1.6–1.7 | body | 400 | `--ink-soft` |
| UI / buttons / nav | `0.9rem` | body | 500 | varies |
| Label | `0.85rem` | body | 500 | `--ink-soft` |
| Caption / meta | `0.8rem` | body | 400 | `--ink-muted` |

Line-height: 1.15 for display sizes, 1.6 for UI, 1.7 for reading copy. Letter-spacing `-0.01em` on anything above 2.5rem; leave everything else alone.

The hero title is the one place the body font goes to 700 — that's intentional contrast against the serif used everywhere else for display. Don't generalize it into a rule that headings are bold sans.

### Numerals

Any column or stack of amounts gets `font-variant-numeric: tabular-nums`. Without it, DM Sans digits have varying widths and a table of rupee figures looks ragged.

---

## Spacing and layout

```css
--max-width: 1200px;   /* content container */
--auth-width: 440px;   /* narrow single-column forms */
```

Reading-width containers cap at `720px` (see `.legal-container` and `.hero-inner`'s 720px). Use that for anything text-heavy.

Spacing runs on a rem scale the existing CSS sticks to closely: `0.4 / 0.5 / 0.75 / 1 / 1.25 / 1.5 / 2 / 2.5 / 3 / 4 / 5 / 6rem`. Pick from it rather than inventing `0.85rem`.

Established rhythms worth copying: page sections pad `4rem 2rem` to `6rem 2rem` vertically; cards pad `2rem`; compact cards `1.25rem`; form groups sit `1.25rem` apart; grid gaps are `1rem` for tight grids and `2rem` for feature grids. Mobile drops horizontal padding from `2rem` to `1rem`.

Standard page wrapper:

```html
<section class="page-section">
    <div class="page-container">
        <!-- content -->
    </div>
</section>
```
```css
.page-section { padding: 3rem 2rem 5rem; }
.page-container { max-width: var(--max-width); margin: 0 auto; }
@media (max-width: 600px) { .page-section { padding: 2rem 1rem 3rem; } }
```

Note `base.html` gives `.main-content` a `min-height: calc(100vh - 60px - 100px)` — the nav is 60px, the footer roughly 100px. A short page still pins the footer to the bottom, so you don't need your own min-height hack.

---

## Borders, radii, shadows

```css
--radius-sm: 6px;   /* buttons, inputs, small pills, alerts */
--radius-md: 12px;  /* cards, panels, table containers */
--radius-lg: 20px;  /* large showcase surfaces only */
```

Fully round (`999px`) is reserved for badges, dots, and progress tracks.

The system is border-first: `1px solid var(--border)` defines almost every surface. Only two shadows exist in the codebase and that's enough:

```css
box-shadow: 0 8px 40px rgba(0,0,0,0.06);   /* large raised surface */
box-shadow: 0 20px 60px rgba(0,0,0,0.3);   /* modal only */
```

Don't add a shadow scale. If a card needs to feel raised, it gets `--paper-card` against `--paper-warm` plus the hairline — that's the intended mechanism.

---

## Motion

Transitions in the codebase are `0.2s` for color and background, `0.6s ease` for a bar filling. Match that. Keep motion to opacity, background, border-color, and transform — never animate layout properties. No entrance animations on page load; the app is a tool, not a landing experience (the landing page is the exception and already exists).

Respect the user's setting:

```css
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

---

## Responsive breakpoints

Two, both already in `style.css`:

- **`max-width: 900px`** — multi-column grids collapse to one column, max-widths release to 100%.
- **`max-width: 600px`** — horizontal padding drops to `1rem`, button rows stack full-width, tables become stacked cards, nav hides non-CTA links.

Don't introduce a third breakpoint unless a specific layout genuinely breaks. Design mobile-first inside the component, then use these to widen.

---

## Adding new tokens

When a page needs a color, size, or radius that doesn't exist:

1. Confirm it isn't already covered — most "new" needs are an existing token used differently.
2. Add it to `:root` in `style.css` with a short comment on what it's for.
3. Name it semantically by role, not by appearance: `--cat-food`, `--warning`, `--surface-sunken`. Never `--green-2` or `--light-grey`.
4. Mention the addition when you report back, so the user knows the shared file changed.

Never declare tokens in a page-specific stylesheet. A token in `dashboard.css` is invisible to everyone building the next page, and the system forks.