# Changelog

All notable changes to this project are documented here.

## 0.2.0 — long-form fix and draft-box hygiene

- Fixed long-form publishing: HTTP responses are now JSON-decoded from the
  full body before any receipt truncation. Draft load/save responses embed
  the whole article and previously failed to parse once they exceeded the
  2,000-character receipt window, which mislabeled successful saves as
  platform rejections and blocked every long article.
- Failed runs now delete the leftover network draft; the submit-dispatched
  path deliberately keeps it (it may already be an article). The platform
  draft box has a hard capacity of 30, and accumulated leftovers used to
  fill it until create requests were rejected with 110002.
- `create` rejections with code 110002 now surface as an actionable
  `draft_box_full` error with cleanup guidance instead of a generic
  platform rejection.
- Added `delete_draft` and `draft_usage` to the gateway protocol.

## 0.1.0 — public release

- Extracted the one-owner, one-article direct publishing workflow into an independent package.
- Added visible QR login, in-memory session handling, draft creation, body-media staging, cover upload, final save, one-way submit, and fresh-read verification.
- Added explicit stop semantics for platform rejection, security challenges, transport failure, and indeterminate writes.
- Added trusted-host and per-request credential boundaries for the direct HTTP client.
- Added offline gateway/state-machine tests, Ruff checks, wheel build, and GitHub Actions CI.
- Completed owner-operated pure-text and body-media-plus-cover CLI canaries; the owner confirmed both published results.

This project targets observed web behavior rather than an official Weibo API. Compatibility is not guaranteed.
