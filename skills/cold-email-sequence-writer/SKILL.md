---
name: cold-email-sequence-writer
description: Write a B2B cold email sequence (3 to 5 steps) with subject lines, short personalized bodies, a single low-friction call to action, follow-up timing, A/B variants and merge tags, following deliverability and anti-spam rules. Use when the user asks to write cold emails, an outreach sequence, follow-ups, or to improve an existing cold email campaign.
---

# Cold email sequence writer

Write sequences a real person would answer: short, specific to the recipient, honest
about who is writing and why, and easy to say no to.

## 1. Collect the brief

Ask only for what is missing. If the user gave enough, start writing.

- **Who is it for**: role, company type and size, region (region decides language,
  tone and compliance).
- **The offer**: what you do, for whom, and the one outcome it brings.
- **Proof**: a customer, a number, a case; anything checkable. Never invent proof.
- **Call to action**: the smallest next step (a reply, a 15-minute call, "worth a
  look?").
- **Sender**: name, role, company, and the signature details.
- **Available data per lead**: which fields exist (first name, company, job title,
  website, a custom field such as a recent event). Only use fields the user has.

## 2. Rules for every email

- **Length**: 50 to 125 words for step 1; follow-ups shorter (25 to 75).
- **Subject**: 2 to 5 words, plain, lowercase or sentence case, no clickbait, no
  "Re:" or "Fwd:" on a first message, no ALL CAPS, no emoji in B2B.
- **Opening line**: about them, not about you. Use a real detail when you have one;
  otherwise a relevant observation about their role or market. No "I hope this email
  finds you well".
- **One call to action**, phrased as a question that is easy to answer.
- **Plain text**: no images, attachments or tracking-heavy formatting in step 1; at
  most one link, and none in step 1 if you can avoid it.
- **No spam patterns**: no "100% free", "guaranteed", "act now", excessive
  exclamation marks, or misleading claims.
- **Merge tags**: write them as `{{first_name}}`, `{{company_name}}`,
  `{{job_title}}`, `{{website}}` (adapt the syntax to the user's tool). Every
  sentence with a merge tag must still read naturally if the field is empty, or set a
  fallback where the tool supports it.
- **Opt-out and identity**: end with a short way to opt out ("If this is not
  relevant, just tell me and I will not follow up.") and keep a real signature with
  the company's postal address where the law requires it (see Compliance).

## 3. Sequence structure

Default 4 steps; each follow-up adds a new angle instead of "just bumping this".

| Step | Wait after previous | Purpose |
| --- | --- | --- |
| 1 | - | Relevance + offer + one question |
| 2 | 2-3 business days | New angle: a proof point or a short case |
| 3 | 4-5 business days | Different value: a useful insight, resource or objection handled |
| 4 | 6-8 business days | Polite close-out: "should I close the loop?" |

Follow-ups usually go in the same thread (reply to step 1), so they need no new
subject unless the user wants a fresh thread.

## 4. A/B variants

Offer 2 variants for what moves results most: the subject of step 1 and the opening
line. Keep the rest identical so the test measures one thing. Note how many leads
each variant needs before a difference means anything (roughly 100+ sends per
variant for reply rate differences you can trust).

## 5. Output format

For each step:

```
Step 1 (day 0)
Subject A: ...
Subject B: ...
Body:
...
```

Then a table of the merge tags used and which lead field each needs, and a short
list of assumptions you made about the offer or audience.

## Compliance (state this briefly, not as legal advice)

- **US (CAN-SPAM)**: accurate From and subject, a working opt-out honored within 10
  business days, and the sender's valid postal address.
- **EU/UK (GDPR, PECR)**: B2B outreach usually relies on legitimate interest; the
  message must be relevant to the recipient's role, say where the data came from if
  asked, and stop on request. Personal (non-business) addresses need consent in many
  countries.
- **Canada (CASL)**: requires consent; implied consent applies in narrow cases (for
  example a published business address with no "no unsolicited email" notice and a
  message relevant to the role).
- Never write deceptive subject lines, fake "Re:" threads, or messages that hide who
  is sending.

Suggest the user checks local rules with counsel for regulated industries or large
campaigns.

## If MailBeast is connected

If the MailBeast MCP server is available (tools such as `create_campaign`,
`send_test_email`), offer to load the sequence:

1. Show the final sequence and get the user's approval.
2. `create_campaign` with the steps; put A/B versions in `variants`. MailBeast merge
   tags are snake_case (`{{first_name}}`, `{{company_name}}`, custom fields as
   `{{custom_<field>}}`); unknown tags render as empty text. The campaign is created as
   a draft and sends nothing.
3. Offer `send_test_email` of step 1 to the user's own address.
4. Start sending with `start_campaign` only when the user explicitly asks.

Learn more at https://mailbeast.ai.
