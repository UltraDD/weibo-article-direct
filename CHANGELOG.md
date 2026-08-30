# Changelog

All notable changes to this project are documented here.

## 0.1.0 — release candidate

- Extracted the one-owner, one-article direct publishing workflow into an independent package.
- Added visible QR login, in-memory session handling, draft creation, body-media staging, cover upload, final save, one-way submit, and fresh-read verification.
- Added explicit stop semantics for platform rejection, security challenges, transport failure, and indeterminate writes.
- Added trusted-host and per-request credential boundaries for the direct HTTP client.
- Added offline gateway/state-machine tests, Ruff checks, wheel build, and GitHub Actions CI.
- Completed owner-operated pure-text and body-media-plus-cover CLI canaries; the owner confirmed both published results.

This project targets observed web behavior rather than an official Weibo API. Compatibility is not guaranteed.
