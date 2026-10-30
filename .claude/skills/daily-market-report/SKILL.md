---
name: daily-market-report
description: Produce one issue of the Kubeerra Market Brief: gather verified data with four agents, write the issue file, render email HTML and PDF, run the checks and an independent review, and hand Shriansh an approval pack. Use for the scheduled morning run or a manual run.
---

# Daily Kubeerra Market Brief

Read `CLAUDE.md`, `docs/EDITORIAL.md` and the decision log in `docs/PROJECT_RECORD.md` first.
Nothing in this procedure sends email or posts anything: Shriansh approves and sends.

## Inputs

- Edition date (YYYY-MM-DD): the morning the issue goes out (today, in IST).
- Session date: the previous NSE trading day. Check NSE's trading holiday list; if the edition
  date is a weekend or an NSE holiday, there is no issue: say so in one line and stop.

## Timing

The scheduled run starts at about 7:10 AM IST on weekdays. The approval pack must reach
Shriansh by 9:00 AM IST. If the independent review is not finished by 8:45 AM, deliver what is
ready and list the unverified items at the top of the hand-off message.

## The client edition (from 30 Oct 2026)

Issues go to trusted clients, so every issue is written for a general reader:
- `meta.audience` is `"client"`. No internal labels: no pilot notes, "RM", "dry run" or "not
  for clients". `meta.label` is kept for the record but never shown.
- No clock times as data stamps (no "at 8:11 AM"). Use dates and closes: "India: close,
  Thu 29 Oct 2026 · Global: US close, 29 Oct". Event times in the day-ahead section are fine.
- The registration line (name, AMFI tagline, ARN, EUIN) and the standard warning sit at the
  bottom of the email and PDF, never at the top. The WhatsApp card carries the registration
  line but no disclaimer lines; its caption still opens with the registration line.
- Mutual fund content stays at industry and category level; new fund offers appear only as a
  category summary.
- Use `day_ahead_title` when the calendar runs past the edition day.

## Steps

1. **Gather in parallel.** Launch `markets-gatherer`, `flows-global-gatherer`,
   `news-ipo-gatherer` and `funds-gatherer` together, each given the edition and session dates.
   Each returns JSON with a source URL for every figure, or null with a reason.
2. **Write the issue.** Create `issues/<edition-date>.json` against `schema/issue.schema.json`,
   using the latest issue file as the pattern. Use only figures an agent returned with a URL.
   Where two sources disagree, prefer the primary source and say which in the detail line.
   Give level figures a `change_pct` so their direction shows in green or red. Choose four to
   six stories that pass the India-relevance test. Add a new lesson (next L-number). Set
   `meta.subject` and `meta.preheader`. Then run
   `python3 render/fill_sources.py issues/<date>.json` to rebuild the sources list.
3. **Render.** `python3 render/build.py issues/<date>.json` (the hosted logo URL is in
   `config/publication.json`).
4. **Check.** `python3 checks/check_issue.py issues/<date>.json`. Fix every FAIL. Read every
   review word in context and rewrite any that read as advice or alarm. Look at
   `out/<date>/preview/` (email at desktop and phone width, PDF pages): the PDF should run four
   to six pages with no half-empty page, and no figure should break across lines.
5. **Independent review.** Give `compliance-reviewer` the rendered `out/<date>/*.txt` and the
   WhatsApp caption. Run `fact-checker` three times in parallel, one per part of the issue
   file: (a) brief, snapshot, flows, sectors and global; (b) stories and day ahead; (c) IPOs,
   mutual fund corner and learn. All start fresh and never see the drafting. Apply their
   corrections, then repeat steps 3 and 4. Write `issues/<date>-review.md` (findings and
   resolutions).
6. **Learning library.** Append the day's lesson to `learn/library.json` (id, date, title,
   issue, topics).
7. **Hand off.** Send Shriansh the email HTML, the PDF, the WhatsApp card and caption,
   `issues/<date>-check-report.md` (suggested subject and the figures to confirm) and the
   review log, with a three-line summary. Shriansh approves and sends; see
   `docs/SENDING_GUIDE.md`.
8. **Record.** Commit the issue JSON, check report, review log and library update to `main`
   with the author `Shriansh Jena <89731022+shrianshjena@users.noreply.github.com>` (Vercel
   blocks deployments from authors it cannot match), and push. If the process changed, update
   `docs/PROJECT_RECORD.md` in the same commit.

## Failure rules

- A figure that cannot be sourced is left out, never estimated.
- If NSE provisional FII/DII data is not out, say so in the tile detail; do not use a guess.
- If any FAIL remains, stop and report it rather than delivering the issue.
