# The radar profile (`radar-profile.json`)

One file holds everything the radar needs: who the user sells to, what they sell (1 to 3 offers), and which leads they have already seen.

## Questions to ask (at most 3 at a time)

1. What do you sell, in one sentence? Do you have more than one offer? (up to 3)
2. Who buys it: industry, company size, stage, countries?
3. Which tools or alternatives do your buyers use or compare you with? (competitor names)
4. What do your buyers say when they have the problem you solve? (short phrases, as people actually write them: "how do I find my first customers", "linkedin outreach")
5. Anything to exclude? (consumer apps, agencies, crypto, a country...)
6. Optional: a contact email (only used for the SEC data source, which requires one).

Do not guess answers. If the user skips a question, leave the field empty.

## Format

```json
{
  "icp": "Early-stage B2B SaaS startups (pre-seed to Series A), 2-20 people, no sales team yet. US, Canada, UK.",
  "countries": ["US", "CA", "GB"],
  "company_size_max": 20,
  "exclude": ["consumer apps", "crypto tokens", "funds", "agencies"],
  "contact_email": "",
  "sources": ["hn", "hn_intent", "hn_hiring", "yc", "github", "sec_formd"],
  "offers": [
    {
      "key": "main",
      "label": "Acme Outreach",
      "pitch": "LinkedIn outreach tool for founders who sell themselves.",
      "competitors": ["expandi", "waalaxy", "heyreach"],
      "pain_phrases": ["linkedin outreach", "founder led sales", "first customers"],
      "max_team": 20,
      "max_raise": 15000000,
      "weights": {}
    }
  ],
  "seen": []
}
```

## Fields

- `icp`: free text; used for the 0 to 10 fit score.
- `countries`, `company_size_max`, `exclude`: hard filters, applied after scoring.
- `sources`: which collectors to run. Leave out `sec_formd` if the user only sells outside the US, and `companies_house` unless they target the UK and have the free key.
- `offers[].competitors`: lowercase names. A public post mentioning one is the strongest buying signal.
- `offers[].pain_phrases`: short, literal phrases (2 to 4 words work best). They are searched as written.
- `offers[].max_team`, `offers[].max_raise`: soft limits; bigger companies are scored down, not removed.
- `offers[].weights`: optional overrides of the default weights in `scoring.md` (for example `{"funding": 3.0}` for an offer that sells best right after a round).
- `seen`: company keys from earlier reports. Add the new ones after every run.
