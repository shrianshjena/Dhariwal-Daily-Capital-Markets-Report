#!/usr/bin/env python3
"""Automated checks for a rendered Kubeerra Market Brief issue.

    python3 checks/check_issue.py issues/2026-10-29.json

FAIL (exit 1): em or en dashes; banned phrases; missing disclosures; email HTML over
102 KB (Gmail clips larger messages); images without alt text or size; any link that does not
go to kubeerra.com or the firm's email address (D-039); text on a dark background in the
Outlook version (D-040); PDF without extractable text or with unembedded fonts.
REVIEW (reported, not failing): advice-like or sensational words in the issue's own
writing, which a person must read in context; source URLs missing from the sources list.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DASHES = {"—": "em dash", "–": "en dash"}
BANNED = [
    r"\bguarantee(d|s)?\b", r"\bassured returns?\b", r"\brisk[- ]free\b", r"\bmultibagger",
    r"\bsure[- ]shot\b", r"\btarget price", r"\bgrey market premium\b", r"\bGMP\b", r"\bjackpot\b",
]
REVIEW = [
    r"\badvis(e|ory|er|ers)\b", r"\badvisor", r"\bIFA\b", r"\bwealth manag", r"\bportfolio management\b",
    r"\brecommend", r"\btips?\b", r"\b(buy|sell|hold)\b", r"\bbullish\b", r"\bbearish\b", r"\bre-?rat",
    r"\bbest (fund|scheme)s?\b", r"\btop picks?\b", r"\bshould (invest|buy|sell)\b", r"\bcrash",
    r"\bbloodbath\b", r"\bpanic\b", r"\bfrenzy\b", r"\bsoar", r"\bplung", r"\bskyrocket", r"\bpredict",
    r"\bwill (rise|fall|rally|climb|drop)\b", r"\boutperform", r"\bupside\b", r"\bdownside\b",
]
REQUIRED = {
    "AMFI tagline": "AMFI-registered Mutual Fund Distributor",
    "ARN": "ARN-369716",
    "standard warning (exact)": "Mutual Fund investments are subject to market risks, read all scheme related documents carefully.",
    "not an Investment Adviser": "not a SEBI-registered Investment Adviser",
}
# Sources that publish grey market premium tables or ratings on IPOs (lane: no GMP, no IPO views)
GMP_DOMAINS = ("ipogyani.com", "investorgain.com", "chittorgarh.com", "ipowatch.in", "ipocentral.in",
               "ipoplatform.com", "gmpipowatch", "ipopremium.in", "dhan.co/blog/ipo")
GMP_WARN = ("groww.in/blog", "5paisa.com", "tapetide.com")  # GMP links in navigation or footer (checked 29 to 30 Oct)
# Pages that are not reporting: AI-written summaries of other outlets, and broker marketing (checked 30 Oct)
SOURCE_WARN = {"indianopinion.org": "AI-written summary of other outlets, not wire copy",
               "admiralmarkets.com": "CFD broker marketing page"}
# The only link targets allowed in what readers receive (D-039)
LINK_OK = re.compile(r"^(https://(www\.)?kubeerra\.com(/|$)|mailto:dhariwal\.securities@kubeerra\.com)")
EMAIL_FAIL_BYTES = 102_000
EMAIL_WARN_BYTES = 90_000


VOID = {"br", "img", "meta", "link", "hr", "input", "col", "source", "wbr", "area", "base"}


def luminance(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return 1.0
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


class Collector(HTMLParser):
    """Visible text, images and links; also text that sits on a dark background."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.imgs, self.links, self._skip = [], [], [], 0
        self._bg, self.dark_text = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("style", "script"):
            self._skip += 1
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "a":
            self.links.append(a.get("href", ""))
        if tag in VOID:
            return
        colour = a.get("bgcolor") or ""
        m = re.search(r"background(?:-color)?:\s*(#[0-9a-fA-F]{3,6})", a.get("style") or "")
        if m:
            colour = m.group(1)
        self._bg.append((tag, colour.startswith("#") and luminance(colour) < 0.18))

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._skip -= 1
        if tag in VOID:
            return
        for i in range(len(self._bg) - 1, -1, -1):  # tolerate unclosed tags
            if self._bg[i][0] == tag:
                del self._bg[i:]
                break

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)
            if data.strip(" \n\t\u00a0") and any(dark for _, dark in self._bg):
                self.dark_text.append(data.strip()[:40])


def strings(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from strings(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, f"{path}/{i}")
    elif isinstance(node, str):
        yield path, node


def urls(node):
    for path, value in strings(node):
        if path.endswith("/url"):
            yield value


def context(text, match, width=48):
    start, end = max(0, match.start() - width), min(len(text), match.end() + width)
    return text[start:end].replace("\n", " ")


def main():
    issue_path = Path(sys.argv[1])
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    date = issue["meta"]["date"]
    out = ROOT / "out" / date
    stem = f"kubeerra-market-brief-{date}"
    fails, warns, reviews, passes = [], [], [], []

    emails = {}
    for variant in ("gmail", "outlook"):
        raw = (out / f"{stem}-{variant}.html").read_text(encoding="utf-8")
        parsed_variant = Collector()
        parsed_variant.feed(raw)
        emails[variant] = (raw, parsed_variant, " ".join(" ".join(parsed_variant.text).split()))
    html_raw, parsed, html_text = emails["gmail"]
    pdf_html = Collector()
    pdf_html.feed((out / f"{stem}.pdf.html").read_text(encoding="utf-8"))
    txt = (out / f"{stem}.txt").read_text(encoding="utf-8")

    from pypdf import PdfReader
    reader = PdfReader(out / f"{stem}.pdf")
    pdf_text = " ".join(" ".join((p.extract_text() or "") for p in reader.pages).split())

    # 1. Dashes anywhere
    for label, text in (("issue", "\n".join(s for _, s in strings(issue))), ("Gmail email", html_text),
                        ("Outlook email", emails["outlook"][2]), ("text", txt), ("pdf", pdf_text)):
        for ch, name in DASHES.items():
            if ch in text:
                fails.append(f"{name} found in {label} output")
    if not any(f.startswith(("em dash", "en dash")) for f in fails):
        passes.append("No em or en dashes in the issue, email, text or PDF")

    # 2. Banned phrases anywhere
    corpus = "\n".join([s for _, s in strings(issue)] + [html_text, emails["outlook"][2], txt, pdf_text])
    hits = [(p, context(corpus, m)) for p in BANNED for m in re.finditer(p, corpus, re.I)]
    fails += [f"banned phrase /{p}/: ...{c}..." for p, c in hits]
    if not hits:
        passes.append("No banned phrases (guaranteed, risk-free, target price, GMP and similar)")

    # 3. Review words in the issue's own writing only (boilerplate disclosures excluded)
    for path, value in strings(issue):
        if path.endswith("/url") or path.startswith("/sources") or path.endswith("/source/name"):
            continue
        for p in REVIEW:
            for m in re.finditer(p, value, re.I):
                reviews.append(f"{path}: '{m.group(0)}' in ...{context(value, m)}...")

    # 4. Required disclosures in every format
    for name, phrase in REQUIRED.items():
        missing = [lbl for lbl, text in (("Gmail email", html_text), ("Outlook email", emails["outlook"][2]),
                                          ("text", txt), ("pdf", pdf_text)) if phrase not in text]
        if missing:
            fails.append(f"missing {name} in: {', '.join(missing)}")
        else:
            passes.append(f"{name} present in both emails, text and PDF")

    # 5. Email size (both versions)
    for variant, (raw, _, _) in emails.items():
        size = len(raw.encode("utf-8"))
        if size > EMAIL_FAIL_BYTES:
            fails.append(f"{variant} email HTML is {size:,} bytes; Gmail clips above about 102 KB")
        elif size > EMAIL_WARN_BYTES:
            warns.append(f"{variant} email HTML is {size:,} bytes; budget is under 90 KB")
        else:
            passes.append(f"{variant.capitalize()} email HTML size {size:,} bytes (budget under 90 KB)")

    # 5b. Outlook version: no text on a dark background (Outlook can drop text colours on paste)
    dark = emails["outlook"][1].dark_text
    if dark:
        fails += [f"Outlook email has text on a dark background: '{d}'" for d in dark[:5]]
    else:
        passes.append("Outlook email: all text on light backgrounds (readable if Outlook drops colours)")

    # 6. Images
    for img in parsed.imgs + emails["outlook"][1].imgs:
        src = img.get("src", "")
        if not img.get("alt"):
            fails.append(f"image without alt text: {src[:60]}")
        if not (img.get("width") and img.get("height")):
            fails.append(f"image without width and height: {src[:60]}")
        if src.startswith("data:"):
            warns.append("image uses a data URI; Gmail does not show these. Host it and pass --logo-url")
        elif not src.startswith("https://"):
            warns.append(f"image source is not a hosted https URL: {src[:60] or '(empty)'}")
    if not parsed.imgs:
        warns.append("email has no images: the masthead logo is missing until a hosted URL is set")

    # 7. Links: only kubeerra.com pages and the firm's email address, in every format (D-039)
    bad = []
    for label, links in (("Gmail email", parsed.links), ("Outlook email", emails["outlook"][1].links),
                         ("PDF", pdf_html.links)):
        bad += [f"{label}: {h or '(empty)'}" for h in links if not LINK_OK.match(h or "")]
    bad += [f"text: {u}" for u in re.findall(r"https?://\S+", txt) if not LINK_OK.match(u)]
    fails += [f"link goes outside kubeerra.com: {b}" for b in sorted(set(bad))]
    if not bad:
        n = len(parsed.links) + len(emails["outlook"][1].links) + len(pdf_html.links)
        passes.append(f"All {n} links in the emails and PDF go to kubeerra.com or the firm's email address")

    # 8. Sources list covers every URL used
    listed = {s["url"] for s in issue["sources"]}
    used = {u for u in urls({k: v for k, v in issue.items() if k != "sources"}) if not LINK_OK.match(u)}
    missing_sources = sorted(used - listed)
    if missing_sources:
        warns += [f"source used but not in the sources list: {u}" for u in missing_sources]
    else:
        passes.append(f"Sources list covers all {len(used)} URLs used")

    # 8b. No source that carries grey market premium content
    all_urls = set(urls(issue))
    gmp = sorted(u for u in all_urls if any(d in u for d in GMP_DOMAINS))
    fails += [f"source publishes grey market premium content: {u}" for u in gmp]
    warns += [f"source site links to grey market premium content; prefer another page: {u}"
              for u in sorted(all_urls) if any(d in u for d in GMP_WARN)]
    warns += [f"source is not a reporting page ({why}); cite the original: {u}"
              for u in sorted(all_urls) for d, why in SOURCE_WARN.items() if d in u]
    if not gmp:
        passes.append("No sources from grey market premium sites")

    # 9. WhatsApp caption opens with the registered name and ARN (SEBI social media rule)
    caption_path = out / f"{stem}-whatsapp-caption.txt"
    if caption_path.exists():
        first = caption_path.read_text(encoding="utf-8").splitlines()[0]
        if "ARN-369716" in first and "Dhariwal Securities Private Limited" in first:
            passes.append("WhatsApp caption opens with the registered name and ARN")
        else:
            fails.append("WhatsApp caption must open with the registered name and ARN")
        for ch, name in DASHES.items():
            if ch in caption_path.read_text(encoding="utf-8"):
                fails.append(f"{name} found in the WhatsApp caption")

    # 9b. Client editions: no internal labels, no clock-time stamps, registration at the bottom
    if issue["meta"].get("audience") == "client":
        markers = ["internal pilot", "not for clients", "rm and mf team", "dry run", "pilot note"]
        caption_text = caption_path.read_text(encoding="utf-8") if caption_path.exists() else ""
        found = [(m, lbl) for m in markers for lbl, text in
                 (("Gmail email", html_text), ("Outlook email", emails["outlook"][2]), ("text", txt),
                  ("pdf", pdf_text), ("caption", caption_text))
                 if m in text.lower()]
        fails += [f"client edition contains internal label '{m}' in {lbl}" for m, lbl in found]
        clock = re.compile(r"\b\d{1,2}:\d{2}\s?(AM|PM)\b", re.I)
        for path, value in strings(issue):
            if path.endswith("/url") or path.startswith("/sources") or path.startswith("/day_ahead"):
                continue
            if clock.search(value):
                where = "fails" if path.startswith(("/meta", "/flows", "/global/items", "/snapshot")) else "warns"
                (fails if where == "fails" else warns).append(
                    f"clock time in a client edition at {path}: '{clock.search(value).group(0)}'")
        tag = REQUIRED["AMFI tagline"]
        if tag in html_text and html_text.index(tag) < 0.6 * len(html_text):
            fails.append("registration line appears near the top of the email; it belongs in the footer")
        if len(reader.pages) > 1 and "ARN-369716" in (reader.pages[0].extract_text() or ""):
            fails.append("registration line appears on page 1 of the PDF; it belongs at the end")
        if not found:
            passes.append("Client edition: no internal labels; registration at the bottom")

    # 10. PDF quality
    pages = len(reader.pages)
    if len(pdf_text) < 1000:
        fails.append("PDF text is not extractable")
    else:
        passes.append(f"PDF text is selectable ({len(pdf_text):,} characters)")
    if not 4 <= pages <= 7:
        warns.append(f"PDF has {pages} pages; the standard length is four to seven")
    else:
        passes.append(f"PDF length {pages} pages")
    unembedded = set()
    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for ref in fonts.values():
            font = ref.get_object()
            desc = font.get("/FontDescriptor")
            if desc is None and "/DescendantFonts" in font:
                desc = font["/DescendantFonts"][0].get_object().get("/FontDescriptor")
            desc = desc.get_object() if desc is not None else {}
            if not any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                unembedded.add(str(font.get("/BaseFont")))
    if unembedded:
        fails.append(f"PDF fonts not embedded: {', '.join(sorted(unembedded))}")
    else:
        passes.append("All PDF fonts embedded")

    sys.path.insert(0, str(ROOT / "render"))
    import fmt
    subject = issue["meta"].get("subject") or f"Kubeerra Market Brief · {issue['meta']['weekday']} {date}"
    confirm = [f"- [ ] {r['name']}: {fmt.level(r['close'])} ({fmt.pct(r['change_pct'])}), {r['source']['url']}"
               for r in issue["snapshot"]["indices"]]
    confirm += [f"- [ ] {t['label']}: {fmt.figure(t['value'], t['format'])}"
                + (f" ({fmt.pct(t['change_pct'])})" if t.get("change_pct") is not None
                   else (f" ({fmt.bp(t['change_bp'])})" if t.get("change_bp") is not None else ""))
                + f", {t['source']['url']}"
                for t in issue["flows"]["tiles"] + issue["mf"]["stats"]]
    il = issue["mf"].get("inflow_leaders")
    if il:
        confirm += [f"- [ ] Net inflow, {il['period']}: {x['scheme']} {fmt.figure(x['net_inflow_cr'], 'crore')} "
                    f"(riskometer {x['riskometer']}, {x['riskometer_source']['url']}), {il['source']['url']}"
                    for x in il["items"]]
    etfs = issue["mf"].get("etfs")
    if etfs:
        confirm += [f"- [ ] ETF turnover, {etfs['as_of']}: {x['name']} {fmt.figure(x['turnover_cr'], 'crore')} "
                    f"(riskometer {x['riskometer']}, {x['riskometer_source']['url']}), {etfs['source']['url']}"
                    for x in etfs["items"]]

    lines = [f"Suggested subject: {subject}", "", f"# Checks for {stem}", ""]
    lines += [f"- FAIL: {f}" for f in fails] + [f"- WARN: {w}" for w in warns]
    lines += [f"- PASS: {p}" for p in passes]
    lines += ["", f"## Figures to confirm before sending ({len(confirm)})", ""] + confirm
    lines += ["", f"## Words for human review ({len(reviews)})", ""] + [f"- {r}" for r in reviews]
    report = "\n".join(lines) + "\n"
    (out / "check-report.md").write_text(report, encoding="utf-8")
    # keep a committed copy in deliverables/check-reports (out/ is not committed); fixtures get none
    if issue_path.resolve().parent == (ROOT / "issues").resolve():
        reports = ROOT / "deliverables" / "check-reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / f"{date}-check-report.md").write_text(report, encoding="utf-8")
    print(report)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
