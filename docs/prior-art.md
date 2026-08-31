# Prior art and project positioning

## Research snapshot

This comparison was prepared on 2026-08-31 from GitHub repository search, GitHub code search, and manual inspection of the relevant source files. GitHub search is not exhaustive, repositories and branches change, and this document is a positioning record rather than a claim of historical priority.

## Public projects in adjacent categories

| Project | Observed scope | Transport or interaction model | Relation to this project |
| --- | --- | --- | --- |
| [michaelliao/sinaweibopy](https://github.com/michaelliao/sinaweibopy) | Regular Weibo SDK | Public SDK-style API client | Prior art for ordinary Weibo publishing, not headline-article publishing |
| [yangyuan/weibo-publisher](https://github.com/yangyuan/weibo-publisher) | Regular Weibo publishing | Web API client | Prior art for ordinary Weibo publishing |
| [wdwind/weibo_api](https://github.com/wdwind/weibo_api) | Regular Weibo write operations | Described as a private write API client | Prior art for private write flows, not the article workflow covered here |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | Weibo headline-article CLI script | Chrome CDP opens the editor, fills content, and leaves the browser for review/publishing | Article publishing CLI, but browser-driven rather than direct HTTP |
| [doocs/cose](https://github.com/doocs/cose) | Multi-platform article synchronization | Browser extension injects title/body into the Weibo editor and saves a draft | Article synchronization, but page-driven and draft-oriented |
| [yanfishrider/social-publisher](https://github.com/yanfishrider/social-publisher) | Multi-platform article publishing | Playwright/CDP operates a real Edge editor page | Article publishing, but browser-driven and multi-platform |
| [leaperone/MultiPost-Extension](https://github.com/leaperone/MultiPost-Extension) | Multi-platform article synchronization | Weibo adapter creates/saves article drafts and uploads images, then opens the editor; DOM fallback handles page publishing | Closest adjacent implementation; it is not the same standalone end-to-end HTTP CLI boundary |

The source-level distinction for the closest examples is visible in [MultiPost's Weibo adapter](https://github.com/leaperone/MultiPost-Extension/blob/main/src/sync/article/weibo.ts), [COSE's Weibo adapter](https://github.com/doocs/cose/blob/main/apps/extension/src/background.js), and [Baoyu's article script](https://github.com/JimLiu/baoyu-skills/blob/main/skills/baoyu-post-to-weibo/scripts/weibo-article.ts).

## This project's boundary

The public project is intentionally narrower than a general social-media automation suite. It combines these properties in one inspectable Python CLI:

- a visible QR-login session owned by the account operator;
- direct HTTP requests for the observed article workflow rather than Playwright, Selenium, or Chrome CDP as the publishing transport;
- body text, inline media, and cover handling;
- one-way submission with explicit indeterminate outcomes;
- fresh-read verification after a successful write;
- offline request-contract and state-machine tests.

The contribution is therefore best described as an independent implementation and reliability study of an observed web workflow. It should not be described as the first Weibo article publisher, an official API, or a platform authorization.

## How to cite the positioning

Use:

> A focused CLI for direct HTTP publishing of one Weibo headline article, with visible QR login, body media, cover handling, submit-once semantics, and fresh-read verification.

Avoid unsupported claims such as “the first Weibo article publisher”, “official Weibo API”, “private API authorization”, “anti-detection”, or “unlimited batch publishing”.
