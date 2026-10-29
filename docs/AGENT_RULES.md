# Rules shared by every gatherer (referenced by each agent file)

- Every figure comes from a page you opened with WebFetch, or from WebSearch results that
  clearly refer to the right date. Never write a figure from memory or estimate it; return
  null with a reason instead.
- Prefer primary sources (NSE, NSE Indices, BSE, RBI, FBIL, CCIL, NSDL, AMFI, SEBI, company
  filings). When a primary site blocks fetching, use reputable outlets (Reuters, Economic
  Times, Mint, Business Standard, Moneycontrol, Business Today, NDTV Profit, CNBC-TV18).
- Cross-check headline figures against a second source and report whether they agree.
- Record the date, and the time and timezone where relevant, for every figure.
- Summarise in your own words; no quote longer than 10 words; never copy headlines.
- Facts only: no buy, sell or hold views, targets, forecasts, IPO opinions or grey market
  premium figures.
- Return only a JSON object in a ```json block, then at most three lines on gaps.
