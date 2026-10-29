---
name: daily-market-report
description: Produce one issue of the Kubeerra Market Brief: gather verified data with four agents, write the issue file, render email HTML and PDF, run the checks and an independent review, and hand Shriansh an approval pack. Use for the daily morning run or a dry run.
---

# Daily Kubeerra Market Brief

Read `CLAUDE.md` and `docs/EDITORIAL.md` first. Nothing in this procedure sends email.

## Inputs

- Edition date (YYYY-MM-DD): the morning the issue goes out.
- Session date: the previous NSE trading day. Check NSE's trading holiday list; if the edition
  date is a holiday, there is no issue.

## Timing (morning edition)

Start about 6:45 AM IST, after US markets close and before Asia is far into its session.
The approval pack should be ready by 7:30 AM; Shriansh sends at about 8:00 AM.

## Steps

1. **Gather in parallel.** Launch `markets-gatherer`, `flows-global-gatherer`,
   `news-ipo-gatherer` and `funds-gatherer` together, each given the edition and session dates.
   Each returns JSON with a source URL for every figure, or null with a reason.
2. **Write the issue.** Create `issues/<edition-date>.json` against `schema/issue.schema.json`.
   Use only figures an agent returned with a URL. Where two sources disagree, prefer the
   primary source and say which in the detail line. Choose four to six stories that pass the
   India-relevance test. Set `meta.subject` and `meta.preheader`. Then run
   `python3 render/fill_sources.py issues/<date>.json` to rebuild the sources list.
3. **Render.** `python3 render/build.py issues/<date>.json --logo-url <hosted logo URL>`
4. **Check.** `python3 checks/check_issue.py issues/<date>.json`. Fix every FAIL. Read every
   review word in context and rewrite any that read as advice or alarm. Look at
   `out/<date>/preview/` (email at desktop and phone width, PDF pages): the PDF should run four
   to six pages with no half-empty page, and no figure should break across lines.
5. **Independent review.** Give `compliance-reviewer` the rendered `out/<date>/*.txt` and the
   WhatsApp caption. Run `fact-checker` three times in parallel, one per part of the issue
   file: (a) brief, snapshot, flows, sectors and global; (b) stories and day ahead; (c) IPOs,
   mutual fund corner and learn. All start fresh and never see the drafting. Apply their
   corrections, then repeat steps 3 and 4.
6. **Learning library.** Append the day's lesson to `learn/library.json` (id, date, title, url).
7. **Hand off.** Deliver the HTML, the PDF, the WhatsApp card and caption, and
   `check-report.md` (suggested subject and the figures to confirm). Shriansh approves and
   sends; see `docs/SENDING_GUIDE.md`.
8. **Record.** Commit the issue JSON, the library update and the check report. If the process
   changed, update `docs/PROJECT_RECORD.md` in the same commit.

## Failure rules

- A figure that cannot be sourced is left out, never estimated.
- If NSE provisional FII/DII data is not out, say so in the tile detail; do not use a guess.
- If any FAIL remains, stop and report it rather than delivering the issue.
