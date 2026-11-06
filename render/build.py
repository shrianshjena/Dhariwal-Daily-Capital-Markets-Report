#!/usr/bin/env python3
"""Render one Kubeerra Market Brief issue into every format.

    python3 render/build.py issues/2026-10-29.json [--logo-url URL] [--no-previews]

Outputs go to out/<date>/:
    kubeerra-market-brief-<date>.html   email HTML (inline styles; Outlook and Gmail safe)
    kubeerra-market-brief-<date>.txt    plain-text alternative
    kubeerra-market-brief-<date>.pdf    A4 PDF
    preview/                            PNG previews of the email (704 and 390 px, the Gmail one also in
                                        parts for the hand-off) and PDF pages
    manifest.json                       file sizes and checksums
"""
import argparse
import base64
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import jsonschema
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(issue):
    schema = load_json(ROOT / "schema" / "issue.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(issue), key=lambda e: list(e.path))
    for err in errors:
        print("SCHEMA", "/".join(map(str, err.path)) or "(root)", err.message, file=sys.stderr)
    if errors:
        sys.exit(2)


def sector_view(issue):
    items = sorted(issue["sectors"]["items"], key=lambda s: s["change_pct"], reverse=True)
    # up to four each side, never the same index in both lists (with seven sectors: four and three)
    n_top = min(4, (len(items) + 1) // 2)
    n_bottom = min(4, len(items) - n_top)
    top = items[:n_top]
    bottom = list(reversed(items[len(items) - n_bottom:]))
    biggest = max(abs(s["change_pct"]) for s in top + bottom) or 1
    def bar(s):
        return dict(s, bar=max(2, round(abs(s["change_pct"]) / biggest * 100)))
    return {"top": [bar(s) for s in top], "bottom": [bar(s) for s in bottom], "max": biggest}


# The issue's clusters and sections (D-046). Sections without data drop out, and the numbering
# closes up, so "1.2" always means the second section that is actually in the issue.
CLUSTERS = [
    ("week", "The week", "Each market's change from the previous week's last close", [
        ("week", "Week in review", lambda i: bool((i.get("week") or {}).get("items")))]),
    ("markets", "Markets", "Indian indices, the day's biggest movers, levels, sectors, flows and the rupee", [
        ("snapshot", "Market snapshot", lambda i: True),
        ("movers", "Top gainers and losers", lambda i: bool(i.get("movers"))),
        ("technicals", "Technical snapshot", lambda i: bool(i.get("technicals"))),
        ("sectors", "Sector scoreboard", lambda i: True),
        ("flows", "Flows, rupee and bonds", lambda i: True)]),
    ("outlook", "Market drivers", "Crude and other local factors, how global markets reach India, and the events and data ahead", [
        ("drivers", "What is driving markets", lambda i: bool((i.get("outlook") or {}).get("drivers"))),
        ("cues", "How global markets reach India", lambda i: bool((i.get("outlook") or {}).get("global_cues"))),
        ("events", "Events and data ahead", lambda i: bool((i.get("outlook") or {}).get("events")))]),
    ("global", "Global markets", "The US session, world indices, rates and global events", [
        ("us", "The US session", lambda i: bool(i["global"].get("us"))),
        ("world", "World markets", lambda i: True),
        ("gevents", "Global events", lambda i: bool(i["global"].get("events")))]),
    ("metals", "Gold and silver", "IBJA rates in rupees, international prices and what moved them", [
        ("metals", "Gold and silver prices", lambda i: bool(i.get("metals")))]),
    ("companies", "Companies", "Results, big single-day moves, corporate actions, IPOs and other news", [
        ("results", "Results", lambda i: bool(i.get("results"))),
        ("bigmovers", "Big movers", lambda i: bool(i.get("big_movers"))),
        ("actions", "Corporate actions", lambda i: bool((i.get("corporate_actions") or {}).get("items"))),
        ("ipos", "IPO desk", lambda i: True),
        ("stories", "More news", lambda i: bool(i.get("stories")))]),
    ("funds", "Mutual funds", "Industry data, new fund offers, rule changes, a lesson and how to reach us", [
        ("mf", "Mutual fund corner", lambda i: True),
        ("talk", "Talk to us", lambda i: True),
        ("learn", "Learn", lambda i: True)]),
    ("calendar", "Calendar", "Results, data releases, listings and holidays in the days ahead", [
        ("dayahead", "Day ahead", lambda i: True)]),
]


def structure(issue):
    clusters, sections = [], {}
    for cid, title, desc, secs in CLUSTERS:
        present = [(sid, stitle) for sid, stitle, test in secs if test(issue)]
        if not present:
            continue
        n = len(clusters) + 1
        cl = {"id": cid, "num": n, "title": title, "desc": desc, "sections": []}
        for k, (sid, stitle) in enumerate(present, start=1):
            sec = {"id": sid, "num": f"{n}.{k}", "title": stitle, "cluster": cid}
            cl["sections"].append(sec)
            sections[sid] = sec
        clusters.append(cl)
    return clusters, sections


def find_index(issue, *names):
    for r in issue["snapshot"]["indices"]:
        if r["name"].lower() in [n.lower() for n in names]:
            return r
    return None


def glance(issue):
    """The six key numbers for the top of the email and PDF and for the WhatsApp card (D-047)."""
    tiles = []
    for label, names in (("NIFTY 50", ("NIFTY 50",)), ("Sensex", ("BSE Sensex", "Sensex")),
                         ("NIFTY Midcap 100", ("NIFTY Midcap 100", "Nifty Midcap 100")),
                         ("NIFTY Smallcap 100", ("NIFTY Smallcap 100", "Nifty Smallcap 100"))):
        r = find_index(issue, *names)
        if r:
            tiles.append({"label": label, "value": fmt.level(r["close"]), "change_pct": r["change_pct"]})
    m = metals_view(issue)
    if m:
        # IBJA rates older than the India session carry their own date (compliance review, 5 Nov).
        tag = ""
        if m["date"] and m["date"] not in (issue["meta"].get("india_as_of") or ""):
            tag = " · IBJA " + " ".join(m["date"].split()[:2])
        tiles.append({"label": "Gold 24K · ₹/10 g" + tag, "value": "₹" + fmt.group_indian(m["gold"], 0), "change_pct": m["gold_pct"]})
        tiles.append({"label": "Silver · ₹/kg" + tag, "value": "₹" + fmt.group_indian(m["silver"], 0), "change_pct": m["silver_pct"]})
    return tiles


def metals_view(issue):
    m = issue.get("metals")
    if not m:
        return None
    ib = m["ibja"]
    def pct(now, prev):
        return round((now - prev) / prev * 100, 2) if prev else None
    return {"gold": ib["gold_999_10g"], "gold_prev": ib.get("gold_prev"), "gold_pct": pct(ib["gold_999_10g"], ib.get("gold_prev")),
            "silver": ib["silver_999_kg"], "silver_prev": ib.get("silver_prev"),
            "silver_pct": pct(ib["silver_999_kg"], ib.get("silver_prev")),
            "date": ib["date"], "session": ib["session"], "prev_date": ib.get("prev_date"), "source": ib["source"]}


def week_rows(issue, tokens):
    """The week table's display strings: start and end values and the change (percent, or basis
    points for yields), coloured by direction (yields in grey: a rise is not good or bad)."""
    colors = tokens["color"]
    rows = []
    for it in (issue.get("week") or {}).get("items", []):
        if it.get("change_bp") is not None:
            chg, v, neutral = fmt.bp(it["change_bp"]), it["change_bp"], True
        elif it.get("change_pct") is not None:
            chg, v, neutral = fmt.arrow(it["change_pct"]) + " " + fmt.pct(it["change_pct"]), it["change_pct"], False
        else:
            chg, v, neutral = "", 0, True
        d = fmt.direction(v)
        color = colors["text"]["secondary"] if (neutral or d == "flat") else colors["status"]["up" if d == "up" else "down"]
        rows.append({"name": it["name"], "start_s": fmt.figure(it["start"], it["format"]),
                     "end_s": fmt.figure(it["end"], it["format"]), "chg_s": chg, "color": color,
                     "pct": it.get("change_pct"), "note": it.get("note")})
    return rows


def world_groups(issue):
    """World markets in region groups, in the issue's order, then rates and currency. A group whose
    rows share one as-of date shows it once, in its heading."""
    groups = []
    for g in issue["global"]["items"]:
        if not groups or groups[-1]["region"] != g["region"]:
            groups.append({"region": g["region"], "rows": []})
        groups[-1]["rows"].append({"kind": "index", "x": g, "as_of": g.get("as_of")})
    extras = issue["global"].get("extras") or []
    if extras:
        groups.append({"region": "Rates and currency", "rows": [{"kind": "extra", "x": x, "as_of": x.get("as_of") or x.get("detail")}
                                                               for x in extras]})
    for gr in groups:
        dates = {r["as_of"] for r in gr["rows"]}
        gr["as_of"] = dates.pop() if len(dates) == 1 else None
    return groups


def range_bar(it):
    """The day's range as three segments (percent widths): low to the open/close, the open-to-close
    move, and the rest up to the high. Email tables and the SVG charts share it."""
    lo, hi, o, c = it.get("low"), it.get("high"), it.get("open"), it.get("close")
    if None in (lo, hi, o, c) or hi <= lo:
        return None
    span = hi - lo
    a = round((min(o, c) - lo) / span * 100)
    b = max(2, round(abs(c - o) / span * 100))
    a = min(a, 100 - b)
    return {"a": a, "b": b, "c": 100 - a - b, "up": c >= o, "open_pct": round((o - lo) / span * 100, 1),
            "close_pct": round((c - lo) / span * 100, 1)}


def trend(points, height=56, width=560):
    """Bars for the email (pixel heights) and a polyline for the PDF and card (SVG coordinates)."""
    if not points:
        return None
    vals = [p["close"] for p in points]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    bars = [{"h": 6 + round((v - lo) / span * (height - 6)), "close": v, "date": p["date"]} for p, v in zip(points, vals)]
    n = len(vals)
    xs = [round(i * width / (n - 1), 1) for i in range(n)] if n > 1 else [0]
    ys = [round((hi - v) / span * 100, 1) for v in vals]   # 0 (top) to 100 (bottom) of the plot area
    first, last = points[0]["date"], points[-1]["date"]
    def short(d):
        dd = datetime.date.fromisoformat(d)
        return f"{dd.day} {dd:%b}"
    return {"bars": bars, "lo": lo, "hi": hi, "first": short(first), "last": short(last),
            "start": vals[0], "end": vals[-1], "change_pct": round((vals[-1] - vals[0]) / vals[0] * 100, 2),
            "xs": xs, "ys": ys, "n": n,
            "points": " ".join(f"{x},{y}" for x, y in zip(xs, ys))}


WEIGHTS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "medium": 500,
           "semibold": 600, "bold": 700, "extrabold": 800, "black": 900}


def font_faces():
    """@font-face entries for the PDF. General Sans is used automatically once its files are in assets/fonts."""
    faces = []
    for path in sorted((ROOT / "assets" / "fonts").iterdir()):
        if path.suffix.lower() not in (".ttf", ".otf"):
            continue
        family, _, weight = path.stem.partition("-")
        weight = weight.lower()
        if "italic" in weight or "variable" in weight:
            continue
        name = {"GeneralSans": "General Sans", "HankenGrotesk": "Hanken Grotesk",
                "JetBrainsMono": "JetBrains Mono"}.get(family)
        if not name:
            continue
        value = int(weight) if weight.isdigit() else WEIGHTS.get(weight, 400)
        faces.append({"family": name, "weight": value, "path": f"assets/fonts/{path.name}"})
    return faces


MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
GLUE = [
    (re.compile(r"(?<=\d) (?=(?:lakh|crore|cr|bp|paise|times|AM|PM)\b)"), "\u00a0"),  # 1,450 crore; 8:11 AM
    (re.compile(r"(?<=\blakh) (?=(?:crore|cr)\b)"), "\u00a0"),                         # lakh crore
    (re.compile(r"(?<=\d) (?=" + MONTHS + r"\b)"), "\u00a0"),                            # 28 Oct
    (re.compile(r"(?<=\d) (?=\d)"), "\u00a0"),                                             # +91 73042 11122
    (re.compile(r"\b(NIFTY|Nifty|Sensex|S&P|FTSE|Midcap|Smallcap) (?=\d)"), "\\1\u00a0"),     # NIFTY 50
]
SIGNED_MONEY = re.compile(r"([+\u2212][\u20b9$][\d,]+(?:\.\d+)?)")


def glue(text):
    """Typographic glue for HTML output: keep numbers with their units, days with months,
    index names with their numbers, and a sign with its currency symbol (browsers and
    mail apps may otherwise break a line between the minus sign and the rupee sign)."""
    s = str(text)
    for pattern, repl in GLUE:
        s = pattern.sub(repl, s)
    s = str(escape(s)).replace("\u00a0", "&nbsp;")
    return Markup(SIGNED_MONEY.sub(r'<span style="white-space:nowrap;">\1</span>', s))


def nobreak(text):
    """Join all words of a short label, such as a footer link, so it never wraps."""
    return Markup(str(escape(str(text))).replace(" ", "&nbsp;"))


def is_flow(f):
    """A figure that is itself a movement (a net flow), coloured by its sign."""
    return f.get("flow", f["format"] == "crore_signed")


def movement(f):
    """Direction of a figure: explicit, from its change, or from the sign of a net flow; None for a plain level."""
    if f.get("direction"):
        return f["direction"]
    if f.get("change_pct") is not None:
        return fmt.direction(f["change_pct"])
    if f.get("change_bp") is not None:
        return fmt.direction(f["change_bp"])
    if is_flow(f):
        return fmt.direction(f["value"])
    return None


def chip(f):
    """The coloured change beside a level: '▲ +0.22%' or '▼ −5 bp'; empty when no change is stated."""
    if f.get("change_pct") is not None:
        return f"{fmt.arrow(f['change_pct'])} {fmt.pct(f['change_pct'])}".strip()
    if f.get("change_bp") is not None:
        return f"{fmt.arrow(f['change_bp'])} {fmt.bp(f['change_bp'])}".strip()
    return ""


def srcs(item):
    """Every page an item cites, in order: its source, then its `also` (one source or a list)."""
    out = [item["source"]] if item.get("source") else []
    extra = item.get("also")
    if isinstance(extra, dict):
        out.append(extra)
    elif isinstance(extra, list):
        out.extend(extra)
    return out


def unique_sources(items):
    """The distinct sources of a list of figures, in order (for a shared source line)."""
    seen, out = set(), []
    for item in items:
        for s in srcs(item):
            if s["url"] not in seen:
                seen.add(s["url"])
                out.append(s)
    return out


def groupby_ordered(items, key):
    """Consecutive groups by a key, in the items' own order (Jinja's groupby sorts)."""
    groups = []
    for x in items:
        k = x[key]
        if not groups or groups[-1][0] != k:
            groups.append((k, []))
        groups[-1][1].append(x)
    return groups


def build_env(tokens):
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=lambda name: bool(name) and name.endswith(".html.j2"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    colors = tokens["color"]

    def dircolor(value, neutral=False):
        if neutral:
            return colors["text"]["secondary"]
        return {"up": colors["status"]["up"], "down": colors["status"]["down"],
                "flat": colors["text"]["secondary"]}[fmt.direction(value)]

    def mvcolor(mv):
        # green up, red down, grey flat, ink for a level with no stated change
        return {"up": colors["status"]["up"], "down": colors["status"]["down"],
                "flat": colors["text"]["secondary"]}.get(mv, colors["text"]["primary"])

    def figcolor(f):
        # a net flow is coloured by its sign; a level stays in ink beside its coloured change
        return mvcolor(movement(f)) if is_flow(f) else colors["text"]["primary"]

    env.filters.update(
        level=fmt.level, points=fmt.points, pct=fmt.pct, arrow=fmt.arrow,
        figure=lambda f: fmt.figure(f["value"], f["format"]), dircolor=dircolor,
        group=fmt.group_indian,
        host=lambda url: urlparse(url).netloc.removeprefix("www."),
        t=glue, nb=nobreak, movement=movement, is_flow=is_flow, mvcolor=mvcolor, figcolor=figcolor,
        chip=chip, bp=fmt.bp, srcs=srcs, unique_sources=unique_sources,
        crore=lambda v: fmt.figure(v, "crore"),
        groupby_ordered=groupby_ordered,
        andjoin=lambda xs: (", ".join(list(xs)[:-1]) + " and " + list(xs)[-1]) if len(list(xs)) > 1 else "".join(xs),
    )
    return env


def compact(html):
    """Remove indentation-only whitespace between tags; inline spacing is never written across lines."""
    html = re.sub(r">\s*\n\s*<", "><", html)
    return re.sub(r"\n\s+", "\n", html).strip() + "\n"


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def trim_png(path, background=(243, 246, 250)):
    from PIL import Image, ImageChops
    image = Image.open(path).convert("RGB")
    diff = ImageChops.difference(image, Image.new("RGB", image.size, background))
    box = diff.getbbox()
    if box:
        image.crop((0, 0, image.width, min(image.height, box[3] + 24))).save(path, optimize=True)


def split_png(path, max_height=3800):
    """Cut a tall preview into parts the chat shows at full size (it shrinks images over 8,000 px)."""
    from PIL import Image
    for stale in path.parent.glob(f"{path.stem}-part-*.png"):
        stale.unlink()
    image = Image.open(path)
    n = -(-image.height // max_height)
    step = -(-image.height // n)
    for i in range(n):
        part = image.crop((0, i * step, image.width, min(image.height, (i + 1) * step)))
        part.save(path.parent / f"{path.stem}-part-{i + 1}-of-{n}.png", optimize=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue")
    parser.add_argument("--logo-url", default=None, help="Hosted PNG for the email masthead")
    parser.add_argument("--no-previews", action="store_true")
    args = parser.parse_args()

    tokens = load_json(ROOT / "design-tokens" / "tokens.json")
    pub = load_json(ROOT / "config" / "publication.json")
    issue = load_json(args.issue)
    validate(issue)

    date = issue["meta"]["date"]
    eid = issue["meta"].get("edition_id") or date   # a second edition on one date, e.g. 2026-11-06-close
    out = ROOT / "out" / eid
    (out / "preview").mkdir(parents=True, exist_ok=True)
    stem = f"kubeerra-market-brief-{eid}"
    env = build_env(tokens)

    logo_url = args.logo_url or pub["assets"]["logo_email_url"]
    if not logo_url:
        print("WARN no hosted logo URL: the email masthead will show alt text until one is set", file=sys.stderr)

    day = datetime.date.fromisoformat(date)
    snapshot_sources = list({s['source']['url']: s['source'] for s in issue['snapshot']['indices']}.values())
    global_sources = list({s['url']: s for s in [g['source'] for g in issue['global']['items']]
                           + issue['global'].get('note_sources', [])}.values())
    # Open NFOs are named (in every edition, D-042) only with their riskometer; others are counted, not named
    nfos = issue["mf"].get("nfos") or []
    named_nfos = [n for n in nfos if n.get("riskometer")]
    show_nfo_names = bool(named_nfos)
    unnamed = len(nfos) - len(named_nfos)
    nfo_unnamed_note = ""
    if unnamed:
        count = "one two three four five six seven eight nine".split()[unnamed - 1].capitalize() if unnamed < 10 else str(unnamed)
        nfo_unnamed_note = (f"{count} other open {'offer is' if unnamed == 1 else 'offers are'} not named because "
                            f"{'its risk level' if unnamed == 1 else 'their risk levels'} could not be confirmed "
                            "from fund house documents.")
    clusters, S = structure(issue)
    tech = issue.get("technicals") or {}
    nifty_tech = next((t for t in tech.get("items", []) if t["index"] == "NIFTY 50"), None)
    charts = {"range": range_bar(nifty_tech) if nifty_tech else None,
              "trend": trend((tech.get("trend") or {}).get("points") or [])}
    ctx = dict(issue=issue, pub=pub, tokens=tokens, sectors=sector_view(issue), snapshot_sources=snapshot_sources,
               clusters=clusters, S=S, glance=glance(issue), metals=metals_view(issue), charts=charts,
               nifty_tech=nifty_tech, world_groups=world_groups(issue), week_rows=week_rows(issue, tokens),
               edition_name=issue["meta"].get("edition_name") or issue["meta"].get("edition") or pub["edition_name"],
               global_sources=global_sources, show_nfo_names=show_nfo_names, named_nfos=named_nfos,
               nfo_unnamed_note=nfo_unnamed_note, kb=pub["kubeerra_links"],
               date_long=f"{day.day} {day:%B %Y}", date_short=f"{day.day} {day:%b %Y}")

    # Email HTML in two versions (D-040): Gmail keeps the navy masthead; Outlook uses a light one so
    # its text stays readable when Outlook drops colours on paste. The old single file is removed.
    email = env.get_template("email/issue.html.j2")
    for variant in ("gmail", "outlook"):
        html = compact(email.render(**ctx, variant=variant, logo_src=logo_url or "", logo_tile=False))
        (out / f"{stem}-{variant}.html").write_text(html, encoding="utf-8")
    (out / f"{stem}.html").unlink(missing_ok=True)
    text = env.get_template("email/issue.txt.j2").render(**ctx)
    (out / f"{stem}.txt").write_text(text.strip() + "\n", encoding="utf-8")

    # A4 PDF
    from weasyprint import CSS, HTML
    pdf_html = env.get_template("pdf/issue.html.j2").render(**ctx, font_faces=font_faces())
    (out / f"{stem}.pdf.html").write_text(pdf_html, encoding="utf-8")
    document = HTML(string=pdf_html, base_url=str(ROOT))
    try:
        document.write_pdf(out / f"{stem}.pdf", pdf_variant="pdf/ua-1")
    except Exception as exc:  # fall back to an untagged PDF rather than failing the build
        print(f"WARN tagged PDF failed ({exc}); writing a standard PDF", file=sys.stderr)
        document.write_pdf(out / f"{stem}.pdf")

    # WhatsApp snapshot card (1080 x 1350 PNG) and its caption; the caption opens with the
    # registered name and ARN, as SEBI's social media disclosure rule requires
    card_pdf = out / f"{stem}-card.pdf"
    card_html = env.get_template("card/card.html.j2").render(**ctx, font_faces=font_faces())
    HTML(string=card_html, base_url=str(ROOT)).write_pdf(card_pdf)
    run(["pdftoppm", "-png", "-r", "96", "-singlefile", str(card_pdf), str(out / f"{stem}-whatsapp-card")])
    card_pdf.unlink()
    caption = env.get_template("card/caption.txt.j2").render(**ctx)
    (out / f"{stem}-whatsapp-caption.txt").write_text(caption.strip() + "\n", encoding="utf-8")

    if not args.no_previews:
        local_logo = (ROOT / pub["assets"]["logo_email_local"]).resolve()
        data_uri = "data:image/png;base64," + base64.b64encode(local_logo.read_bytes()).decode()
        for stale in ("email-desktop.png", "email-phone.png"):  # single-version previews before D-040
            (out / "preview" / stale).unlink(missing_ok=True)
        previews = {}
        for variant in ("gmail", "outlook"):
            previews[variant] = compact(email.render(**ctx, variant=variant, logo_src=data_uri, logo_tile=False))
        # What a reader sees if Outlook drops every text colour on paste: all text falls back to black
        previews["outlook-nocolour"] = re.sub(r"(?<![-\w])color:[^;\"]*;?", "", previews["outlook"])
        jobs = (("gmail", 704, "gmail-desktop"), ("gmail", 390, "gmail-phone"),
                ("outlook", 704, "outlook-desktop"), ("outlook-nocolour", 704, "outlook-nocolour"))
        for key, width, name in jobs:
            pdf_path = out / "preview" / f"{name}.pdf"
            # presentational_hints: honour width, bgcolor and align attributes as email clients do
            HTML(string=previews[key], base_url=str(ROOT)).write_pdf(
                pdf_path, presentational_hints=True,
                stylesheets=[CSS(string=f"@page {{ size: {width}px 40000px; margin: 0 }}")])
            run(["pdftoppm", "-png", "-r", "96", "-singlefile", str(pdf_path), str(out / "preview" / name)])
            pdf_path.unlink()
            trim_png(out / "preview" / f"{name}.png", background=(255, 255, 255))
        split_png(out / "preview" / "gmail-desktop.png")   # for the hand-off: one tall image is shrunk
        for stale in (out / "preview").glob("pdf-page-*.png"):  # page count can shrink between builds
            stale.unlink()
        run(["pdftoppm", "-png", "-r", "60", str(out / f"{stem}.pdf"), str(out / "preview" / "pdf-page")])

    manifest = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest[str(path.relative_to(out))] = {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
            }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for name, info in manifest.items():
        print(f"{info['bytes']:>9,}  {name}")


if __name__ == "__main__":
    main()
