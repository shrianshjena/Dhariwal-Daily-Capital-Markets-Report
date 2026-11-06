#!/usr/bin/env python3
"""Prepare the morning Gmail draft (D-043) and check it once Gmail has saved it.

    python3 render/gmail_draft.py prepare issues/2026-11-04.json
    python3 render/gmail_draft.py verify-raw issues/2026-11-04.json <saved get_draft RAW result>
    python3 render/gmail_draft.py verify issues/2026-11-04.json out/2026-11-04/gmail-draft/returned.txt

prepare writes out/<date>/gmail-draft/: body.html (the Gmail email with the logo pointing at the
first inline attachment, cid:att0, because Gmail drafts drop images hosted elsewhere), logo.b64 (a
small logo for that attachment, in 76-character lines to be joined without breaks), body-nologo.html
(the fallback if Gmail rejects the attachment), subject.txt and expected-numbers.txt.

verify-raw reads the draft as Gmail stored it (get_draft with RAW; the tool saves a large result to
a file) and checks two things: the inline logo is byte-for-byte the logo in logo.b64 (on 4 Nov 2026
two miscopied characters left a corrupt image in the email), and every number matches body.html.
verify does the number check alone on the text from get_draft PLAIN_TEXT.
Any failure means the draft is deleted; the HTML files stay the source of truth.
"""
import base64
import email
import hashlib
import io
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "title"):
            self._skip += 1
        if tag == "div" and "display:none" in (dict(attrs).get("style") or ""):
            self._skip += 1  # the hidden preheader is not part of the visible body

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def numbers(text):
    return Counter(n.replace(",", "") for n in NUMBER.findall(text))


def visible_text(html):
    # drop the hidden preheader block whole, then collect text
    html = re.sub(r'<div style="display:none;[^"]*">.*?</div>', "", html, count=1, flags=re.S)
    parser = Text()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def prepare(issue_path):
    issue = json.loads(Path(issue_path).read_text(encoding="utf-8"))
    date = issue["meta"].get("edition_id") or issue["meta"]["date"]
    out = ROOT / "out" / date
    folder = out / "gmail-draft"
    folder.mkdir(parents=True, exist_ok=True)
    html = (out / f"kubeerra-market-brief-{date}-gmail.html").read_text(encoding="utf-8")
    html, n = re.subn(r'<img src="[^"]+"', '<img src="cid:att0"', html, count=1)
    if n != 1:
        sys.exit("no masthead logo found in the Gmail email")
    # short lines (a break after each block closing tag) so the body can be read and copied
    # whole; whitespace between these tags does not change how the email renders
    html = re.sub(r"(</(?:p|tr|table|h1|h2|h3|div|style|head)>)", r"\1\n", html)
    (folder / "body.html").write_text(html, encoding="utf-8")
    # fallback when the logo cannot be attached intact: the same email with a lettered tile drawn
    # in HTML (gold K on black, as in the logo), so the masthead never shows a broken image
    tile = ('<td width="48" height="48" valign="middle" align="center" bgcolor="#0A0A0A" style="width:48px;'
            'height:48px;background-color:#0A0A0A;border:2px solid #C9A227;text-align:center;font-family:Georgia,'
            '\'Times New Roman\',serif;font-size:30px;line-height:44px;font-weight:700;color:#D4AF37;">K</td>')
    nologo, n = re.subn(r'<td width="48" valign="middle" style="width:48px;"><img src="cid:att0"[^>]*></td>',
                        lambda m: tile, html, count=1)
    if n != 1:
        sys.exit("could not build the fallback masthead")
    (folder / "body-nologo.html").write_text(nologo, encoding="utf-8")

    from PIL import Image
    pub = json.loads((ROOT / "config" / "publication.json").read_text(encoding="utf-8"))
    # 48 px and 16 colours keeps the encoded logo near 1,200 characters, short enough to copy
    # into the tool call reliably (a 4,600-character version failed on 3 Nov 2026)
    logo = Image.open(ROOT / pub["assets"]["logo_email_local"]).convert("RGBA").resize((48, 48), Image.LANCZOS)
    flat = Image.new("RGB", logo.size, (11, 31, 51))  # navy, the Gmail masthead colour
    flat.paste(logo, mask=logo.split()[3])
    buf = io.BytesIO()
    flat.quantize(colors=16).save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    (folder / "logo.sha256").write_text(hashlib.sha256(buf.getvalue()).hexdigest() + "\n", encoding="ascii")
    # 76-character lines so the file reads whole; join the lines (no breaks) for the attachment
    (folder / "logo.b64").write_text("\n".join(b64[i:i + 76] for i in range(0, len(b64), 76)) + "\n",
                                     encoding="ascii")

    subject = issue["meta"].get("subject") or f"Kubeerra Market Brief · {issue['meta']['weekday']} {date}"
    (folder / "subject.txt").write_text(subject + "\n", encoding="utf-8")
    expected = numbers(visible_text(html))
    (folder / "expected-numbers.txt").write_text(
        "\n".join(f"{k} x{v}" for k, v in sorted(expected.items())) + "\n", encoding="utf-8")
    print(f"prepared {folder.relative_to(ROOT)}: body.html {len(html):,} bytes, "
          f"logo.b64 {(folder / 'logo.b64').stat().st_size:,} characters, {sum(expected.values())} numbers")


def verify(issue_path, returned_path):
    issue = json.loads(Path(issue_path).read_text(encoding="utf-8"))
    folder = ROOT / "out" / (issue["meta"].get("edition_id") or issue["meta"]["date"]) / "gmail-draft"
    expected = numbers(visible_text((folder / "body.html").read_text(encoding="utf-8")))
    returned = Path(returned_path).read_text(encoding="utf-8")
    # get_draft returns Gmail's own HTML when the draft has no plain-text part: read its text
    got = numbers(visible_text(returned) if re.search(r"<(td|p|table)\b", returned) else returned)
    missing, extra = expected - got, got - expected
    if missing or extra:
        print("DRAFT MISMATCH: delete the draft and say so in the hand-off")
        for k, v in sorted(missing.items()):
            print(f"  missing from draft: {k} (x{v})")
        for k, v in sorted(extra.items()):
            print(f"  extra in draft:     {k} (x{v})")
        sys.exit(1)
    print(f"DRAFT OK: all {sum(expected.values())} numbers match the Gmail email")


def raw_message(path):
    """The draft's MIME message from a saved get_draft RAW result: JSON holding a base64url
    'raw' field (possibly nested under 'message'), or the raw .eml text itself."""
    text = Path(path).read_text(encoding="utf-8", errors="replace").strip()
    if text.startswith("{"):
        data = json.loads(text)
        raw = data.get("raw") or (data.get("message") or {}).get("raw")
        if not raw:
            sys.exit("no 'raw' field in the saved get_draft result")
        return email.message_from_bytes(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    return email.message_from_string(text)


def verify_raw(issue_path, raw_path):
    issue = json.loads(Path(issue_path).read_text(encoding="utf-8"))
    folder = ROOT / "out" / (issue["meta"].get("edition_id") or issue["meta"]["date"]) / "gmail-draft"
    msg = raw_message(raw_path)
    html, pngs = None, []
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/html" and html is None:
            html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
        elif ctype == "image/png":
            pngs.append(part.get_payload(decode=True))
    if html is None:
        sys.exit("DRAFT MISMATCH: the draft has no HTML part")
    ok = True
    uses_logo = "cid:" in html
    if uses_logo:
        want = (folder / "logo.sha256").read_text(encoding="ascii").strip()
        got = [hashlib.sha256(b).hexdigest() for b in pngs]
        if want in got:
            print("LOGO OK: the inline logo matches logo.b64 byte for byte")
        else:
            ok = False
            print("LOGO CORRUPT: the inline image differs from logo.b64 (a miscopied character); "
                  "delete the draft and create it again")
    else:
        print("LOGO TILE: the draft uses the lettered tile, no image to check")
    expected = numbers(visible_text((folder / "body.html").read_text(encoding="utf-8")))
    got_n = numbers(visible_text(html))
    missing, extra = expected - got_n, got_n - expected
    if missing or extra:
        ok = False
        print("DRAFT MISMATCH: numbers differ from the Gmail email")
        for k, v in sorted(missing.items()):
            print(f"  missing from draft: {k} (x{v})")
        for k, v in sorted(extra.items()):
            print(f"  extra in draft:     {k} (x{v})")
    else:
        print(f"NUMBERS OK: all {sum(expected.values())} numbers match the Gmail email")
    if not ok:
        sys.exit(1)
    print("DRAFT OK")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "prepare":
        prepare(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "verify-raw":
        verify_raw(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "verify":
        verify(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
