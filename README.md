# Earlybird: a free lead radar skill for AI assistants

Earlybird finds B2B leads at the moment they are most likely to buy: startups that just launched, just raised, just posted their first sales role, and people publicly asking for a tool like yours. Every lead comes with the reason ("why now") and the source link.

It runs inside the AI assistant you already use: Claude, ChatGPT, Codex or any tool that supports the open Agent Skills format (a folder with a `SKILL.md`). No server, no account, no cost beyond your assistant's plan.

## What you get

- A weekly (or daily) report of new leads that match your ICP, one table per offer
- The 3 leads to contact first, with a first line based on the real signal
- People on Hacker News who mention your competitors or describe the problem you solve
- Free public sources only: Hacker News, HN "Who is hiring", Y Combinator, GitHub, SEC Form D, UK Companies House, plus web search for Product Hunt, Reddit and funding news

## Install

| Tool | How |
| --- | --- |
| **Claude** (web and desktop) | Download this repo as a ZIP and upload it as a skill in Claude's settings. Turn on code execution so the collector script can run. |
| **ChatGPT** | Download the ZIP and upload it under Skills (Create, then Upload from your computer). Availability of Skills depends on your plan and workspace settings. |
| **Claude Code** | Copy the folder to `~/.claude/skills/earlybird`. |
| **Codex and other agents** | Copy the folder into the tool's skills directory (see its docs for the Agent Skills format). |
| **Anything else** | Paste `SKILL.md` into a project's or custom assistant's instructions and add the `references` files as knowledge. Without code execution it runs in web-search mode. |

Menu names change often; if you can't find Skills, search your assistant's help for "skills".

## First run

Say: **"Set up my Earlybird radar."** The assistant asks what you sell, who buys it and which competitors your buyers use, and saves `radar-profile.json`. Then: **"Run my radar for the last 14 days."**

For a weekly report, ask your assistant to schedule it, if it supports scheduled tasks: "Every Monday at 8:00, run my Earlybird radar for the last 7 days."

## Optional keys

| Variable | Why | Where to get it |
| --- | --- | --- |
| `contact_email` (in the profile) | SEC requires a contact for Form D data | your email |
| `COMPANIES_HOUSE_API_KEY` | new UK companies | free at developer.company-information.service.gov.uk |
| `GITHUB_TOKEN` | higher GitHub rate limit | github.com/settings/tokens (no scopes needed) |

## Outreach

Earlybird has no LinkedIn data and never contacts anyone. If you have an outreach, LinkedIn or CRM connector in your assistant, Earlybird can hand leads to it with the "why now" context, after you approve each step.

## Run the collector yourself

```bash
python scripts/collect.py collect --profile radar-profile.json --days 7 --out signals.json
python scripts/collect.py jobs --company acme
python scripts/collect.py site --url https://acme.com
```

Python 3.9+, standard library only.

## Privacy

Earlybird reads public sources and keeps results where you run it. It lists people only when a public source names them (company registries, SEC filings, public posts). If you contact them, give an easy way to opt out. This is not legal advice.

## License

MIT
