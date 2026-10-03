"""Map a PIB release (title + ministry + text) to an exam category and relevance."""
import re

# Ordered: first matching rule wins.
CATEGORY_RULES = [
    ("RBI & Monetary Policy", r"\b(reserve bank|rbi|repo rate|monetary policy|mpc|inflation|liquidity|crr|slr)\b"),
    ("Appointments", r"\b(appoint(?:s|ed|ment)?|takes? charge|assumes? charge|new (?:chairman|governor|secretary|chief))\b"),
    ("Awards & Honours", r"\b(award|awarded|honou?r|prize|felicitat|conferred|rank(?:ed|ing)|index)\b"),
    ("MoUs & Agreements", r"\b(mou|memorandum of understanding|agreement|signs?|signed|pact|treaty)\b"),
    ("Summits & Conferences", r"\b(summit|conference|conclave|forum|g20|brics|sco|quad|asean|cop\d*|session|sammelan|sammilan)\b"),
    ("Economy & Banking", r"\b(bank|banking|gst|tax|fiscal|budget|gdp|economy|economic|export|import|trade|msme|finance|insurance|sebi|nabard|ipo|forex|fdi|investment|upi|digital payment|loan|credit|pension|nps|mudra|gem)\b"),
    ("Science & Tech", r"\b(isro|space|satellite|ai\b|artificial intelligence|semiconductor|quantum|drdo|missile|research|innovation|technology|nuclear|cyber)\b"),
    ("Sports", r"\b(olympic|games|medal|championship|cricket|hockey|athlet|khelo|sports?)\b"),
    ("Government Schemes", r"\b(yojana|scheme|mission|abhiyan|pm-|pradhan mantri|programme|portal|launch(?:es|ed)?|initiative)\b"),
    ("International", r"\b(bilateral|foreign|visit|ambassador|diaspora|united nations|un\b|imf|world bank|wto|abroad|prime minister of)\b"),
]
SKIP_PATTERNS = re.compile(r"\b(condol|obituary|passed away|demise|tributes? to|greets? (?:the )?(?:nation|people))\b", re.I)
BANKING_MINISTRIES = re.compile(r"finance|corporate affairs|commerce|reserve bank|financial services|cooperation|micro, small", re.I)
RBI_PAT = re.compile(r"\b(reserve bank|rbi|monetary policy|repo rate|sebi|irdai|nabard|sidbi)\b", re.I)


def is_noise(title: str) -> bool:
    return bool(SKIP_PATTERNS.search(title))


def categorize(title: str, ministry: str = "", text: str = "") -> str:
    hay = f"{title} {ministry} {text[:600]}".lower()
    # Title match is stronger than body match: check title first.
    for name, pat in CATEGORY_RULES:
        if re.search(pat, title.lower()):
            return name
    for name, pat in CATEGORY_RULES:
        if re.search(pat, hay):
            return name
    return "National"


def relevance(title: str, ministry: str, category: str, text: str = "") -> str:
    blob = f"{title} {text[:400]}"
    if RBI_PAT.search(blob) or category == "RBI & Monetary Policy":
        return "rbi"
    if BANKING_MINISTRIES.search(ministry) or category == "Economy & Banking":
        return "banking"
    if category in ("Appointments", "Awards & Honours", "Summits & Conferences", "MoUs & Agreements", "Government Schemes"):
        return "ssc"
    return "general"
