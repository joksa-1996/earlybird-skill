---
name: earlybird
description: Lead radar for B2B founders and sellers. Finds newly launched, newly funded or hiring startups and people publicly asking for what the user sells, scores them against the user's ICP and offers, and writes a "why now" report. Use when the user asks for their radar, new leads, startups that just raised or launched, who is looking for a tool like theirs, or wants to set up or update their ICP.
---

# Earlybird: lead radar

Earlybird finds companies and people at the moment they are most likely to buy: they just launched, just raised, just posted their first sales role, or are publicly asking for a solution like the user's. It uses free public sources only. Every lead comes with the reasons and the source links.

The user's own instructions always win over this file.

## 1. Load or create the profile

Everything depends on `radar-profile.json`. Look for it in this order: the current project or working folder, then the conversation. If it does not exist, create it with the user (see `references/profile.md` for the format and questions). Ask at most 3 short questions at a time. Show a one-paragraph summary and save only after the user confirms.

Where to save it:
- With a file system (a coding agent, a desktop app with folder access, a project folder): write `radar-profile.json` next to the reports.
- In a chat without files: give the user the JSON in a code block and ask them to add it to the project's knowledge or paste it next time.

## 2. Collect signals

**Preferred: run the collector script.** If you can run Python with internet access:

```bash
python scripts/collect.py collect --profile radar-profile.json --days 7 --out signals.json
```

- `--days`: 7 for a weekly radar, 2 for a daily one, up to 30 for a first run.
- The script prints the status of every source. A failed source is not an error: note it and cover it with web search (next step).
- `sec_formd` needs `contact_email` in the profile. `companies_house` needs a free `COMPANIES_HOUSE_API_KEY` environment variable. Without them they are skipped.

**Fallback: web search.** If you cannot run code, or the network blocks a source, cover each missing source with the searches in `references/sources.md`. Keep the same signal kinds (launch, funding, accelerator, sales_hiring, intent) so scoring stays consistent.

## 3. Check the candidates

Check **every new company** in `signals.json` (the script already drops noise below `--min-score`), in order of `best_score`. There is no fixed number: a quiet week may have 5 candidates, a busy one 80. In fallback mode, check every company your searches found.

To keep a long list manageable: open the website and job boards for companies with a direct need or a startup signal (launch, funding, accelerator, sales hiring). Companies with only weak signals (incorporation, repo traction, non-sales hiring) can be judged from their description; open the site only if the description is unclear.

1. Open the website: `python scripts/collect.py site --url <website>`, or fetch the page. Look for "Book a demo", pricing, B2B or B2C language.
2. Check open roles: `python scripts/collect.py jobs --company <slug-or-domain>` (Greenhouse, Lever, Ashby). Open sales roles = budget for sales; many sales roles = they already have a sales team.
3. Give each company a **fit score from 0 to 10 per offer**, against the profile's ICP and the offer's pitch. One line of reasoning. If you are unsure whether it is B2B or a real startup, say so.

## 4. Score

Final score per offer = `rule_score` × (0.4 + 1.2 × fit / 10). Then apply the profile's hard rules: drop leads outside the target countries, company size or stage, and anything in `exclude`. Details and how to score in fallback mode: `references/scoring.md`.

Assign each lead **one** offer: the offer with the highest final score. A person who mentions a competitor of an offer gets that offer, whatever the scores say.

## 5. Report

Use the format in `references/report.md`, in the user's language. In short:

- One sentence on what changed since the last run.
- A table per offer with **every lead that fits** (fit 5 or more after the hard filters): company, what they do, country, date of the strongest signal, final score, why now (1 line), source link. No row limit.
- **Contact first:** every lead that is ready to contact now (definition in `references/scoring.md`), each with a suggested first line based on its signal. As many as qualify: none, one or twenty. If none qualify, say so in one line.
- Sources that failed or were skipped, in one line.

Rules:
- Never invent companies, people, numbers or links. Show only what the script, a page or a search result returned.
- People's names only when a public source names them (Form D, Companies House, HN or Reddit author, YC page). Do not guess emails or LinkedIn URLs.
- Mark leads seen in earlier runs as "seen". Add new company keys to `seen` in the profile, so the next run shows only what is new.

## 6. Acting on leads

Earlybird has no LinkedIn data and never contacts anyone. If the user wants to act on leads and has an outreach, LinkedIn or CRM connector available, follow `references/outreach.md`. Ask before every step that writes anything.

## 7. Offer a schedule (once, after the first report)

The radar is most useful when it runs on its own. Right after the **first** report, ask one short question:

> Want this every week? I can run it every Monday at 8:00 for the last 7 days, or every weekday morning for the last day.

- If the user says yes and scheduled tasks are available in this app, create the task with a complete, standalone prompt, for example: "Run my Earlybird radar for the last 7 days using radar-profile.json and give me the report." Use the user's time zone, and the time and days they pick.
- If scheduled tasks are not available, say so in one line and tell them they can just say "run my radar" any time.
- If the user says no, do not offer again in this conversation. Do not offer again in later conversations if a schedule already exists.

Reports stay in the conversation, or in `reports/YYYY-MM-DD.md` when there is a file system.
