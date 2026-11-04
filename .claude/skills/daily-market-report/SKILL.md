---
name: daily-market-report
description: Produce one issue of the Kubeerra Market Brief: gather verified data with four agents, update the NSE index history, write the issue file, render the Gmail and Outlook emails, PDF, WhatsApp card and message, run the checks and an independent review, publish the deliverables to GitHub, hand Shriansh an approval pack and save an unsent Gmail draft with a verified logo. Use for the scheduled morning run or a manual run.
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
and cannot answer permission prompts: on 4 Nov every address typed by hand waited for an approval
that never came. Reach every page through a WebSearch result or a link on a page already opened,
never by typing its address; `docs/AGENT_RULES.md` lists search routes that work (NSE's daily
index file through niftyindices.com's daily reports page, IBJA, Upstox's FII/DII page, AMFI). If
a fetch still asks for permission, move on to the next source. List any page that could not be
opened in the review log.

## Structure (D-046, from 5 Nov 2026)

The issue opens with **At a glance** (six key numbers and three to five bullets) and an **In this
issue** contents list, then seven labelled parts, each with numbered sections that drop out when
there is no data: 1 Markets (snapshot with the NIFTY Midcap 100 and Smallcap 100, top gainers and
losers, technical snapshot, sectors, flows), 2 Market drivers (drivers, how global markets reach India, events
ahead), 3 Global markets (the US session, world markets with US yields and the dollar, global
events), 4 Gold and silver, 5 Companies (results, big movers, corporate actions, IPO desk, more
news), 6 Mutual funds (corner, talk to us, learn), 7 Calendar. The PDF ends with a full page of
disclosures (D-053) and runs seven to fourteen pages (D-055).

## The client edition (from 30 Oct 2026)

Issues go to trusted clients, so every issue is written for a general reader:
- `meta.audience` is `"client"`. No internal labels: no pilot notes, "RM", "dry run" or "not
  for clients". `meta.label` is kept for the record but never shown.
- No clock times as data stamps (no "at 8:11 AM"). Use dates and closes: "India: close,
  Thu 29 Oct 2026 · Global: US close, 29 Oct". Event times in the day-ahead section are fine.
- The registration line (name, AMFI tagline, ARN, EUIN) and the standard warning sit at the
  bottom of the emails and PDF, never at the top, inside the full disclosures
  (`config/publication.json`, `disclosures`; a draft for legal review, D-053). The WhatsApp card
  carries the registration line and the standard warning (an image is often forwarded alone);
  its message opens with the registration line and ends with the short disclaimer, the standard
  warning and the link to kubeerra.com/disclaimer (D-054).
- Never a direction call (D-048): the technical snapshot states levels, ranges and averages only;
  the outlook and the gold and silver commentary attribute every expectation to a named source
  (D-049, D-050). Never a scheme recommendation: the "Talk to us" box and the category explainer
  replace it (D-052).
- Links (D-039): readers' links go only to kubeerra.com blog posts and service or disclosure
  pages (`config/publication.json`, `kubeerra_links`), which may be reused, for example the
  Learn "Read more" and the mutual fund section's `link` (a blog post or the scheme documents
  page, never the services page next to a list of schemes or new fund offers, D-058). Outside sources are named, never
  linked; the templates do this, so keep every `source` object with its URL in the issue file.
- Mutual fund corner (D-042): AMFI industry data; category trends (`highlights`); the schemes
  with the largest net inflows in the latest month (`inflow_leaders`, as published by a
  reputable outlet); the most traded ETFs on NSE by turnover (`etfs`); fund house news
  (`fund_news`); open NFOs (`nfos`), named only when the fund house's document gives the
  riskometer, with the others counted but not named (keep `nfo_summary` as the fallback when
  none has one); rule changes; the category explainer (`category_explainer`, next in
  `learn/categories.json`; record its `used_on` date). The corner's headline starts with the
  latest month's facts ("In September, ..."), never with data that is not yet out. Every named
  scheme carries its category and
  riskometer level from the fund house's own document; never returns or performance, and never
  the words best, top, popular or trending about a scheme. Leave out any part the gatherer
  could not source.
- Use `day_ahead_title` when the calendar runs past the edition day.

## Steps

1. **Gather in parallel.** Launch `markets-gatherer`, `flows-global-gatherer`,
   `news-ipo-gatherer` and `funds-gatherer` together, each given the edition and session dates.
   Each returns JSON with a source URL for every figure, or null with a reason.
2. **Update the index history (D-048).** Write the NSE file rows the markets gatherer returned
   (`nse_index_file.rows`, header included) to `out/<date>/nse-rows.csv` (create the folder) and run
   `python3 render/technicals.py add out/<date>/nse-rows.csv --url <the file's URL>`. It refuses
   rows whose points change does not match the previous close (a miscopied digit): fetch the
   file again and retry. If the file cannot be had, leave the technical snapshot out and say so.
3. **Write the issue.** Create `issues/<edition-date>.json` against `schema/issue.schema.json`,
   using the latest issue file as the pattern. Use only figures an agent returned with a URL.
   Where two sources disagree, prefer the primary source and say which in the detail line.
   Give level figures a `change_pct` so their direction shows in green or red. The snapshot
   lists NIFTY 50, BSE Sensex, Nifty Bank, NIFTY Midcap 100 and NIFTY Smallcap 100. Fill the new
   sections from the gatherers: `movers`, `outlook`, `metals`, `results`, `big_movers`,
   `corporate_actions`, `global.us`, `global.extras`, `global.events` and
   `mf.category_explainer`. Say each fact once: a result goes in `results`, not again in
   `stories`; `stories` ("More news") holds only what no other section covers. Add a new lesson
   (next L-number) with a kubeerra.com `link`. Set `meta.subject` and `meta.preheader`. Then run
   `python3 render/technicals.py compute issues/<date>.json` (writes `technicals`) and
   `python3 render/fill_sources.py issues/<date>.json` (rebuilds the sources list).
4. **Render.** `python3 render/build.py issues/<date>.json`. It writes
   `out/<date>/kubeerra-market-brief-<date>-gmail.html`, `-outlook.html`, the text edition, the
   PDF, the WhatsApp card and caption, and previews.
5. **Check.** `python3 checks/check_issue.py issues/<date>.json`. Fix every FAIL (it fails on
   any link outside kubeerra.com and on text over a dark background in the Outlook file). Read
   every review word in context and rewrite any that read as advice or alarm. Look at
   `out/<date>/preview/` (Gmail at desktop and phone width, Outlook, Outlook with colours
   stripped, PDF pages): the PDF should run seven to fourteen pages, the last one the full
   disclosures, with no half-empty page, and no figure should break across lines. The Gmail
   file must stay under 96 KB (Gmail clips at about 102 KB, which would hide the disclosures):
   shorten text before dropping a section. The check report is written to
   `deliverables/check-reports/<date>-check-report.md`.
6. **Independent review.** Give `compliance-reviewer` the rendered `out/<date>/*.txt` and the
   WhatsApp caption. Run `fact-checker` three times in parallel, one per part of the issue
   file: (a) brief, snapshot, movers, flows, sectors, metals and global (including `global.us`,
   `extras` and `events`); (b) outlook, results, big movers, corporate actions, stories and day
   ahead; (c) IPOs, mutual fund corner (including every named scheme's figure and riskometer and
   the category explainer) and learn. The technical snapshot is checked by the script against
   NSE's files and needs no fact-check. All
   start fresh and never see the drafting. Apply their corrections, then repeat steps 3 and 4.
   Write `deliverables/reviews/<date>-review.md` (findings and resolutions).
7. **Learning library.** Append the day's lesson to `learn/library.json` (id, date, title,
   issue, topics).
8. **Publish to GitHub.** `python3 render/publish.py issues/<date>.json` copies the deliverables
   into `deliverables/pdf`, `gmail`, `outlook`, `whatsapp` and `text`, and deletes deliverable
   files older than the 14 most recent issues (D-041). Check reports, review logs and issue
   files are never deleted.
9. **Hand off.** Send Shriansh the PDF and the WhatsApp card for viewing
   (`display: "render"`), the Gmail preview images `out/<date>/preview/gmail-desktop-part-*.png`
   (the app's preview cannot load the hosted logo, so view the email as images; one tall image
   would be shrunk to fit the chat), and as attachments
   (`display: "attach"`) the Gmail and Outlook HTML files, the WhatsApp message, the check report
   (suggested subject and the figures to confirm) and the review log, with a three-line summary.
   Shriansh approves and sends; see `docs/SENDING_GUIDE.md`.
10. **Gmail draft (D-043).** After the hand-off:
   - Run `python3 render/gmail_draft.py prepare issues/<date>.json`.
   - Read `out/<date>/gmail-draft/body.html`, `logo.b64` and `subject.txt`, and call the Gmail
     `create_draft` tool with: `subject` from subject.txt; `htmlBody` exactly the contents of
     body.html; no `to`, `cc`, `bcc` or plain `body`; and `attachments` holding one item:
     `content` the lines of logo.b64 joined with no breaks, `filename` "kubeerra-logo.png", `mimeType`
     "image/png", `inline` true. (body.html already points the logo at `cid:att0`.)
   - Call `get_draft` with the new draft's id and `messageFormat` RAW. The result is large, so
     the tool saves it to a file and gives you the path; run
     `python3 render/gmail_draft.py verify-raw issues/<date>.json <that path>`. It checks the
     inline logo byte for byte against logo.b64 (on 4 Nov two miscopied characters left a broken
     image in the sent email) and every number against body.html.
   - LOGO CORRUPT: delete the draft and create it again, copying logo.b64 with care; at most
     three attempts. After a third failure, create it with `htmlBody` the contents of
     `body-nologo.html` (a lettered K tile drawn in HTML, no image) and no attachments, and
     verify that draft the same way.
   - If it prints DRAFT OK, send Shriansh the draft's view link in one line, saying whether it
     carries the logo or the lettered tile. If the numbers do not match or any step fails, delete
     the draft with `delete_draft` and tell Shriansh to use the Gmail HTML file instead. Never
     send the draft.
11. **Record.** Commit `issues/<date>.json`, `data/index-history.csv`, `learn/categories.json`,
    `deliverables/` (additions and deletions: `git add -A deliverables`) and the library update
    to `main` with the author
    `Shriansh Jena <89731022+shrianshjena@users.noreply.github.com>` (Vercel blocks deployments
    from authors it cannot match), and push. If the process changed, update
    `docs/PROJECT_RECORD.md` in the same commit.

## Failure rules

- A figure that cannot be sourced is left out, never estimated.
- If NSE provisional FII/DII data is not out, say so in the tile detail; do not use a guess.
- If any FAIL remains, stop and report it rather than delivering the issue.
