"""Number formatting for the Kubeerra Market Brief.

Indian digit grouping (1,23,456), a true minus sign (U+2212) for negatives,
and the display formats named in schema/issue.schema.json.
"""

MINUS = "−"
RUPEE = "₹"


def group_indian(value, decimals=0):
    """1234567.8 -> '12,34,567.80' (Indian grouping). Always returns the absolute value."""
    text = f"{abs(value):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return whole + ("." + frac if frac else "")


def sign(value):
    if value is None:
        return ""
    return "+" if value > 0 else (MINUS if value < 0 else "")


def direction(value):
    if value is None or value == 0:
        return "flat"
    return "up" if value > 0 else "down"


def arrow(value):
    return {"up": "▲", "down": "▼", "flat": ""}[direction(value)]


def level(value, decimals=2):
    """Index level or price: 25,812.35"""
    return group_indian(value, decimals)


def points(value, decimals=2):
    return sign(value) + group_indian(value, decimals)


def bp(value):
    """Basis points: −5 bp"""
    if value is None:
        return "Not available"
    text = f"{abs(value):.0f}" if float(value).is_integer() else f"{abs(value):.1f}"
    return sign(value) + text + " bp"


def pct(value, decimals=2):
    if value is None:
        return "Not available"
    return sign(value) + f"{abs(value):.{decimals}f}%"


def figure(value, fmt):
    """Format a headline figure by its schema format name."""
    if fmt == "crore_signed":
        decimals = 0 if abs(value) >= 100 else 2
        return f"{sign(value)}{RUPEE}{group_indian(value, decimals)} cr"
    if fmt == "crore":
        decimals = 0 if abs(value) >= 100 else 2
        return f"{RUPEE}{group_indian(value, decimals)} cr"
    if fmt == "inr_level":
        return f"{RUPEE}{group_indian(value, 0)}"
    if fmt == "fx":
        return f"{RUPEE}{value:.2f}"
    if fmt == "usd_bbl":
        return f"${value:,.2f}"
    if fmt == "usd_oz":
        return f"${value:,.0f}"
    if fmt == "pct_level":
        return f"{value:.2f}%"
    if fmt == "lakh_crore":
        return f"{RUPEE}{value:.2f} lakh cr"
    if fmt == "count":
        return group_indian(value, 0)
    raise ValueError(f"unknown figure format: {fmt}")
