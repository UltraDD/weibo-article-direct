# Authentication boundary

The CLI opens the platform's normal visible QR-login page for each invocation. It keeps the resulting browser session in memory only for that invocation, then closes the browser and clears the in-memory HTTP cookie map. It does not import or export cookies, persist browser profiles, distribute credentials, or bypass a verification challenge.

The HTTP client only permits HTTPS requests to the small set of Weibo hosts required by the workflow. Session cookies and the XSRF header are attached per trusted request; an article URL outside that allowlist is treated as an indeterminate verification result without making a network request.

To use it in an owner-operated app:

1. Complete the platform's normal QR login in the visible browser.
2. Confirm the article with `--confirm-publish`.
3. Keep the resulting session local to the owner-controlled process.
4. Treat authentication challenges, explicit rejections, and uncertain writes as stop conditions.

This separation is deliberate. The public project shows the difficult article workflow and its no-retry semantics without turning credentials, unattended accounts, or evasion into a reusable distribution surface.
