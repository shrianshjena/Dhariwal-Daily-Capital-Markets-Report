---
name: daily-market-report
description: Produce one issue of the Kubeerra Market Brief: gather verified data with four agents, write the issue file, render the Gmail and Outlook emails, PDF and WhatsApp card, run the checks and an independent review, publish the deliverables to GitHub, hand Shriansh an approval pack and save an unsent Gmail draft. Use for the scheduled morning run or a manual run.
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
ready and list the unverified items at the top of the hand-off message. The Gmail draft comes
after the hand-off, so it never delays the pack.

## Web access

The owner authorises opening any public website the work needs (D-044). The run is unattended
and cannot answer permission prompts, so reach pages through WebSearch results or links on pages
already opened rather than typing addresses. List any page that still could not be opened in the
review log.

## The client edition (from 30 Oct 2026)

Issues go to trusted clients, so every issue is written for a general reader:
- `meta.audience` is `"client"`. No internal labels: no pilot notes, "RM", "dry run" or "not
  for clients". `meta.label` is kept for the record but never shown.
- No clock times as data stamps (no "at 8:11 AM"). Use dates and closes: "India: close,
  Thu 29 Oct 2026 · Global: US close, 29 Oct". Event times in the day-ahead section are fine.
- The registration line (name, AMFI tagline, ARN, EUIN) and the standard warning sit at the
  bottom of the emails and PDF, never at the top. The WhatsApp card carries the registration
  line but no disclaimer lines; its caption still opens with the registration line.
- Links (D-039): readers' links go only to kubeerra.com blog posts and service or disclosure
  pages (`config/publication.json`, `kubeerra_links`), which may be reused, for example the
  Learn "Read more" and the mutual fund section's `link`. Outside sources are named, never
  linked; the templates do this, so keep every `source` object with its URL in the issue file.
- Mutual fund corner (D-042): AMFI industry data; category trends (`highlights`); the schemes
  with the largest net inflows in the latest month (`inflow_leaders`, as published by a
  reputable outlet); the most traded ETFs on NSE by turnover (`etfs`); fund house news
  (`fund_news`); open NFOs by name when every one has its riskometer (`nfos`), otherwise the
  category summary (`nfo_summary`); rule changes. Every named scheme carries its category and
  riskometer level from the fund house's own document; never returns or performance, and never
  the words best, top, popular or trending about a scheme. Leave out any part the gatherer
  could not source.
- Use `day_ahead_title` when the calendar runs past the edition day.

## Steps

1. **Gather in parallel.** Launch `markets-gatherer`, `flows-global-gatherer`,
   `news-ipo-gatherer` and `funds-gatherer` together, each given the edition and session dates.
   Each returns JSON with a source URL for every figure, or null with a reason.
2. **Write the issue.** Create `issues/<edition-date>.json` against `schema/issue.schema.json`,
   using the latest issue file as the pattern. Use only figures an agent returned with a URL.
   Where two sources disagree, prefer the primary source and say which in the detail line.
   Give level figures a `change_pct` so their direction shows in green or red. Choose four to
   six stories that pass the India-relevance test. Add a new lesson (next L-number) with a
   kubeerra.com `link`. Set `meta.subject` and `meta.preheader`. Then run
   `python3 render/fill_sources.py issues/<date>.json` to rebuild the sources list.
3. **Render.** `python3 render/build.py issues/<date>.json`. It writes
   `out/<date>/kubeerra-market-brief-<date>-gmail.html`, `-outlook.html`, the text edition, the
   PDF, the WhatsApp card and caption, and previews.
4. **Check.** `python3 checks/check_issue.py issues/<date>.json`. Fix every FAIL (it fails on
   any link outside kubeerra.com and on text over a dark background in the Outlook file). Read
   every review word in context and rewrite any that read as advice or alarm. Look at
   `out/<date>/preview/` (Gmail at desktop and phone width, Outlook, Outlook with colours
   stripped, PDF pages): the PDF should run four to seven pages with no half-empty page, and no
   figure should break across lines. The check report is written to
   `deliverables/check-reports/<date>-check-report.md`.
5. **Independent review.** Give `compliance-reviewer` the rendered `out/<date>/*.txt` and the
   WhatsApp caption. Run `fact-checker` three times in parallel, one per part of the issue
   file: (a) brief, snapshot, flows, sectors and global; (b) stories and day ahead; (c) IPOs,
   mutual fund corner (including every named scheme's figure and riskometer) and learn. All
   start fresh and never see the drafting. Apply their corrections, then repeat steps 3 and 4.
   Write `deliverables/reviews/<date>-review.md` (findings and resolutions).
6. **Learning library.** Append the day's lesson to `learn/library.json` (id, date, title,
   issue, topics).
7. **Publish to GitHub.** `python3 render/publish.py issues/<date>.json` copies the deliverables
   into `deliverables/pdf`, `gmail`, `outlook`, `whatsapp` and `text`, and deletes deliverable
   files older than the 14 most recent issues (D-041). Check reports, review logs and issue
   files are never deleted.
8. **Hand off.** Send Shriansh the Gmail and Outlook HTML files, the PDF, the WhatsApp card and
   caption, the check report (suggested subject and the figures to confirm) and the review log,
   with a three-line summary. Shriansh approves and sends; see `docs/SENDING_GUIDE.md`.
9. **Gmail draft (D-043).** After the hand-off:
   - Run `python3 render/gmail_draft.py prepare issues/<date>.json`.
   - Read `out/<date>/gmail-draft/body.html`, `logo.b64` and `subject.txt`, and call the Gmail
     `create_draft` tool with: `subject` from subject.txt; `htmlBody` exactly the contents of
     body.html; no `to`, `cc`, `bcc` or plain `body`; and `attachments` holding one item:
     `content` the lines of logo.b64 joined with no breaks, `filename` "kubeerra-logo.png", `mimeType`
     "image/png", `inline` true. (body.html already points the logo at `cid:att0`.) If Gmail
     rejects the attachment (for example "Base64 decoding failed"), create the draft once more
     with `htmlBody` the contents of `body-nologo.html` and no attachments.
   - Call `get_draft` with the new draft's id and `messageFormat` PLAIN_TEXT. Gmail returns the
     draft's `htmlBody` (its own cleaned copy of the HTML; it drops the `<style>` block, which is
     expected). Write that value, unescaped, to `out/<date>/gmail-draft/returned.txt`, and run
     `python3 render/gmail_draft.py verify issues/<date>.json out/<date>/gmail-draft/returned.txt`.
   - If it prints DRAFT OK, send Shriansh the draft's view link in one line. If it prints a
     mismatch or any step fails, delete the draft with `delete_draft` and tell Shriansh to use
     the Gmail HTML file instead. Never send the draft.
10. **Record.** Commit `issues/<date>.json`, `deliverables/` (additions and deletions:
    `git add -A deliverables`) and the library update to `main` with the author
    `Shriansh Jena <89731022+shrianshjena@users.noreply.github.com>` (Vercel blocks deployments
    from authors it cannot match), and push. If the process changed, update
    `docs/PROJECT_RECORD.md` in the same commit.

## Failure rules

- A figure that cannot be sourced is left out, never estimated.
- If NSE provisional FII/DII data is not out, say so in the tile detail; do not use a guess.
- If any FAIL remains, stop and report it rather than delivering the issue.
