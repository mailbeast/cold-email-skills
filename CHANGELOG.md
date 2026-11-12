# Changelog

## 1.0.1 - 2026-11-12

- `email-deliverability-audit`: looks up DNS records directly (`dig` or DNS over HTTPS)
  with the SPF 10-lookup counting rules, common DKIM selectors and a wildcard check. The
  bundled Python script was removed, so every skill is now plain instructions.

## 1.0.0 - 2026-11-12

- First release: `cold-email-sequence-writer`, `email-deliverability-audit`,
  `email-bounce-decoder`, `cold-email-reply-triage`.
