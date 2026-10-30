#!/usr/bin/env python3
"""Render one Kubeerra Market Brief issue into every format.

    python3 render/build.py issues/2026-10-29.json [--logo-url URL] [--no-previews]

Outputs go to out/<date>/:
    kubeerra-market-brief-<date>.html   email HTML (inline styles; Outlook and Gmail safe)
    kubeerra-market-brief-<date>.txt    plain-text alternative
    kubeerra-market-brief-<date>.pdf    A4 PDF
    preview/                            PNG previews of the email (640 and 390 px) and PDF pages
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
    top = items[:4]
    bottom = list(reversed(items[-4:]))
    biggest = max(abs(s["change_pct"]) for s in top + bottom) or 1
    def bar(s):
        return dict(s, bar=max(2, round(abs(s["change_pct"]) / biggest * 100)))
    return {"top": [bar(s) for s in top], "bottom": [bar(s) for s in bottom], "max": biggest}


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
    out = ROOT / "out" / date
    (out / "preview").mkdir(parents=True, exist_ok=True)
    stem = f"kubeerra-market-brief-{date}"
    env = build_env(tokens)

    logo_url = args.logo_url or pub["assets"]["logo_email_url"]
    if not logo_url:
        print("WARN no hosted logo URL: the email masthead will show alt text until one is set", file=sys.stderr)

    day = datetime.date.fromisoformat(date)
    snapshot_sources = list({s['source']['url']: s['source'] for s in issue['snapshot']['indices']}.values())
    global_sources = list({s['url']: s for s in [g['source'] for g in issue['global']['items']]
                           + issue['global'].get('note_sources', [])}.values())
    # Scheme names appear only in the internal edition, and only when every NFO carries its riskometer
    nfos = issue["mf"].get("nfos") or []
    show_nfo_names = issue["meta"].get("audience") == "internal" and bool(nfos) and all(n.get("riskometer") for n in nfos)
    ctx = dict(issue=issue, pub=pub, tokens=tokens, sectors=sector_view(issue), snapshot_sources=snapshot_sources,
               global_sources=global_sources, show_nfo_names=show_nfo_names,
               date_long=f"{day.day} {day:%B %Y}", date_short=f"{day.day} {day:%b %Y}")

    # Email HTML (the send build) and plain text
    email_html = compact(env.get_template("email/issue.html.j2").render(**ctx, logo_src=logo_url or ""))
    (out / f"{stem}.html").write_text(email_html, encoding="utf-8")
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
        preview_html = compact(env.get_template("email/issue.html.j2").render(**ctx, logo_src=data_uri))
        for width, name in ((704, "email-desktop"), (390, "email-phone")):
            pdf_path = out / "preview" / f"{name}.pdf"
            # presentational_hints: honour width, bgcolor and align attributes as email clients do
            HTML(string=preview_html, base_url=str(ROOT)).write_pdf(
                pdf_path, presentational_hints=True,
                stylesheets=[CSS(string=f"@page {{ size: {width}px 20000px; margin: 0 }}")])
            run(["pdftoppm", "-png", "-r", "96", "-singlefile", str(pdf_path), str(out / "preview" / name)])
            pdf_path.unlink()
            trim_png(out / "preview" / f"{name}.png")
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
