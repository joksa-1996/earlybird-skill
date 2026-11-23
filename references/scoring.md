# Scoring

## What the script computes (`rule_score`, per offer)

For each company and offer:

1. Every signal gets a tag: its kind, or an intent topic (`competitor`, `pain`, `first_sales_hire`).
2. Value of a signal = weight of its tag × signal strength × age decay × direct-need boost.
   - Default weights: competitor 4.0, pain 3.0, first_sales_hire 2.0, funding 2.0, accelerator 2.0, sales_hiring 1.5, launch 1.5, incorporation 0.6, repo_traction 0.5, hiring 0.3. An offer's `weights` in the profile override these.
   - Age decay: value halves every 14 days; every 7 days for intent (a question asked last month is already answered); every 45 days for job posts (a role stays open for weeks).
   - Direct-need boost: ×2.5 for competitor, pain, first_sales_hire and sales_hiring.
3. Only the strongest signal per source counts. They are summed.
4. Corroboration: +35% for every additional independent source, at most ×2.
5. Soft limits: team above `max_team` ×0.35; round above `max_raise` ×0.5; only non-sales job posts (no startup signal) ×0.6. Each one adds a flag.

## What you add (fit)

Fit is 0 to 10 per offer: how well the company matches the profile's `icp` and the offer's `pitch`, based on the website, description and signals. Final score = `rule_score` × (0.4 + 1.2 × fit / 10). Fit 0 cuts the score to 40%; fit 10 raises it to 160%.

Then apply the hard filters from the profile (`countries`, `company_size_max`, `exclude`). Drop what fails, and say how many were dropped.

## Fallback mode (no script)

Score by hand with the same logic:

- **Tier A:** a person or company with a direct need (mentions a competitor, asks about the problem, posts a first sales role) and fit 7 or more.
- **Tier B:** a new startup signal (launch, round, YC) from 2 or more sources, or a direct need with fit 5 or 6.
- **Tier C:** everything else that passes the hard filters.

In the report, show the tier in place of the numeric score and say the run used web search only.
