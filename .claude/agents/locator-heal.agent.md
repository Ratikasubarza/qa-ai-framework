---
name: Locator Heal Agent
description: Suggests 3 alternative Playwright locators when an existing locator breaks. Use when a UI element locator has failed and you have a DOM snapshot. Returns candidates ordered by stability (data-testid first). Does NOT apply the fix — the caller decides which candidate to use.
---

## What this agent does

Analyzes a broken locator and a DOM snapshot, then returns 3 alternative locator candidates ranked by stability.

**Python module:** `agents/locator_agent.py`  
**Singleton:** `locator_agent = LocatorAgent()`  
**LLM tier:** `ModelTier.FAST`  
**Prompt:** Inline `SYSTEM_PROMPT` constant

## Input

Method: `locator_agent.suggest(broken_locator, element_description, dom_snapshot)`

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `broken_locator` | `str` | ✅ | The currently failing locator string |
| `element_description` | `str` | ✅ | Human description of the element (e.g. "Submit button on login form") |
| `dom_snapshot` | `str` | ✅ | Relevant DOM HTML section; sanitized and truncated to 3000 chars |

## Output

Returns `list[dict]` — up to 3 candidate locators, ordered by confidence:

```json
[
  {
    "locator": "page.get_by_role('button', name='Submit')",
    "strategy": "role",
    "confidence": "high",
    "reasoning": "Button has semantic role and unique name on this page"
  },
  {
    "locator": "[data-testid='login-submit']",
    "strategy": "data-testid",
    "confidence": "medium",
    "reasoning": "data-testid present but may be dynamically added"
  }
]
```

Returns an empty list `[]` if the LLM call fails or the DOM snapshot cannot be parsed.

## Locator stability priority (highest → lowest)

1. `[data-testid="..."]` — most stable; ask devs to add if missing
2. `page.get_by_role("...", name="...")` — semantic, good stability
3. `page.get_by_label("...")` — for form inputs with labels
4. `page.get_by_placeholder("...")` — for inputs with placeholder text
5. `input[type="email/password/submit"]` — attribute-based
6. `button[type="submit"]` — specific attribute selectors
7. CSS class — least stable, last resort only

## `strategy` field values

`data-testid | role | label | placeholder | attribute | css`

## Rules

- **Never hardcode credentials or URLs** — use `TestConfig` or `settings`
- **Always use `./venv/bin/python3.11`** — never system Python
- **This agent suggests only — it does NOT modify test files.** The caller (self-healer or developer) decides which candidate to apply
- **DOM snapshot must be real** — do not pass fabricated HTML; the agent will suggest locators that only work in the actual DOM
- **Prefer `data-testid`:** if the element lacks one, include a note in `reasoning` that devs should add it
- **Truncation:** DOM snapshot is limited to 3000 characters — pass the most relevant section around the target element
