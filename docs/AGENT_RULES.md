# Rules shared by every gatherer (referenced by each agent file)

- Every figure comes from a page you opened with WebFetch, or from WebSearch results that
  clearly refer to the right date. Never write a figure from memory or estimate it; return
  null with a reason instead.
- Prefer primary sources (NSE, NSE Indices, BSE, RBI, FBIL, CCIL, NSDL, AMFI, SEBI, company
  filings). When a release states a cause (AMFI on asset or flow changes, for example), quote
  that cause rather than inferring one. When a primary site blocks fetching, use reputable outlets (Reuters, Economic
  Times, Mint, Business Standard, Moneycontrol, Business Today, NDTV Profit, CNBC-TV18).
- Cross-check headline figures against a second source and report whether they agree.
- Record the date, and the time and timezone where relevant, for every figure.
- Summarise in your own words; no quote longer than 10 words; never copy headlines.
- Facts only: no buy, sell or hold views, targets, forecasts, IPO opinions or grey market
  premium figures.
- Never cite a page that shows or links to grey market premium (GMP) content, or that carries
  a subscribe or avoid rating. IPO aggregators (IPO Gyani, Investorgain, Chittorgarh, IPO Watch,
  Dhan's IPO blog) and Groww blog pages (a "What is Grey Market Premium?" link in their
  navigation) are out. Open each IPO page and search it for "GMP" and "grey market" before
  citing it. Pages that passed on 29 Oct 2026: Business Standard, Outlook Money, HDFC Sky news
  and IPO pages, Kotak Neo news, Upstox news, JM Financial market news, PTI-Bhasha wire copy.
  Added on 30 Oct 2026: Angel One news IPO pages, Kotak Neo IPO pages, Fintechbiznews,
  Cafemutual, Corplaw Updates and Upstox's FII/DII data page. Out on 30 Oct 2026: 5paisa (its
  footer links to a GMP explainer) and Tapetide (its IPO section shows GMP).
- Not reporting, so never cited: indianopinion.org (AI-written summaries of other outlets; never
  label them Reuters) and broker marketing pages such as Admirals' traders' blog. Label wire copy
  carried elsewhere as "Reuters via <site>" or "PTI via <site>".
- FII/DII: cite a page that shows the day's provisional figures and passes the GMP check
  (Upstox's FII/DII data page did on 30 Oct); give month-to-date totals only from such a page.
- Subscription multiples change through the day: give the time of the reading, prefer the
  end-of-day figure, and expect aggregators to differ (EAAA was reported at 5.51x and 5.25x on
  different bases). HDFC Sky's 5:00 PM subscription articles can be incomplete (on 29 Oct they
  gave 0.70x and 0.45x against end-of-day 1.16x and 2.65x); Kotak Neo IPO pages show a day-wise
  table with a "last updated" time.
- Return only a JSON object in a ```json block, then at most three lines on gaps.
