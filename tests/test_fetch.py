"""Offline tests against saved PIB fixtures. Run: python tests/test_fetch.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fetch_pib as f
from categorize import categorize, is_noise

here = os.path.dirname(__file__)
feed = f.parse_feed(open(os.path.join(here, "pib_feed_sample.xml"), "rb").read())
assert len(feed) >= 10 and all(p.isdigit() for p, _ in feed), feed[:2]
rel = f.parse_release(open(os.path.join(here, "pib_release_sample.html"), "rb").read())
assert rel["title"] and rel["ministry"] and rel["date"] and rel["paras"], rel
item = f.build_item("2318631", "x", rel)
for k in ("id", "date", "title", "summary", "ministry", "category", "exam_relevance", "source_url", "key_facts"):
    assert k in item, k
assert item["date"].count("-") == 2 and item["summary"]
assert categorize("RBI keeps repo rate unchanged") == "RBI & Monetary Policy"
assert categorize("India signs MoU with Japan") == "MoUs & Agreements"
assert is_noise("PM condoles demise of veteran actor")
print("ok:", item["date"], "|", item["category"], "|", item["title"])
