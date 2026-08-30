# Security and responsible use

This project is designed for an account owner operating their own local session. Do not submit credentials, session cookies, request captures, account identifiers, or real published content in issues or pull requests.

## Supported boundary

- Use only the account you are authorized to operate.
- Keep a human-visible confirmation before a publish action.
- Stop after a timeout, identity challenge, explicit rejection, or an indeterminate outcome.
- Use test doubles for development and a dedicated test account for any live validation.

## Not supported

- Credential import/export or sharing.
- CAPTCHA solving, security-control bypass, proxy rotation, account farms, fingerprint spoofing, or anti-detection behavior.
- Multi-account, scheduled, or high-frequency publishing.

## Reporting a vulnerability

Do not open a public issue for a credential leak or a behavior that could expose another user's data. Contact the maintainer privately through the GitHub security advisory flow once it is enabled for the published repository.

This is an independent research project. It is not affiliated with, endorsed by, or authorized by Weibo.
