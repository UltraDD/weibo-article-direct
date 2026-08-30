# Safety boundary

## Intended use

This is an owner-operated local research prototype. The user signs in through the platform's normal QR-login experience and explicitly starts one article publish action.

## Product boundary

The project deliberately does not implement account acquisition, credential import, session sharing, CAPTCHA handling, rate-evasion, proxies, fingerprint spoofing, or multi-account scheduling. Those capabilities are not required to demonstrate a reliable article write path and would change the product's risk profile.

## Platform boundary

Observed web behavior is not an official API guarantee. The platform may change, reject, restrict, or discontinue the workflow at any time. Users are responsible for complying with applicable law and the platform's current terms.

## Disclosure boundary

The source includes a clean, runtime-generated implementation of the observed article workflow. It must not include credentials, raw HTTP captures, copied request identifiers, fixed account or draft identifiers, original user content, or a recipe for bypassing platform controls.
