# Release evidence

> Update this document with real evidence only. Do not publish fabricated measurements or screenshots.

## Required evidence

| Evidence | Release requirement | Result |
| --- | --- | --- |
| Offline unit tests | All passing | 2026-08-30: 14 passed |
| Gateway contract test | Covers direct create/save defaults, trusted-host requests, unsafe fresh-read URL stop, block-stop behavior, numeric success codes, successful submit, missing-ID indeterminate handling, and fresh read | 2026-08-30: 14 passed with stub HTTP |
| Static checks | Lint and bytecode compilation pass | 2026-08-30: Ruff and `python -m compileall -q src` passed |
| Credential scan | No session data, tokens, account IDs, raw captures, or real content in the intended public tree | 2026-08-30: manual publishable-tree scan passed; local build/cache output is ignored and excluded |
| Manual CLI canary | One explicit synthetic article through QR login, followed by owner-side confirmation that it was published | 2026-08-31: passed with pure text; no retry; account, article ID, and URL withheld |
| Body-media and cover canary | One explicit article with body media and cover, followed by fresh-read title verification | Pending public CLI rerun |
| Package build | A wheel can be built from a clean source tree | 2026-08-30: `python -m pip wheel --no-deps --no-build-isolation . -w dist` passed |
| CI definition | Fresh checkout can repeat lint, tests, and wheel build | 2026-08-31: private staging Actions run passed (lint, 14 tests, wheel build) |
| Video evidence | Optional redacted owner-operated run showing submit-once and fresh-read result | Not required for v0.1.0 |
| Public README review | Claims, limitations, license, and screenshots match actual behavior | 2026-08-31: updated and reviewed; private staging state and media-canary boundary are explicit |

## Reporting rules

Only publish aggregate results, dates, release versions, and sanitized observations. Do not publish account identifiers, source article URLs, remote IDs, request headers, cookies, or raw request/response bodies.

## Example release statement

> v0.1.0 passed offline contract tests and one owner-operated CLI canary with a synthetic pure-text article. The canary used one explicit submission attempt; the owner confirmed the article was published. The body-media and cover variant remains pending. No credentials, raw captures, or real identifiers are included in this repository.
