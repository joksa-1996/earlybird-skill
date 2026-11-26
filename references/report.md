# Report format

Write in the user's language. Keep it short enough to read in two minutes.

```markdown
# Earlybird radar: {date range}

{One sentence: how many new leads, the strongest signal of the week, anything unusual.}

## {Offer label}

| Company | What they do | Country | Signal date | Score | Why now | Source |
| --- | --- | --- | --- | --- | --- | --- |
| Acme | AI invoicing for agencies | US | 20 Nov | 31 | Posted a Founding AE role; 4 people | [HN](...) |

## Contact first ({N} ready now)

1. **Acme** ({offer}): {why, in one line}. Suggested first line: "{one sentence based on the actual signal}"
2. ...
{One entry per lead that qualifies. If none: "Nobody is ready to contact this week; the strongest lead is {X}, worth watching."}

## People asking for this

{Intent signals without a company: name or handle, what they asked, date, link.}

---
Sources: {source: count, ...}. Failed or skipped: {list}. {N} leads dropped by filters, {M} with low fit left out.
```

Rules:
- Every lead that fits goes in the table (see `scoring.md`, "Which leads make the report"). No row limit. Sort by final score, highest first.
- If a table has more than 25 rows, keep the "What they do" and "Why now" cells to a few words so it stays scannable; do not drop rows.
- "Why now" is the strongest signal, not a description of the company.
- The suggested first line refers to the real signal ("saw your Founding AE post on HN"), never to things you guessed.
- Leave out empty sections.
