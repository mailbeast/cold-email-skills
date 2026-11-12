---
name: email-bounce-decoder
description: Decode email bounce messages (NDR/DSN), SMTP reply codes and enhanced status codes such as 550 5.1.1, 421 4.7.0 or Gmail 5.7.26 and Microsoft 5.7.708; classify each as a bad address, a temporary failure or a block against the sender, and say exactly what to do. Use when the user pastes a bounce, a "Mail delivery failed" or "Undeliverable" message, an SMTP error, or asks why emails to some recipients fail.
---

# Email bounce decoder

A bounce is only useful if you read it correctly. Most damage comes from two
mistakes: deleting good addresses after a temporary or sender-side error, and
retrying addresses that are permanently gone.

## 1. Find the facts in the message

From the pasted text, extract:

- **Action** (DSN field): `failed` is a bounce. `delayed` is NOT a bounce; the
  server is still retrying and the message may arrive. `delivered`, `relayed`,
  `expanded` are success reports.
- **Status**: the enhanced status code `X.Y.Z` (RFC 3463), for example `5.1.1`.
  The first digit decides permanence: `5` permanent, `4` temporary.
- **Diagnostic-Code** / the SMTP reply text from the remote server, for example
  `550 5.1.1 The email account that you tried to reach does not exist`.
- **Remote-MTA** / the reporting server: identifies the provider (Google, Microsoft,
  Yahoo, Mimecast, Proofpoint, a company server).
- **Final-Recipient**: the address that failed.

Ignore messages that only look like bounces: out-of-office replies, "I have left the
company" auto-replies (useful: they often name a new contact), "your message is
delayed" warnings and read receipts.

## 2. Classify

Decide with the code AND the text; servers often use generic codes with a specific
explanation.

| Class | Typical codes and phrases | What it means |
| --- | --- | --- |
| **Bad address (hard)** | `5.1.1` user unknown / no such user / does not exist; `5.1.2` bad destination domain; `5.1.10` null MX (RFC 7505) or, at Microsoft, recipient not found; `5.2.1` mailbox disabled; Microsoft `5.4.1 Recipient address rejected: Access denied` (address not in the tenant) | The address will never work |
| **Temporary** | `4.2.2` mailbox full (some servers send `5.2.2`); `4.4.1`/`4.4.2` connection or timeout; `4.3.0`, `4.4.7` expired in queue after retries; `421`/`450`/`451` "try again later"; greylisting | May succeed later |
| **Blocked: authentication** | Gmail `5.7.26` (unauthenticated sender, DMARC), `5.7.25` (no PTR for the sending IP); Microsoft `5.7.509` (fails DMARC with p=reject); "SPF fail", "DKIM fail" | The sender setup is wrong, not the recipient |
| **Blocked: reputation or policy** | Gmail `550-5.7.1` "likely unsolicited mail" and `421-4.7.28` "unusual rate of unsolicited mail"; Microsoft `5.7.708` "traffic not accepted from this IP", `S3150` IP blocked; Yahoo `421 4.7.0 [TSS04]` deferred for volume or complaints; Proofpoint `554 5.7.1 Blocked`; Mimecast and Barracuda policy rejections; "listed on" a blocklist | The receiver distrusts the sending IP, domain or content |
| **Content** | `5.3.4` / `5.2.3` message too large; `5.6.x` malformed; "rejected due to content", "virus" | Fix the message itself |
| **Recipient-side rule** | "rejected by recipient's policy", "sender not allowed", "not authorized to send to this recipient" (restricted or internal-only mailbox) | The recipient org blocks outside mail to that address |

If the code and text disagree, trust the text. If you cannot tell, say so and give
the two most likely readings.

## 3. Recommend the action

- **Bad address**: remove or suppress the address; do not retry. If a whole domain
  fails with `5.1.2` or null MX, suppress the domain.
- **Temporary**: retry later (hours, then a day). Treat it as bad only after it keeps
  failing over several days; a single `4xx` is not a reason to delete a lead.
- **Authentication**: fix SPF, DKIM and DMARC alignment on the sending domain (the
  `email-deliverability-audit` skill checks this), then resend. Do not touch the
  recipient list.
- **Reputation or policy**: do not delete the recipient. Slow down or pause the
  sending mailbox, check blocklists for the sending IP and domain, review content and
  targeting, warm up new mailboxes gradually, and keep bounce and complaint rates
  low. If the block names a delisting URL, give it to the user.
- **Content**: shrink the message, remove attachments, fix encoding or links.
- **Recipient-side rule**: stop emailing that address; it is not a deliverability
  problem of the sender.

## 4. Output format

For each bounce:

```
Recipient:  jane@example.com
Verdict:    Bad address (hard bounce)
Evidence:   550 5.1.1 "The email account that you tried to reach does not exist" from Google
Action:     Remove the address; no retry.
```

For several bounces, add a summary: counts per class, and whether the pattern points
at the sender (many policy or authentication blocks at one provider) or at list
quality (many bad addresses: verify the list before the next send).

## If MailBeast is connected

If the MailBeast MCP server is available, `get_campaign_analytics` shows bounces of a
campaign by mailbox, sequence step and bounce type, which tells whether one mailbox
or one step causes them. `get_mailbox` shows the last error of a sending mailbox.
Learn more at https://mailbeast.ai.
