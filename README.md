# Weibo Article Direct Publish

> An independent, owner-operated CLI prototype for verified direct publishing of one Weibo headline article.

[中文说明](#中文说明) · [Architecture](docs/architecture.md) · [Safety boundary](docs/safety-boundary.md) · [Authentication boundary](docs/authentication-boundary.md) · [Demo script](docs/demo-script.md) · [Release evidence](docs/release-evidence.md) · [Changelog](CHANGELOG.md)

## Why this exists

Publishing a regular Weibo post is a single write. A headline article is a multi-step workflow: create a draft, stage body media, bind media to the article, save the final draft, submit once, and verify the result with a fresh read.

This project implements that workflow as an owner-operated local CLI. Its engineering focus is reliability:

- Submit exactly once; a timeout is never retried blindly.
- Verify a successful response with a fresh read.
- Stop on identity challenges, explicit rejections, or indeterminate results.
- Keep the direct adapter isolated; an embedding application may provide its own browser fallback, but this CLI never silently retries a write.

This repository is the small public extraction of the direct article-publishing path discovered while researching a separate desktop workbench. The workbench's batch, AI, activation, and commercial product layers are intentionally not included here.

## What this repository demonstrates

- How a multi-step article editor workflow can be isolated behind a small gateway protocol.
- How draft creation, media staging, attachment, final save, one-way submit, and fresh-read verification fit together.
- How to make platform drift and uncertain network outcomes visible instead of turning them into duplicate publishes.

The implementation is intentionally narrow so the engineering boundary is easy to inspect and test. It is a research prototype for developers studying reliability around observed web workflows, not a general-purpose account automation tool.

## Scope

The public release is intentionally narrow:

- one owner-operated account, authenticated by a normal QR login in a visible browser;
- one article per explicit action;
- title, text blocks, body images, image captions, and cover image;
- a concrete direct HTTP adapter, with all account-specific fields generated at runtime;
- no persistence, import, or export of browser credentials.

## Out of scope

This repository does not provide:

- batch, scheduled, multi-account, or unattended publishing;
- Cookie import/export, credential sharing, CAPTCHA handling, proxy rotation, fingerprint spoofing, or anti-detection measures;
- a claim of affiliation with, endorsement by, or authorization from Weibo;
- a guarantee that Weibo's web behavior will remain compatible.

## Install

```bash
python -m pip install .
```

If neither Edge nor Chrome is installed, run `playwright install chromium` once.

## Publish one article

Create a UTF-8 body file. Blank lines split paragraphs; an image on its own line uses standard Markdown syntax.

```markdown
First paragraph.

![Optional caption](body-image.png)

Last paragraph.
```

Then run:

```bash
weibo-article publish --title "My article" --body-file article.md --confirm-publish
```

The command opens the platform's normal login page for QR login, performs one publish workflow, fresh-reads the resulting URL, and exits. Without `--confirm-publish`, it stops before opening a browser or sending a write.

The adapter targets observed web behavior, not an official Weibo API. A platform change can make the workflow stop safely or become incompatible; neither outcome should be worked around by retrying blindly.

## Run the offline tests

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Optional demo

A short masked test-account recording is strongly recommended after the first release, but is not a publishing prerequisite. Add it here when it is ready:

```text
assets/demo.gif
```

The recording must show the user-visible sequence — draft preparation, one submission, and fresh-read verification — while masking account identifiers, article identifiers, request headers, and browser session data.

## Repository layout

```text
src/                CLI, QR session, direct adapter, and publish state machine
tests/              Offline request-contract and state-machine tests
docs/               Architecture, safety boundary, and evidence
assets/demo.gif     Optional redacted test-account recording
```

## Status

Release candidate. The standalone CLI, offline request-contract tests, package build, remote CI, and one owner-controlled live CLI canary are complete. The candidate repository is currently private while the body-media and cover canary is pending.

## License

MIT. See [LICENSE](LICENSE).

---

## 中文说明

这是一个面向本人账号的本地 CLI 研究原型，展示微博头条文章的“扫码登录 → 创建草稿 → 正文媒体处理 → 保存 → 单次提交 → fresh read 核验”发布闭环。

它不提供批量、定时、多账号、Cookie 导入导出、验证码处理、代理/IP/指纹规避或反检测能力；不代表获得微博授权，也不承诺平台长期兼容。

公开版本的重点是可靠发布：网络超时不盲目重发，身份验证、明确拒绝或结果不确定时立即停止。CLI 不内置浏览器兜底；宿主应用如需兜底，必须自行确认直连请求尚未发送。
