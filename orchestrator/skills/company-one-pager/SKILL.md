---
name: company-one-pager
description: Recipe for a pitch-book company one-pager. Use when asked for a company profile or one-pager.
metadata:
  adk_additional_tools: [get_company_profile, get_recent_deals]  # tools this recipe unlocks
---
# Company one-pager

Gather data first: call `get_company_profile`, then `get_recent_deals` for the company's sector.

Write exactly these sections, in this order:

1. **Snapshot**: ticker, sector, HQ, CEO, coverage MD (one line each).
2. **Financials**: revenue and EBITDA in USD millions, plus EBITDA margin (EBITDA / revenue, one decimal).
3. **Sector deal context**: the recent deals as bullets: target, acquirer, value, EV/EBITDA, year.
4. **Angle**: one sentence on why this company could be an M&A candidate now.

Rules: under 200 words; numbers only from the tools, never invented; if a tool returns an error, say "not available".
