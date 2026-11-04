#!/usr/bin/env python3
"""Factual technical snapshot from NSE's official daily index files (D-048).

The history lives in data/index-history.csv: one row per index per session, copied from NSE's
daily index file (ind_close_all_DDMMYYYY.csv), with the file's URL. Every row is checked against
the previous session: the file's "Points Change" must equal the difference between the two
closes, which catches a mistyped digit.

    python3 render/technicals.py import-backfill <folder>      # one-time merge of part-*.csv files
    python3 render/technicals.py add <rows.csv> --url <file URL> # the session's rows, as fetched
    python3 render/technicals.py check                         # validate the whole history
    python3 render/technicals.py compute issues/<date>.json    # write issue["technicals"]

The snapshot states levels only: the day's range, the close against its 20, 50 and 200-session
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
            if None in (h, l, c):
                out.append(f"{r['date']} {name}: missing high, low or close")
            elif o is not None and not (l - 0.011 <= min(o, c) and max(o, c) <= h + 0.011):
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


def cmd_add(path, url):
    rows = load()
    new = []
    for line in csv.reader(Path(path).open(encoding="utf-8")):
        if not line or line[0].lower().startswith("index name"):
            continue
        rec = parse_row(line, url=url)
        if rec:
            new.append(rec)
    if not new:
        sys.exit("no NIFTY 50, NIFTY BANK, NIFTY MIDCAP 100, NIFTY SMALLCAP 100 or INDIA VIX rows found")
    dates = {r["date"] for r in new}
    if len(dates) != 1:
        sys.exit(f"rows carry more than one date: {sorted(dates)}")
    day = dates.pop()
    rows = [r for r in rows if r["date"] != day] + new
    found = [p for p in problems(rows) if p.startswith(day)]
    for p in found:
        print("PROBLEM", p)
    if found:
        sys.exit("Not saved: re-read the file; a figure does not match the previous close.")
    save(rows)
    print(f"added {len(new)} rows for {day}: " + ", ".join(f"{DISPLAY[r['index']]} {fmt_num(r['close'])}" for r in new))


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
            "source": {"name": "NSE daily index file", "url": last["source_url"]}})
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
        "note": ("Levels from NSE's daily index files. Averages are simple averages of the last 20, 50 and "
                 "200 closes, calculated by Kubeerra. These describe where prices have been; they are not "
                 "a forecast, a signal or a recommendation."),
    }
    Path(issue_path).write_text(json.dumps(issue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for it in items:
        print(f"{it['index']}: close {fmt_num(it['close'])}, range {fmt_num(it['low'])} to {fmt_num(it['high'])}, "
              f"20/50/200-session averages {it['sma20']}, {it['sma50']}, {it['sma200']} ({it['sessions']} sessions)")
    print(f"technicals written for the {session} session")


def headline(items):
    """A factual default headline: where the NIFTY 50 closed against its averages."""
    n = next((i for i in items if i["index"] == "NIFTY 50"), None)
    if not n:
        return "Index levels and averages from NSE's daily files"
    above = [k for k, label in (("sma20", "20"), ("sma50", "50"), ("sma200", "200")) if n[k] is not None and n["close"] > n[k]]
    below = [k for k, label in (("sma20", "20"), ("sma50", "50"), ("sma200", "200")) if n[k] is not None and n["close"] < n[k]]
    label = {"sma20": "20", "sma50": "50", "sma200": "200"}
    def join(keys):
        parts = [label[k] for k in keys]
        return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    if above and not below:
        return f"The NIFTY 50 closed above its {join(above)}-session averages"
    if below and not above:
        return f"The NIFTY 50 closed below its {join(below)}-session averages"
    if above and below:
        return f"The NIFTY 50 closed above its {join(above)}-session and below its {join(below)}-session averages"
    return "The NIFTY 50's close against its recent averages"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("import-backfill"); a.add_argument("folder")
    b = sub.add_parser("add"); b.add_argument("rows"); b.add_argument("--url", required=True)
    sub.add_parser("check")
    c = sub.add_parser("compute"); c.add_argument("issue")
    args = ap.parse_args()
    if args.cmd == "import-backfill":
        cmd_import_backfill(args.folder)
    elif args.cmd == "add":
        cmd_add(args.rows, args.url)
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
