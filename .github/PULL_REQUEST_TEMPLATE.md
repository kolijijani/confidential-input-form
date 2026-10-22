## What this changes

<!-- One or two sentences: which problem, which behaviour. -->

## Why

<!-- The threat, usability break, or documentation gap it fixes. -->

## Type

- [ ] Bug fix
- [ ] New capability (flag, field type, page behaviour)
- [ ] Documentation
- [ ] Accessibility
- [ ] CI / packaging only

## Behaviour that changes

<!-- Delete if nothing user-visible changes. Include the old/new command or status codes. -->

## Tests

- [ ] `python3 -m unittest discover -s tests -v` passes locally
- [ ] `ruff check scripts tests` passes
- [ ] New behaviour has a unit test **and** an end-to-end test where it touches HTTP
- [ ] `CHANGELOG.md` has a one-line, user-facing entry

## Secret-handling checklist

- [ ] No value is printed, logged, echoed in an HTTP body, or written to an audit line
- [ ] No wildcard bind (`0.0.0.0`) introduced or allowed by default
- [ ] File writes stay atomic mode `0600` with symlink rejection
- [ ] No third-party runtime dependency added

## Breaking change?

<!-- "No" or describe: what breaks, who is affected, and what the migration is. -->
