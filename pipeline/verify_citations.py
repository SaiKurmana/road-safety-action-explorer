"""`make verify-citations`: open every cited page and check the action is really there.

For each entry in actions/actions.yaml this script opens the source PDF (downloaded and
checksum-verified via sources.yml) at the cited `pdf_page` and checks that the action title
appears on that page (word-overlap match, because a few summary-table titles are worded
slightly differently from section headings, e.g. "Mass-Media Campaigns" vs "Mass Media
Campaigns"). For CTW entries it also checks the cited summary-table page; for FHWA PSC
entries it checks the handout number printed on the page.

Exit status is non-zero if any citation fails. Requires network access to rosap.ntl.bts.gov
the first time (files are cached under data/raw/docs/).
"""

from __future__ import annotations

import logging
import re
import sys
from functools import cache
from pathlib import Path

import yaml
from pypdf import PdfReader

from pipeline.config import ACTIONS_YAML, RAW
from pipeline.sources import download, load_sources, sha256_file

logging.getLogger("pypdf").setLevel(logging.ERROR)  # font-encoding warnings are irrelevant here

STOP = {"and", "or", "the", "of", "for", "to", "with", "a", "an", "in", "at", "on", "use"}
ALIASES = {"gdl": "graduated driver licensing", "&": "and", "buses": "bus"}


def words(text: str) -> set[str]:
    # Re-join drop caps that PDF text extraction splits off ("C\nommunication" -> "Communication").
    text = re.sub(r"(?<![A-Za-z])([A-Z])\s*\n\s*(?=[a-z])", r"\1", text)
    text = text.lower().replace("’", "'").replace("-", " ")
    for k, v in ALIASES.items():
        text = re.sub(rf"(?<![a-z]){re.escape(k)}(?![a-z])", v, text)
    return {w for w in re.findall(r"[a-z0-9]+", text) if w not in STOP and len(w) > 1}


@cache
def reader(source_id: str) -> PdfReader:
    doc = next(d for d in load_sources()["documents"] if d["id"] == source_id)
    path = RAW / "docs" / f"{source_id}.pdf"
    if not path.exists():
        download(doc["url"], path)
    if sha256_file(path) != doc["sha256"]:
        raise SystemExit(f"{source_id}: checksum differs from sources.yml; refusing to verify against it")
    return PdfReader(str(path))


@cache
def page_words(source_id: str, pdf_page: int) -> set[str]:
    return words(reader(source_id).pages[pdf_page - 1].extract_text() or "")


def overlap(title: str, source_id: str, pdf_page: int) -> float:
    t = words(title.replace("(NRSS objective)", ""))
    return len(t & page_words(source_id, pdf_page)) / max(1, len(t))


def check(action: dict) -> list[str]:
    errs = []
    sid, page, title = action["source_id"], int(action["pdf_page"]), action["title"]
    score = overlap(title, sid, page)
    if score < 0.6:
        errs.append(f"title words found on PDF p.{page}: {score:.0%}")
    if sid == "ctw_11th_2023":
        m = re.search(r"\(PDF p\. (\d+)\)", action["evidence"]["rating_source"])
        if not m:
            errs.append("rating_source lacks a summary-table PDF page")
        elif overlap(title, sid, int(m.group(1))) < 0.6 and overlap(title, sid, int(m.group(1)) + 1) < 0.6:
            errs.append(f"title not found in summary table PDF p.{m.group(1)}")
    if sid == "fhwa_psc_booklet":
        docno = re.search(r"FHWA-SA-\d{2}-\d{3}", action["page"]).group(0)
        text = reader(sid).pages[page - 1].extract_text() or ""
        if docno not in text.replace(" ", ""):
            errs.append(f"handout number {docno} not on PDF p.{page}")
    return errs


def main() -> int:
    actions = yaml.safe_load(Path(ACTIONS_YAML).read_text())["actions"]
    failures = 0
    for a in actions:
        errs = check(a)
        if errs:
            failures += 1
            print(f"FAIL {a['id']}: {'; '.join(errs)}")
    print(f"verified citations: {len(actions) - failures}/{len(actions)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
