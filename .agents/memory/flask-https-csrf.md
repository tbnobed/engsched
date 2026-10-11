---
name: Flask HTTPS CSRF and privacy headers
description: Same-origin Referrer-Policy is required on pages with Flask-WTF protected forms.
---

Use `Referrer-Policy: same-origin`, not `no-referrer`, on HTML pages submitting CSRF-protected forms or fetch requests.

**Why:** API key creation passed local HTTP tests but failed in the HTTPS preview. Flask-WTF's secure-request CSRF check requires a same-origin Referer in addition to the token; the no-referrer privacy header suppressed it. Keeping same-origin preserves this protection without disclosing URLs to other origins.

**How to apply:** Cover sensitive admin forms with an HTTPS integration test as well as token validation. Do not solve the problem by disabling CSRF, relaxing the secure-referrer check, or exempting session-authenticated administration routes.
