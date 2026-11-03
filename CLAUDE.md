# Kubeerra Market Brief: project rules for Claude

A daily pre-market newsletter (email HTML plus A4 PDF) for Kubeerra, the digital brand of
Dhariwal Securities Private Limited. Owner and approver: Shriansh Jena.

These rules apply to this repository only. Never edit global Claude settings, the owner's
global CLAUDE.md, or anything outside this project.

## Read first

1. `docs/PROJECT_RECORD.md`, the canonical record: decisions, open questions, history. The
   Claude Docs copy ("Kubeerra Daily Market Report: Project Record") mirrors it and also holds
   summaries of confidential sources, which stay out of this repository.
2. `docs/EDITORIAL.md` for voice and story pattern, `docs/SENDING_GUIDE.md` for delivery.
3. `.claude/skills/daily-market-report/SKILL.md` for the daily procedure.

## Regulatory lane (non-negotiable)

Dhariwal Securities is an AMFI-registered Mutual Fund Distributor (ARN-369716, EUIN E708284).
It is NOT a SEBI-registered Investment Adviser, Research Analyst or PMS provider.

- Publish market information and investor education only: index-level and macro commentary,
  flows, currency, commodities, factual company and IPO news.
- Never: buy, sell or hold language; price targets; "bullish/bearish on X"; re-rating calls;
  opinions on IPO applications; grey market premium; scheme rankings by returns or
  performance, "best funds" or picks; return projections; testimonials; the words adviser,
  advisory, wealth manager or portfolio management about Kubeerra.
- Named schemes appear only as reported facts (largest net inflows, ETF turnover, open NFOs,
  fund house news), each with its category and riskometer level from the fund house's own
  document and a not-a-recommendation line; never returns or performance (D-042).
- Return illustrations: at most the firm's 12% assumed CAGR, marked illustrative, with the
  standard warning and AMFI's past-performance disclaimer.
- Every issue carries, at the bottom of the email and PDF: "AMFI-registered Mutual Fund
  Distributor" with the name and ARN (12 pt or larger in the PDF) and the standard warning,
  verbatim: "Mutual Fund investments are subject to market risks, read all scheme related documents carefully."
- Nothing is sent without Shriansh's approval. From 30 Oct 2026 issues are client editions
  for trusted clients: no internal labels or clock-time stamps (see the daily skill).

## Data rules

- Every figure comes from a page fetched that day, with its date and time recorded in the
  issue file. Never write a number from memory. Cross-check headline numbers with a
  second source. Label provisional data (FII/DII) as provisional.
- Summarise news in our own words and name the source; never copy article text or images.
- Links in what readers receive go only to kubeerra.com blog posts and service or disclosure
  pages, plus the firm's email address (D-039). Outside sources are named, never linked; their
  URLs stay in the issue file and the check report.

## Style rules

- No em dashes or en dashes anywhere: use commas, colons, parentheses or "to".
- Indian number system (₹1,23,456; crore; lakh crore), the rupee sign, a true minus sign (−).
- Sentence case headlines. Calm, specific, plain language. No crash, bloodbath, panic, frenzy.
- Colours and fonts come from `design-tokens/tokens.json` only. The project-local design
  system (navy, cobalt, teal) governs; the owner's general styling preferences do not apply.

## Commands

    python3 render/build.py issues/<date>.json            # Gmail and Outlook HTML, text, PDF, card
    python3 checks/check_issue.py issues/<date>.json       # automated checks
    python3 render/publish.py issues/<date>.json           # copy deliverables into deliverables/
    python3 render/gmail_draft.py prepare issues/<date>.json   # files for the unsent Gmail draft
    python3 render/build.py tests/fixture-issue.json      # template smoke test

## Repository hygiene

- Confidential source documents (the internal strategic record, forwarded emails) never
  enter this repository.
- `out/` is build output and is not committed. Each issue's deliverables are committed in
  `deliverables/<format>/`, keeping the 14 most recent issues; check reports, review logs and
  issue files are kept permanently (D-041).
- Web access: the owner authorises opening any public website the work needs (D-044).
- Update `docs/PROJECT_RECORD.md` in the same commit as any change it describes.
