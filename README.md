<p align="center">
  <img src="assets/logo.png" alt="MailBeast.ai" width="80" height="80" />
</p>

<h1 align="center">Cold email skills for AI agents</h1>

<p align="center">
  Free Agent Skills for cold email and deliverability: write sequences, audit SPF/DKIM/DMARC,
  decode bounces and triage replies. Works in Claude, Claude Code, Cursor, Codex, Gemini CLI and
  any agent that supports <code>SKILL.md</code>.
</p>

Built and maintained by [MailBeast.ai](https://mailbeast.ai), a cold email outreach platform.
The skills work on their own; none of them needs a MailBeast account.

## Skills

| Skill | What it does |
| --- | --- |
| [`cold-email-sequence-writer`](skills/cold-email-sequence-writer/SKILL.md) | Writes a 3-5 step B2B cold email sequence: subjects, short personalized bodies, one call to action, follow-up timing, A/B variants, merge tags and compliance basics. |
| [`email-deliverability-audit`](skills/email-deliverability-audit/SKILL.md) | Looks up a sending domain's SPF (including the 10-lookup limit), DKIM, DMARC, MX, MTA-STS, TLS-RPT and BIMI and gives the exact DNS records to fix each problem. |
| [`email-bounce-decoder`](skills/email-bounce-decoder/SKILL.md) | Reads bounce messages and SMTP codes (550 5.1.1, Gmail 5.7.26, Microsoft 5.7.708...) and tells a bad address from a temporary failure or a block against the sender. |
| [`cold-email-reply-triage`](skills/cold-email-reply-triage/SKILL.md) | Sorts outreach replies (interested, meeting, referral, not now, unsubscribe, out of office...), extracts dates and referred contacts, and drafts short answers. |

## Install

**Any agent (skills CLI)**

```bash
npx skills add mailbeast/cold-email-skills
```

**Claude Code** (as a plugin)

```
/plugin marketplace add mailbeast/cold-email-skills
/plugin install cold-email-skills@mailbeast-skills
```

**Claude apps** - download a skill folder (for example `skills/email-bounce-decoder`), zip it
and upload it as a custom skill in Claude's settings.

**Other agents** - copy a folder from `skills/` into your agent's skills directory (for Claude
Code: `~/.claude/skills/`).

## Data and network use

The skills are plain instructions with no code. `email-deliverability-audit` looks up the
public DNS records of the domain you name, with `dig` or DNS over HTTPS (Cloudflare or
Google), so that domain name goes to the DNS resolver. Nothing else leaves your agent unless
you connect the optional MailBeast MCP server below.

## Use with MailBeast (optional)

Each skill has a short section for the [MailBeast MCP server](https://github.com/mailbeast/mailbeast-mcp)
(`https://mcp.mailbeast.ai/mcp`). With it connected, the agent can load a sequence into a draft
campaign, check the health of your sending mailboxes, pull bounce analytics and answer replies
from the mailbox that owns the thread.

## Contributing

Issues and pull requests are welcome: new bounce codes, better copy rules, more DKIM
selectors. Keep skills useful without any particular product.

## License

[MIT](LICENSE) - free to use, change and share.
