#!/usr/bin/env python3
"""Copy one issue's deliverables into deliverables/ for collaborators, and prune old ones (D-041).

    python3 render/publish.py issues/2026-11-04.json

Each format has its own folder. The 14 most recent issues are kept in each deliverable folder;
older files are deleted (git history still holds them). Check reports, review logs and the issue
data files in issues/ are records and are never deleted.
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "deliverables"
KEEP = 14
FORMATS = {
    "pdf": ["{stem}.pdf"],
    "gmail": ["{stem}-gmail.html"],
    "outlook": ["{stem}-outlook.html"],
    "whatsapp": ["{stem}-whatsapp-card.png", "{stem}-whatsapp-caption.txt"],
    "text": ["{stem}.txt"],
}
RECORDS = ("check-reports", "reviews")
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def prune(folder):
    """Delete files whose issue date is older than the KEEP most recent dates in the folder."""
    dated = {}
    for path in folder.iterdir():
        m = DATE.search(path.name)
        if path.is_file() and m:
            dated.setdefault(m.group(1), []).append(path)
    removed = []
    for date in sorted(dated, reverse=True)[KEEP:]:
        for path in dated[date]:
            path.unlink()
            removed.append(path.relative_to(ROOT))
    return removed


def main():
    issue = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    date = issue["meta"]["date"]
    stem = f"kubeerra-market-brief-{date}"
    out = ROOT / "out" / date
    problems, copied, removed = [], [], []

    for fmt, names in FORMATS.items():
        folder = DELIVERABLES / fmt
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            src = out / name.format(stem=stem)
            if src.exists():
                shutil.copy2(src, folder / src.name)
                copied.append((folder / src.name).relative_to(ROOT))
            else:
                problems.append(f"missing {src.relative_to(ROOT)}: run render/build.py first")
        removed += prune(folder)

    for record in RECORDS:
        (DELIVERABLES / record).mkdir(parents=True, exist_ok=True)
    if not (DELIVERABLES / "check-reports" / f"{date}-check-report.md").exists():
        problems.append(f"missing deliverables/check-reports/{date}-check-report.md: run checks/check_issue.py")
    if not (DELIVERABLES / "reviews" / f"{date}-review.md").exists():
        problems.append(f"missing deliverables/reviews/{date}-review.md: write the review log")

    for path in copied:
        print(f"copied   {path}")
    for path in removed:
        print(f"removed  {path} (older than the {KEEP} most recent issues)")
    for problem in problems:
        print(f"WARN     {problem}", file=sys.stderr)
    sys.exit(1 if any(p.startswith("missing out") or "build.py" in p for p in problems) else 0)


if __name__ == "__main__":
    main()
