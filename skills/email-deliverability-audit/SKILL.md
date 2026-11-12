---
name: email-deliverability-audit
description: Audit a sending domain's email authentication (SPF and its 10-lookup limit, DKIM, DMARC, MX, MTA-STS, TLS-RPT, BIMI) by looking up its DNS records, explain every problem in plain language and give the exact DNS record that fixes it. Use when the user asks why emails land in spam, wants to check SPF/DKIM/DMARC, sets up a new domain for cold email or newsletters, or asks whether they meet the Gmail, Yahoo or Microsoft sender requirements.
---

# Email deliverability audit

Check the DNS of a sending domain, explain what is wrong and hand back records the
user can paste into their DNS provider.

## 1. Look up the records

Check every domain the user sends from (the domain after `@` in the From address, not
the website if they differ). Look up these names, shown for `example.com`:

| What | Name | Type |
| --- | --- | --- |
| MX | `example.com` | MX |
| SPF | `example.com` | TXT, the record starting with `v=spf1` |
| DMARC | `_dmarc.example.com` | TXT |
| DKIM | `<selector>._domainkey.example.com` | TXT (often a CNAME to the mail provider) |
| MTA-STS | `_mta-sts.example.com` | TXT; the policy is at `https://mta-sts.example.com/.well-known/mta-sts.txt` |
| TLS-RPT | `_smtp._tls.example.com` | TXT |
| BIMI | `default._bimi.example.com` | TXT |

Use whatever the environment allows:

- `dig +short TXT example.com`, `dig +short MX example.com` (or `nslookup -type=TXT example.com`).
- Without `dig`, DNS over HTTPS:
  `curl -s -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=example.com&type=TXT'`
  (or `https://dns.google/resolve?name=example.com&type=TXT`). This sends the domain
  name to Cloudflare or Google.
- Without a shell or network access, ask the user to paste the records from their DNS
  panel.

A TXT value can arrive split into several quoted strings; join them before reading it.

**SPF lookup count.** SPF may use at most 10 DNS lookups (RFC 7208). Each `include:`,
`a`, `mx`, `ptr`, `exists:` and `redirect=` costs one; `ip4:`, `ip6:` and `all` cost
none. Follow every `include:` and `redirect=` target, read its SPF record and add its
lookups to the total. Report the total and the include that adds the most.

**DKIM selectors.** A DKIM key sits under a selector the sender chose. If the user
pasted message headers, take it from `s=` in the `DKIM-Signature` header. Otherwise
try the common ones: `google` (Google Workspace), `selector1` and `selector2`
(Microsoft 365), `k1`, `k2`, `k3` (Mailchimp, Klaviyo), `s1`, `s2` (SendGrid),
`zoho`, `zmail` (Zoho), `sig1` (iCloud), `pm` (Postmark), `mandrill`, `amazonses`,
`protonmail`, `default`, `dkim`, `mail`, `smtp`.

- A record with an empty `p=` is a revoked key.
- Also look up a made-up selector such as `zz-wildcard-probe._domainkey.example.com`.
  If it returns a key too, the domain has a wildcard DKIM record and keys found under
  common selectors prove nothing.
- Finding no key under common selectors does not prove DKIM is missing; say so and ask
  for the header of a sent message.
- Key size: a `p=` value of about 216 base64 characters is a 1024-bit key, about 392 a
  2048-bit key.

## 2. Explain the results

Lead with what blocks delivery, then what hurts it, then optional improvements.

**Blocking (fix first)**
- No SPF and no DKIM: major mailbox providers expect at least one on every message
  and reject or junk unauthenticated mail.
- More than one SPF record, or an SPF record that needs more than 10 DNS lookups:
  SPF returns `permerror`, which counts as a failure.
- `+all` in SPF: anyone can send as the domain.
- No DMARC record: required by Gmail and Yahoo for senders of more than 5,000
  messages a day, and by Microsoft (Outlook.com, Hotmail) for high-volume senders.
- Null MX (`0 .`) on the From domain: replies cannot be delivered and receivers
  treat the domain as not sending mail.

**Hurts reputation**
- DKIM missing or only revoked keys: DMARC then depends on SPF alignment alone,
  which breaks on forwarding.
- DMARC without `rua`: no reports, so problems stay invisible.
- `?all` or no `all` in SPF.

**Optional**
- DMARC `p=none` is the accepted minimum; recommend moving to `quarantine` and then
  `reject` after a few weeks of clean reports.
- MTA-STS and TLS-RPT protect inbound mail; BIMI shows a logo and needs DMARC at
  `quarantine` or `reject`.
- 1024-bit DKIM keys still work; 2048-bit is the current recommendation.

## 3. Give the fix as records

For each problem give the record type, host and value, ready to paste:

| Type | Host | Value |
| --- | --- | --- |
| TXT | `@` | `v=spf1 include:_spf.google.com ~all` |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@example.com` |

Common SPF includes: Google Workspace `include:_spf.google.com`, Microsoft 365
`include:spf.protection.outlook.com`, Zoho Mail `include:zohomail.com` (or the
regional variant shown in the Zoho admin). Take the exact include for any other service from
that service's documentation instead of guessing. Keep one SPF record per domain and
merge includes into it.

DKIM keys are generated by the mailbox provider (Google Admin: Apps > Google
Workspace > Gmail > Authenticate email; Microsoft 365: Microsoft Defender portal,
Email authentication settings, DKIM).
Tell the user where to generate it; never invent a key.

## 4. Beyond DNS

Authentication is necessary but not sufficient. When the user's goal is inbox
placement, add the checks DNS cannot show:

- Gmail and Yahoo bulk-sender rules: SPF and DKIM, DMARC aligned with the From
  domain, a one-click unsubscribe (RFC 8058 `List-Unsubscribe-Post`) for marketing
  mail, and a user-reported spam rate below 0.3% (aim for under 0.1%; monitor in
  Google Postmaster Tools).
- Sending servers need matching forward and reverse DNS (PTR) and TLS; mailbox
  providers such as Google Workspace and Microsoft 365 handle this for you.
- For cold outreach, send from a separate domain or subdomain than the main company
  domain, warm new mailboxes up gradually, keep per-mailbox daily volume modest, and
  verify lead lists before sending to keep bounces low.

## Output format

1. One-line verdict per domain (for example "example.com: ready to send, 2
   optional improvements").
2. Findings grouped as Blocking / Hurts reputation / Optional, each with the fix.
3. The DNS records to add or change, as a table.
4. What to re-check after DNS propagation (usually minutes, up to 48 hours).

## If MailBeast is connected

If the MailBeast MCP server is available (tools such as `list_mailboxes`,
`get_mailbox`), also check the sending side: run `list_mailboxes` to see each
mailbox's status, health and warmup, and `get_mailbox` for the last error of any
mailbox that is not healthy. Audit the domain of every connected mailbox. Learn more
at https://mailbeast.ai.
