# Accessibility

Secret Vault is a single page that exists for a few minutes, usually opened on a
phone. The goal is WCAG 2.1 AA where it is practical for that job, and an honest
list of what is missing.

## What is in place

- Semantic HTML: one `<h1>`, a real `<form>`, a `<button type="submit">`, no
  click-handling `<div>`s.
- Every field is programmatically labelled — `<label for="f0">` points at
  `<input id="f0">`, including the `dual` field's paste box (`f2_paste`) and its
  upload input (`f2_file`, which also carries `aria-label`).
- The first field is focused on load, so mobile keyboards open where expected.
- Keyboard-only operation works end to end; the submit button has a visible
  `:focus-visible` outline rather than relying on colour alone.
- The countdown carries `role="timer"` and is not announced every second (a
  per-second live region would be hostile to screen-reader users).
- Text, labels and the note line use colours above 4.5:1 against the near-black
  background.
- The layout reflows to 320px wide, respects `viewport` scaling, and never traps or
  hijacks scrolling.
- The page works with JavaScript disabled: only the paste/upload toggle and the
  countdown are enhanced by it. Both the paste box and the file input exist in the
  DOM, so submission still succeeds.

## Known gaps

- **Errors are HTTP status pages, not inline messages.** A rejected submission
  returns `400`/`409`/`410` with a short body; there is no field-level error summary
  and no `aria-live` region announcing it.
- **One theme only.** There is no light or high-contrast variant and no
  `prefers-color-scheme` handling; the design is intentionally dark.
- **The paste/upload toggle is a pair of buttons, not an ARIA tablist.** They are
  reachable and labelled, but screen-reader users do not get tab semantics.
- **No automated accessibility check in CI.** Contrast and markup were checked by
  hand; axe-core or Pa11y is not wired up yet.
- **Motion:** there are no animations, but no `prefers-reduced-motion` block either.

## Reporting an accessibility problem

Open an issue using the accessibility template, or email the maintainer (see
`CODE_OF_CONDUCT.md`). Say which browser, assistive technology, and step failed.
If the problem also leaks a secret value, use the private flow in `SECURITY.md`
instead.
