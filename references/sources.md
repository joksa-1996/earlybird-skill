# Sources

All sources are free and public. The script covers the first six; the rest are web-search only.

| Source | Signal kind | What it shows | Script key |
| --- | --- | --- | --- |
| Hacker News Show HN / Launch HN | launch, accelerator | product launches; Launch HN = YC company | `hn` |
| Hacker News posts and comments | intent | people mentioning a competitor or describing the problem | `hn_intent` |
| HN "Who is hiring" (monthly) | sales_hiring, hiring | startups posting their first sales role | `hn_hiring` |
| Y Combinator directory | accelerator | newly listed YC companies | `yc` |
| GitHub | repo_traction | new repos with fast star growth (orgs or repos with a product site) | `github` |
| SEC Form D | funding | US startups that just raised, with executives' names | `sec_formd` |
| UK Companies House | incorporation | newly registered UK software companies | `companies_house` |
| Product Hunt | launch | launches with traction | web search |
| Reddit (r/SaaS, r/startups, r/sales, r/SideProject) | intent, launch | "I launched", "how do I get first customers", tool comparisons | web search |
| Funding news | funding | announced pre-seed and seed rounds outside the US | web search |

## Fallback searches

Use these when the script cannot run or a source failed. Replace `{competitor}` and `{phrase}` with values from the profile, and keep results inside the time window.

- **Launches:** `"Show HN" site:news.ycombinator.com` for this week; `producthunt.com` launches this week in the ICP's category.
- **Funding:** `raises pre-seed {industry} {month year}`; `seed round {industry} startup {month year}`; for Europe also `{country} startup raises seed`.
- **First sales hire:** `"founding account executive" startup`; `"first sales hire" {industry}`; the current month's "Ask HN: Who is hiring?" thread.
- **Intent:** `"{competitor}" alternative` on reddit.com and news.ycombinator.com; `"{phrase}"` on reddit.com; `"{competitor}" vs`.
- **YC:** the YC companies directory filtered to the latest batch.

For every search result you use, open the page, check the date and record the link. A search snippet alone is not enough to list a lead.

## Signal kinds

`launch`, `accelerator`, `funding`, `incorporation`, `repo_traction` say "a new startup exists". `sales_hiring`, `first_sales_hire` and `intent` (competitor or pain) say "they need something now". The second group always outranks the first (see `scoring.md`).
