#!/usr/bin/env python3
"""Factual technical snapshot from NSE's official daily index files (D-048).

The history lives in data/index-history.csv: one row per index per session, copied from NSE's
daily index file (ind_close_all_DDMMYYYY.csv), with the file's URL. Every row is checked against
the previous session: the file's "Points Change" must equal the difference between the two
closes, which catches a mistyped digit.

    python3 render/technicals.py import-backfill <folder>      # one-time merge of part-*.csv files
    python3 render/technicals.py add <rows.csv> --url <file URL> # the session's rows, as fetched
    python3 render/technicals.py add <rows.csv> --url <report URL> --outlet
                                 # fallback when NSE's file cannot be had (D-059): rows from a
                                 # reputable market-close report, same columns, blanks allowed
                                 # for open, high, low and ratios; close, points change and
                                 # percent change are required and checked like NSE's rows
    python3 render/technicals.py check                         # validate the whole history
    python3 render/technicals.py compute issues/<date>.json    # write issue["technicals"]
    python3 render/technicals.py week issues/<date>.json --since YYYY-MM-DD
                                 # the week table's NSE index rows (closes against --since)

The snapshot states levels only: the day's range, the close against its 20, 50 and 200-day
simple averages, and India VIX. It never labels a trend (no bullish or bearish wording).
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "index-history.csv"
FIELDS = ["date", "index", "open", "high", "low", "close", "points_change", "change_pct",
          "pe", "pb", "div_yield", "source_url"]
CANON = {"NIFTY 50": "NIFTY 50", "NIFTY BANK": "NIFTY BANK", "NIFTY MIDCAP 100": "NIFTY MIDCAP 100",
         "NIFTY SMALLCAP 100": "NIFTY SMALLCAP 100", "INDIA VIX": "INDIA VIX"}
DISPLAY = {"NIFTY 50": "NIFTY 50", "NIFTY BANK": "Nifty Bank", "NIFTY MIDCAP 100": "NIFTY Midcap 100",
           "NIFTY SMALLCAP 100": "NIFTY Smallcap 100", "INDIA VIX": "India VIX"}
SNAPSHOT_INDICES = ["NIFTY 50", "NIFTY BANK"]
NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{d}.csv"


def num(text):
    text = (text or "").strip().replace(",", "")
    if text in ("", "-", "NA", "None", "null"):
        return None
    return float(text)


def parse_row(cells, file_date=None, url=None):
    """One NSE file row (Index Name, Index Date, Open, High, Low, Close, Points Change,
    Change(%), Volume, Turnover, P/E, P/B, Div Yield) -> a history record, or None."""
    cells = [c.strip() for c in cells]
    name = CANON.get(cells[0].upper())
    if not name:
        return None
    day = dt.datetime.strptime(cells[1], "%d-%m-%Y").date()
    if file_date and day != file_date:
        raise ValueError(f"{cells[0]}: index date {day} differs from the file date {file_date}")
    o, h, l, c, pts, pct = (num(x) for x in cells[2:8])
    tail = cells[8:] + [""] * 5
    pe, pb, dy = (num(x) for x in tail[2:5]) if len(cells) >= 13 else (None, None, None)
    return {"date": day.isoformat(), "index": name, "open": o, "high": h, "low": l, "close": c,
            "points_change": pts, "change_pct": pct, "pe": pe, "pb": pb, "div_yield": dy,
            "source_url": url or NSE_URL.format(d=day.strftime("%d%m%Y"))}


def load():
    if not HISTORY.exists():
        return []
    with HISTORY.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in FIELDS[2:11]:
            r[k] = num(r[k])
    return rows


def save(rows):
    rows = sorted(rows, key=lambda r: (r["date"], r["index"]))
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r[k] is None else (fmt_num(r[k]) if isinstance(r[k], float) else r[k])) for k in FIELDS})


def fmt_num(v):
    """Up to four decimals, no trailing zeros: 26140.75, 13.6325, 1.3 (never rounds a 2-decimal level)."""
    return ("%.4f" % v).rstrip("0").rstrip(".")


def series(rows, name):
    return sorted((r for r in rows if r["index"] == name), key=lambda r: r["date"])


def problems(rows):
    """Every inconsistency in the history: ranges, and points change against the previous close."""
    out = []
    for name in CANON.values():
        prev = None
        for r in series(rows, name):
            o, h, l, c = r["open"], r["high"], r["low"], r["close"]
            if c is None:
                out.append(f"{r['date']} {name}: missing close")
            elif (h is None) != (l is None):
                out.append(f"{r['date']} {name}: high and low must both be given or both left blank")
            elif h is not None and not (l - 0.011 <= min(x for x in (o, c) if x is not None)
                                        and max(x for x in (o, c) if x is not None) <= h + 0.011):
                out.append(f"{r['date']} {name}: open {o} or close {c} outside low {l} to high {h}")
            if prev and r["points_change"] is not None and c is not None:
                diff = round(c - prev["close"], 2)
                if abs(diff - r["points_change"]) > 0.051:
                    out.append(f"{r['date']} {name}: points change {r['points_change']} but closes moved {diff} "
                               f"(from {prev['close']} on {prev['date']})")
                elif (name != "INDIA VIX" and r["change_pct"] is not None   # NSE rounds VIX closes, not its % change
                      and abs(diff / prev["close"] * 100 - r["change_pct"]) > 0.015):
                    out.append(f"{r['date']} {name}: change {r['change_pct']}% but closes imply "
                               f"{diff / prev['close'] * 100:.3f}%")
            prev = r
    return out


def cmd_import_backfill(folder):
    rows, seen, skipped = [], set(), []
    for path in sorted(Path(folder).glob("part-*.csv")):
        for line in csv.reader(path.open(encoding="utf-8")):
            if not line or line[0].startswith("file_date") or len(line) < 2:
                continue
            if line[1].strip() in ("NO_FILE", "FETCH_FAILED"):
                skipped.append(line[0])
                continue
            file_date = dt.datetime.strptime(line[0].strip(), "%d%m%Y").date()
            rec = parse_row(line[1:], file_date)
            if rec and (rec["date"], rec["index"]) not in seen:
                seen.add((rec["date"], rec["index"]))
                rows.append(rec)
    found = problems(rows)
    sessions = sorted({r["date"] for r in rows})
    print(f"{len(rows)} rows, {len(sessions)} sessions ({sessions[0]} to {sessions[-1]}); "
          f"{len(skipped)} dates without a file: {', '.join(sorted(skipped))}")
    for p in found:
        print("PROBLEM", p)
    if found:
        print("Not saved: fix or re-fetch the dates above first.")
        sys.exit(1)
    save(rows)
    print(f"saved {HISTORY.relative_to(ROOT)}")


def is_nse(url):
    return any(h in (url or "") for h in ("nseindia.com", "niftyindices.com"))


def cmd_add(path, url, outlet=False):
    """Add one session's rows. NSE's file is the source of record; with --outlet the rows come from
    a reputable market-close report (D-059). Each row is checked against the index's previous close;
    a row that does not check out is refused and the others are kept."""
    if outlet == is_nse(url):
        sys.exit("--outlet is for a market-close report's URL; NSE's own file needs no flag"
                 if outlet else "this URL is not NSE's file: add --outlet for a market-close report")
    rows = load()
    new = []
    for line in csv.reader(Path(path).open(encoding="utf-8")):
        if not line or line[0].lower().startswith("index name"):
            continue
        rec = parse_row(line, url=url)
        if rec:
            if outlet and None in (rec["close"], rec["points_change"], rec["change_pct"]) and rec["index"] != "INDIA VIX":
                print(f"REFUSED {rec['date']} {DISPLAY[rec['index']]}: a report row needs close, points change and percent change")
                continue
            new.append(rec)
    if not new:
        sys.exit("no usable NIFTY 50, NIFTY BANK, NIFTY MIDCAP 100, NIFTY SMALLCAP 100 or INDIA VIX rows found")
    dates = {r["date"] for r in new}
    if len(dates) != 1:
        sys.exit(f"rows carry more than one date: {sorted(dates)}")
    day = dates.pop()
    kept = []
    for rec in new:
        trial = [r for r in rows if (r["date"], r["index"]) != (day, rec["index"])] + [rec]
        found = [p for p in problems(trial) if p.startswith(f"{day} {rec['index']}:")]
        if found:
            for p_ in found:
                print("REFUSED", p_)
            continue
        rows = trial
        kept.append(rec)
    if not kept:
        sys.exit("Not saved: no row matched its previous close; re-read the source.")
    save(rows)
    print(f"added {len(kept)} rows for {day}" + (" (market-close report)" if outlet else "") + ": "
          + ", ".join(f"{DISPLAY[r['index']]} {fmt_num(r['close'])}" for r in kept))
    if len(kept) < len(new):
        sys.exit(1)


def sma(values, n):
    return round(sum(values[-n:]) / n, 2) if len(values) >= n else None


def cmd_compute(issue_path):
    issue = json.loads(Path(issue_path).read_text(encoding="utf-8"))
    rows = load()
    found = problems(rows)
    if found:
        for p in found:
            print("PROBLEM", p)
        sys.exit("history has inconsistencies; run `check` and fix them first")
    # the session the issue covers, from the snapshot's as-of text ("close, 3 Nov 2026")
    m = re.search(r"(\d{1,2}) ([A-Z][a-z]{2})[a-z]* (\d{4})", issue["snapshot"]["as_of"])
    if not m:
        sys.exit(f"cannot read the session date from snapshot.as_of: {issue['snapshot']['as_of']!r}")
    session = dt.datetime.strptime(" ".join(m.groups()), "%d %b %Y").date().isoformat()
    if not any(r["date"] == session for r in rows):
        sys.exit(f"the history has no rows for the {session} session: add NSE's file for that day "
                 "(render/technicals.py add), or leave the technical snapshot out")
    day = dt.date.fromisoformat(session)
    as_of = f"close, {day.day} {day:%b %Y}"
    items = []
    for name in SNAPSHOT_INDICES:
        s = [r for r in series(rows, name) if r["date"] <= session]
        if not s or s[-1]["date"] != session:
            continue
        last, closes = s[-1], [r["close"] for r in s]
        prev = s[-2]["close"] if len(s) > 1 else None
        items.append({
            "index": DISPLAY[name], "open": last["open"], "high": last["high"], "low": last["low"],
            "close": last["close"], "prev_close": prev, "change_pct": last["change_pct"],
            "sma20": sma(closes, 20), "sma50": sma(closes, 50), "sma200": sma(closes, 200),
            "sessions": len(closes), "pe": last["pe"],
            "source": {"name": "NSE daily index file" if is_nse(last["source_url"]) else "Market-close report",
                       "url": last["source_url"]}})
    latest = [r for r in rows if r["date"] == session and r["index"] in SNAPSHOT_INDICES]
    from_outlet = sorted({r["source_url"] for r in latest if not is_nse(r["source_url"])})
    vix = [r for r in series(rows, "INDIA VIX") if r["date"] == session]
    nifty = [r for r in series(rows, "NIFTY 50") if r["date"] <= session][-22:]
    issue["technicals"] = {
        "headline": (issue.get("technicals") or {}).get("headline") or headline(items),
        "as_of": as_of,
        "items": items,
        "vix": ({"close": vix[0]["close"], "change_pct": vix[0]["change_pct"],
                 "source": {"name": "NSE daily index file", "url": vix[0]["source_url"]}} if vix else None),
        "trend": ({"index": "NIFTY 50", "points": [{"date": r["date"], "close": r["close"]} for r in nifty],
                   "source": {"name": "NSE daily index files", "url": nifty[-1]["source_url"]}}
                  if len(nifty) >= 5 else None),
        "note": (("Levels from NSE's daily index files" if not from_outlet else
                  f"Levels from NSE's daily index files; the {day.day} {day:%b} levels are from market-close "
                  "reports until NSE publishes its file") +
                 ". Averages are simple averages of the last 20, 50 and 200 closes, calculated by Kubeerra. "
                 "These describe where prices have been; they are not a forecast, a signal or a recommendation."),
    }
    Path(issue_path).write_text(json.dumps(issue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for it in items:
        print(f"{it['index']}: close {fmt_num(it['close'])}, range {fmt_num(it['low'])} to {fmt_num(it['high'])}, "
              f"20/50/200-session averages {it['sma20']}, {it['sma50']}, {it['sma200']} ({it['sessions']} sessions)")
    print(f"technicals written for the {session} session")


def cmd_week(issue_path, since):
    """Week table rows for the NSE indices: the session's close against the close on --since."""
    issue = json.loads(Path(issue_path).read_text(encoding="utf-8"))
    rows = load()
    m = re.search(r"(\d{1,2}) ([A-Z][a-z]{2})[a-z]* (\d{4})", issue["snapshot"]["as_of"])
    if not m:
        sys.exit(f"cannot read the session date from snapshot.as_of: {issue['snapshot']['as_of']!r}")
    session = dt.datetime.strptime(" ".join(m.groups()), "%d %b %Y").date().isoformat()
    week = issue.setdefault("week", {})
    items = [it for it in week.get("items", []) if it.get("name") not in DISPLAY.values()]
    made = []
    for name in ("NIFTY 50", "NIFTY BANK", "NIFTY MIDCAP 100", "NIFTY SMALLCAP 100"):
        start = next((r for r in rows if r["index"] == name and r["date"] == since), None)
        end = next((r for r in rows if r["index"] == name and r["date"] == session), None)
        if not (start and end):
            print(f"skipped {DISPLAY[name]}: no close for {since if not start else session} in the history")
            continue
        made.append({"name": DISPLAY[name], "start": start["close"], "end": end["close"],
                     "change_pct": round((end["close"] - start["close"]) / start["close"] * 100, 2),
                     "format": "level",
                     "source": {"name": "NSE daily index file" if is_nse(end["source_url"]) else "Market-close report",
                                "url": end["source_url"]},
                     "also": {"name": "NSE daily index file" if is_nse(start["source_url"]) else "Market-close report",
                              "url": start["source_url"]}})
    week["items"] = made + items
    d0, d1 = dt.date.fromisoformat(since), dt.date.fromisoformat(session)
    week.setdefault("from", f"{d0:%a} {d0.day} {d0:%b}")
    week.setdefault("to", f"{d1:%a} {d1.day} {d1:%b}")
    Path(issue_path).write_text(json.dumps(issue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for it in made:
        print(f"{it['name']}: {fmt_num(it['start'])} to {fmt_num(it['end'])}, {it['change_pct']:+.2f}%")


def headline(items):
    """A factual default headline: where the NIFTY 50 closed against its averages (the same "N-day"
    wording as the table)."""
    n = next((i for i in items if i["index"] == "NIFTY 50"), None)
    if not n:
        return "Index levels and averages from NSE's daily files"
    keys = (("sma20", 20), ("sma50", 50), ("sma200", 200))
    above = [d for k, d in keys if n[k] is not None and n["close"] > n[k]]
    below = [d for k, d in keys if n[k] is not None and n["close"] < n[k]]

    def name(days):
        parts = [f"{d}-day" for d in days]
        joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        return f"{joined} average" + ("s" if len(parts) > 1 else "")
    if above and below:
        return f"The NIFTY 50 closed above its {name(above)} and below its {name(below)}"
    if above:
        return f"The NIFTY 50 closed above its {name(above)}"
    if below:
        return f"The NIFTY 50 closed below its {name(below)}"
    return "The NIFTY 50's close against its recent averages"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("import-backfill"); a.add_argument("folder")
    b = sub.add_parser("add"); b.add_argument("rows"); b.add_argument("--url", required=True)
    b.add_argument("--outlet", action="store_true", help="rows from a market-close report, not NSE's file")
    w = sub.add_parser("week"); w.add_argument("issue"); w.add_argument("--since", required=True)
    sub.add_parser("check")
    c = sub.add_parser("compute"); c.add_argument("issue")
    args = ap.parse_args()
    if args.cmd == "import-backfill":
        cmd_import_backfill(args.folder)
    elif args.cmd == "add":
        cmd_add(args.rows, args.url, args.outlet)
    elif args.cmd == "week":
        cmd_week(args.issue, args.since)
    elif args.cmd == "check":
        found = problems(load())
        for p in found:
            print("PROBLEM", p)
        print("history OK" if not found else f"{len(found)} problems")
        sys.exit(1 if found else 0)
    else:
        cmd_compute(args.issue)


if __name__ == "__main__":
    main()
