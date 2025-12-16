# Design Notes

## Static vs JS Fallback
- **Strategy:** The scraper attempts a static fetch first. If successful, it checks a simple heuristic:
    1. The total length of extracted section text is less than **500 characters**.
    2. The static HTML **does not contain a `<main>` landmark tag**.
    
    If both conditions are met, it assumes the page is JS-heavy (e.g., just a tiny loader script) and falls back to Playwright rendering. If static content is sufficient, Playwright is still launched, but only to perform interactions (clicks/scrolls) on the loaded DOM, avoiding the initial re-render if not necessary.

## Wait Strategy for JS
- [X] Network idle
- [ ] Fixed sleep
- [X] Wait for selectors
- **Details:** The primary strategy is `page.goto(..., wait_until="load")` followed by `page.wait_for_load_state("networkidle")`. A small, fixed sleep (`page.wait_for_timeout(500)`) is used after interaction clicks (tabs/load more) to allow new content to render.

## Click & Scroll Strategy
- **Click flows implemented (e.g., tab click, load more):**
    1. Clicking tabs (`[role="tab"]`, `button[aria-controls]`). Only the first 3 tabs are clicked.
    2. Clicking "Load more/Show more" style buttons (`text=/Load more/i`, `.load-more-button`, etc.). Only the first visible button is clicked once.
- **Scroll / pagination approach:** The system prioritizes **Pagination** (finding `a[rel="next"]` or next page numbers) up to `MAX_DEPTH=3`. If pagination links are exhausted before depth 3, it attempts **Infinite Scroll** (scrolling `window.scrollTo(0, document.body.scrollHeight)` and waiting) to reach the required depth.
- **Stop conditions (max depth / timeout):** The primary stop condition is reaching `MAX_DEPTH = 3` interactions (pages visited or scrolls performed). A secondary stop condition is the global `JS_RENDER_TIMEOUT` (30.0s) for the Playwright session.

## Section Grouping & Labels
- **How you group DOM into sections:**
    1. **Primary:** Semantic landmarks (`main`, `section`, `nav`, `header`, `footer`).
    2. **Secondary:** High-level divs (`body > div`) if primary landmarks yield insufficient content.
- **How you derive section `type` and `label`:**
    * **Type:** Determined by the element tag (`header` -> `nav`, `footer` -> `footer`) or class/ID pattern matching (`class*="grid"` -> `grid`, `id*="hero"` -> `hero`).
    * **Label:** The first available `h1-h6` within the section is used. If no heading exists, the first 7 words of the section's text content are used as a fallback label.

## Noise Filtering & Truncation
- **What you filter out (e.g., cookie banners, overlays):** Before parsing, elements matching common CSS selectors for overlays are removed from the HTML tree: `[class*="cookie"]`, `[id*="modal"]`, `[role="dialog"]`, `.newsletter-signup`, etc.
- **How you truncate `rawHtml` and set `truncated`:** `rawHtml` is truncated to the first **500 characters**. The `truncated` boolean is set to `true` if the full HTML string's length exceeds this limit.