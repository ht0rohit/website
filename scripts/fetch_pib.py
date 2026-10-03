#!/usr/bin/env python3
"""Fetch recent English press releases from PIB and write data/YYYY-MM-DD.json.

Stdlib only. Fails soft: if nothing can be fetched, existing data is left untouched
and the script exits non-zero so the workflow surfaces the problem.

Usage: python scripts/fetch_pib.py [--max N] [--data-dir DIR]
"""
import argparse, html, json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(__file__))
from categorize import categorize, relevance, is_noise  # noqa: E402

BASE = "https://www.pib.gov.in"
# reg=3 pins the English edition; without it PIB redirects to Hindi.
FEEDS = [f"{BASE}/RssMain.aspx?ModId={m}&Lang=1&Regid=3&reg=3" for m in (6, 8)]
RELEASE = BASE + "/PressReleaseIframePage.aspx?PRID={prid}&reg=3&lang=1"
# PIB answers 403 to user-agents that self-identify as bots; a plain agent is accepted.
UA = "Mozilla/5.0"
MONTHS = {m: i for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}


def http_get(url, retries=3):
    for n in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if n == retries - 1:
                raise
            time.sleep(2 ** (n + 1))


def parse_feed(xml_bytes):
    out = []
    for item in ET.fromstring(xml_bytes.lstrip(b"\xef\xbb\xbf")).iter("item"):
        link = (item.findtext("link") or "").strip()
        m = re.search(r"PRID=(\d+)", link)
        if m:
            out.append((m.group(1), html.unescape((item.findtext("title") or "").strip())))
    return out


class _Text(HTMLParser):
    """Collects <p> text inside the release body (after the PrDateTime div)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.cur, self.paras = [], None, []
        self.ministry = self.title = self.posted = ""
        self._cap = None
        self.seen_date = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append(tag)
        if tag == "div" and a.get("id") == "MinistryName": self._cap = "ministry"
        elif tag == "h1" and a.get("id") == "Titleh2": self._cap = "title"
        elif tag == "div" and a.get("id") == "PrDateTime": self._cap = "posted"
        elif tag == "p" and self.seen_date: self.cur = []
        elif tag in ("script", "style"): self._cap = "skip"

    def handle_endtag(self, tag):
        if self.stack: self.stack.pop()
        if tag in ("div", "h1", "script", "style") and self._cap:
            if self._cap == "posted": self.seen_date = True
            self._cap = None
        if tag == "p" and self.cur is not None:
            t = re.sub(r"\s+", " ", "".join(self.cur)).strip()
            if t: self.paras.append(t)
            self.cur = None

    def handle_data(self, d):
        if self._cap in ("ministry", "title", "posted"):
            setattr(self, self._cap, (getattr(self, self._cap) + " " + d).strip())
        elif self._cap is None and self.cur is not None:
            self.cur.append(d)


def parse_release(page_bytes):
    p = _Text()
    p.feed(page_bytes.decode("utf-8", "ignore"))
    m = re.search(r"(\d{1,2})\s+([A-Z]{3})\s+(\d{4})", p.posted.upper())
    date = f"{int(m.group(3)):04d}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}" if m and m.group(2) in MONTHS else None
    return {"ministry": re.sub(r"\s+", " ", p.ministry), "title": re.sub(r"\s+", " ", p.title),
            "date": date, "paras": [t for t in p.paras if len(t) > 40]}


ABBR = re.compile(r"\b(Rs|Dr|Mr|Mrs|Shri|Smt|Prof|No|Nos|St|vs|approx|Lt|Gen|Col)\.")


def sentences(text):
    text = ABBR.sub(lambda m: m.group(1) + "\u2024", text)  # protect abbreviation dots
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9₹“\"])", text)
    return [s.replace("\u2024", ".").strip() for s in parts if s.strip()]


def summarize(paras, limit=320):
    out = ""
    for s in sentences(" ".join(paras[:3])):
        if len(out) + len(s) > limit:
            break
        out = f"{out} {s}".strip()
    return out or (paras[0][:limit].rsplit(" ", 1)[0] + "…" if paras else "")


FACT_PAT = re.compile(r"(₹|Rs\.?|\bUSD\b|\$|\d+(?:\.\d+)?\s?(?:%|per cent|crore|lakh|billion|million|trillion)|\b(?:19|20)\d{2}\b)", re.I)


def key_facts(paras, summary, n=3):
    facts = []
    for s in sentences(" ".join(paras)):
        if 25 < len(s) < 220 and FACT_PAT.search(s) and s not in summary:
            facts.append(s)
        if len(facts) == n:
            break
    return facts


def build_item(prid, feed_title, rel):
    title = rel["title"] or feed_title
    text = " ".join(rel["paras"])
    summary = summarize(rel["paras"])
    cat = categorize(title, rel["ministry"], text)
    return {
        "id": f"pib-{prid}", "date": rel["date"], "title": title, "summary": summary,
        "ministry": rel["ministry"] or "Press Information Bureau", "category": cat,
        "tags": [], "exam_relevance": relevance(title, rel["ministry"], cat, text),
        "source_url": f"{BASE}/PressReleasePage.aspx?PRID={prid}", "key_facts": key_facts(rel["paras"], summary),
    }


def load_day(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("items", [])
    except FileNotFoundError:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=60, help="max new releases to fetch per run")
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = ap.parse_args()
    os.makedirs(args.data_dir, exist_ok=True)

    known = set()
    for fn in os.listdir(args.data_dir):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", fn):
            known |= {i["id"] for i in load_day(os.path.join(args.data_dir, fn))}

    feed_items, errors = {}, 0
    for url in FEEDS:
        try:
            for prid, title in parse_feed(http_get(url)):
                feed_items.setdefault(prid, title)
        except Exception as e:  # noqa: BLE001
            errors += 1
            print(f"feed failed: {url}: {e}", file=sys.stderr)
        time.sleep(1)
    if not feed_items:
        print("no feed items fetched; leaving data untouched", file=sys.stderr)
        return 1

    new = [(p, t) for p, t in feed_items.items() if f"pib-{p}" not in known and not is_noise(t)][: args.max]
    by_date = {}
    for prid, ftitle in new:
        try:
            rel = parse_release(http_get(RELEASE.format(prid=prid)))
            if not rel["date"] or not rel["paras"]:
                print(f"skip {prid}: unparseable", file=sys.stderr)
                continue
            it = build_item(prid, ftitle, rel)
            by_date.setdefault(it["date"], []).append(it)
        except Exception as e:  # noqa: BLE001
            print(f"release {prid} failed: {e}", file=sys.stderr)
        time.sleep(1)

    for d, items in by_date.items():
        path = os.path.join(args.data_dir, f"{d}.json")
        merged = {i["id"]: i for i in load_day(path)}
        merged.update({i["id"]: i for i in items})
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"date": d, "items": list(merged.values())}, f, ensure_ascii=False, indent=1)

    dates = sorted((fn[:-5] for fn in os.listdir(args.data_dir) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", fn)), reverse=True)
    with open(os.path.join(args.data_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"dates": dates, "sample": False, "source": "Press Information Bureau, Government of India",
                   "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}, f, indent=1)
    print(f"fetched {sum(map(len, by_date.values()))} new items across {len(by_date)} day(s); feed errors: {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
