"""Collect the full published catalogue from the official BIS standards portal.

`standards.bis.gov.in` is an Angular SPA, so there is nothing useful in its
HTML. The data comes from the JSON API its bundle calls:

    POST https://standardsadmin.bis.gov.in/proposal-service/getWebsiteIndianStandardsList
    body: {"page": 1, "pageSize": 100}

which returns, per record: `standardNumber`, `standardName`, `departmentName`,
`sectionalCommitteeName`, `typeOfStandardName`, `publishedOn`, plus ids. It
reports `totalRecord` and `hasMore`, and paginates stably.

**What this API does NOT return: scope text, ICS codes, keywords, QCO status or
normative references.** Those are what make the recommender useful, so this
collector *merges* rather than replaces: the API supplies breadth (every
published IS number, title, department, committee and year) and the curated
corpus in `data/seed/standards.jsonl` keeps supplying depth for the records it
covers. Curated fields always win.

Output goes to `data/processed/standards.jsonl`, which `config.active_corpus()`
prefers over the seed file — so the seed stays intact and is restored simply by
deleting the processed file.

Usage:
    python -m app.ingestion.collector                 # fetch everything, merge, write
    python -m app.ingestion.collector --limit 2000    # cap records (quick trial)
    python -m app.ingestion.collector --from-cache    # re-merge cached pages, no network

Then, and this is not optional:
    python -m app.ingestion.build_index --rebuild
    python -m app.ingestion.calibrate     # the floors WILL move at this scale
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from app import bis_reference as bis
from app.config import get_settings
from app.ingestion import taxonomy as taxonomy_module
from app.ingestion.normalize import load_jsonl, write_jsonl
from app.models import Standard

API_URL = (
    "https://standardsadmin.bis.gov.in/proposal-service/getWebsiteIndianStandardsList"
)

# The server caps a page at 100 however much we ask for, so there is no point
# requesting more.
PAGE_SIZE = 100

# Courtesy delay between requests to a public government service. ~244 requests
# at this rate is about a minute — slow enough to be unobtrusive, fast enough
# to be practical.
REQUEST_DELAY_SECONDS = 0.25

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://standards.bis.gov.in",
    "Referer": "https://standards.bis.gov.in/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
}

# Fields the API can never tell us. When merging, a curated record's value for
# any of these is preserved even though the API record is "newer".
_CURATED_FIELDS = (
    "scope",
    "keywords",
    "ics_codes",
    "qco_mandatory",
    "qco_name",
    "certification_scheme",
    "normative_refs",
    "test_methods",
    "supersedes",
    "superseded_by",
    "amendment_count",
    "verification",
)


def _cache_path(raw_dir: Path, page: int) -> Path:
    return raw_dir / f"bis_portal_page_{page:05d}.json"


def fetch_pages(limit: int | None = None) -> list[dict[str, Any]]:
    """Page through the BIS catalogue API, caching each page to data/raw/."""
    settings = get_settings()
    settings.raw_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    page = 1
    total: int | None = None

    with httpx.Client(headers=HEADERS, timeout=90.0, follow_redirects=True) as client:
        while True:
            response = client.post(
                API_URL, json={"page": page, "pageSize": PAGE_SIZE}
            )
            response.raise_for_status()
            payload = response.json()

            _cache_path(settings.raw_dir, page).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )

            records = payload.get("data") or []
            if not records:
                break

            if total is None:
                total = payload.get("totalRecord")
                print(f"  catalogue reports {total} published standards")

            rows.extend(records)
            if page % 10 == 0 or not payload.get("hasMore"):
                print(f"  page {page}: {len(rows)} of {total} records")

            if limit and len(rows) >= limit:
                return rows[:limit]
            if not payload.get("hasMore"):
                break

            page += 1
            time.sleep(REQUEST_DELAY_SECONDS)

    return rows


def load_cached_pages() -> list[dict[str, Any]]:
    """Re-read previously fetched pages — no network required."""
    settings = get_settings()
    rows: list[dict[str, Any]] = []
    for path in sorted(settings.raw_dir.glob("bis_portal_page_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload.get("data") or [])
    return rows


def _committee(raw: str) -> str:
    """'PGD 38 - Metal Containers' -> 'PGD 38'.

    Keep only the code: the descriptive tail is committee *scope*, not identity,
    and `Standard.department_code()` reads the first token.

    The portal also emits a bare department code with no committee number
    ('CHD') and an em-dash placeholder ('—') for a handful of records. The
    first is kept as-is; the second must become empty, or the dash ends up
    masquerading as a department code in every facet and coverage count.
    """
    text = (raw or "").strip()
    if not text:
        return ""

    match = re.match(r"([A-Z]{2,4})\s*(\d+)", text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    # A bare, real department code is legitimate; anything else is a placeholder.
    return text.upper() if text.upper() in bis.BY_CODE else ""


def _sector(department_name: str, committee: str) -> str:
    """'PRODUCTION AND GENERAL ENGINEERING DEPARTMENT (PGD)' -> our sector name.

    Resolved via the department code so the corpus uses one consistent set of
    sector names — the ones in `bis_reference.DEPARTMENTS` — rather than the
    portal's shouty display strings. Returns "" when the portal itself has no
    department for the record, which the UI reports as Unclassified.
    """
    match = re.search(r"\(([A-Z]{2,4})\)", department_name or "")
    code = match.group(1) if match else (committee.split()[0] if committee else "")
    department = bis.BY_CODE.get(code.upper())
    if department:
        return department.name

    cleaned = re.sub(r"\s*\([A-Z]{2,4}\)\s*$", "", department_name or "").strip()
    # Strip placeholder dashes rather than letting them become a "sector".
    if not cleaned or not re.search(r"[A-Za-z]", cleaned):
        return ""
    return cleaned.title().replace(" Department", "")


def _year(published_on: str, is_number: str) -> int | None:
    for source in (published_on, is_number):
        match = re.search(r"(19|20)\d{2}", str(source or ""))
        if match:
            return int(match.group())
    return None


# The portal's list mixes back issues of the BIS house magazine *Standards
# India* in with the standards themselves ("SI B2410:2011 — Standards India Vol.
# 24 No. 10"). They are not standards, they have no department, and their
# magazine-article titles are broad enough to match almost anything: one of them
# was the top hit for "our MSME assembles LED bulbs and power adapters". Indexing
# them measurably raises the retrieval noise floor, so they are dropped.
_NOT_A_STANDARD = re.compile(r"^SI\s+B?\d", re.IGNORECASE)


def apply_taxonomy(
    standards: list[Standard], rows: list[dict[str, Any]], mapping: dict[str, dict[str, str]]
) -> int:
    """Overlay the BIS subject taxonomy, joined on the portal's `standardId`.

    The catalogue list and the sector browse are two views of the same records,
    and `standardId` is the only field common to both — IS numbers are written
    inconsistently enough across the portal that joining on them loses records.
    """
    by_number = {s.is_number: s for s in standards}
    id_to_number = {
        str(row.get("standardId")): (row.get("standardNumber") or "").strip()
        for row in rows
        if row.get("standardId") is not None
    }

    applied = 0
    for standard_id, labels in mapping.items():
        number = id_to_number.get(standard_id)
        if not number:
            continue
        standard = by_number.get(number)
        if standard is None:
            continue
        standard.bis_sector = labels.get("sector", "") or standard.bis_sector
        standard.bis_subsector = labels.get("subsector", "") or standard.bis_subsector
        applied += 1
    return applied


def to_standard(row: dict[str, Any]) -> Standard | None:
    """Map one API record onto our schema. None when it has no usable identity."""
    is_number = (row.get("standardNumber") or "").strip()
    title = (row.get("standardName") or "").strip()
    if not is_number or not title:
        return None
    if _NOT_A_STANDARD.match(is_number):
        return None

    committee = _committee(row.get("sectionalCommitteeName") or "")
    return Standard(
        is_number=is_number,
        # Portal titles are inconsistently cased ("SPECIFICATION FOR SCISSORS").
        # Leave them as published — normalising risks mangling IS/ISO names —
        # but they are what the embedding sees, so it matters that they are
        # descriptive, which they are.
        title=title,
        scope="",
        sector=_sector(row.get("departmentName") or "", committee),
        technical_committee=committee,
        status="active",
        year=_year(row.get("publishedOn") or "", is_number),
        # The portal exposes no scope text, so the type of standard is the only
        # extra retrieval signal available. It is genuinely useful: "Product
        # Specification" vs "Methods of Test" vs "Code of Practice".
        keywords=[k for k in [(row.get("typeOfStandardName") or "").strip()] if k],
        verification="unverified",
    )


def _edition_key(is_number: str) -> str:
    """Identity of a standard ignoring its year: 'IS 1077:1992' -> 'IS1077'.

    Parts are part of the identity — IS 2062 (Part 1) and IS 2062 (Part 2) are
    different standards — but the year is not, because that is the thing we
    want to let the portal correct.
    """
    without_year = re.split(r"\s*:\s*(?:19|20)\d{2}\s*$", is_number.strip())[0]
    return re.sub(r"\s+", "", without_year).upper()


def _overlay(base: Standard, curated: Standard) -> tuple[Standard, bool]:
    """Copy curated depth onto a portal record."""
    data = base.model_dump()
    source = curated.model_dump()
    changed = False
    for field in _CURATED_FIELDS:
        value = source.get(field)
        if value not in (None, "", [], 0, False):
            data[field] = value
            changed = True
    # The curated title and scope were written to work together, so keep the
    # curated title wherever we have curated scope.
    if source.get("scope"):
        data["title"] = curated.title
    return Standard.model_validate(data), changed


def merge_with_curated(
    collected: list[Standard], curated: list[Standard]
) -> tuple[list[Standard], dict[str, list[str]]]:
    """Overlay curated depth onto collected breadth.

    Matching is by *edition key* — the IS number without its year — not by the
    exact string. That matters because the portal is authoritative about which
    edition is current and several hand-authored years turned out to be stale:
    the curated corpus had IS 1077:1992 where the portal publishes IS 1077:2025.
    Matching on the exact string would have kept both, leaving two records for
    one standard in every search result.

    So on a year mismatch the portal's number wins, the curated scope/QCO/graph
    data is carried onto it, and the superseded number is recorded in
    `supersedes` rather than thrown away.

    Returns the merged corpus and a report of what happened, for the operator to
    look at — silent corpus surgery is how bad data survives.
    """
    by_number = {s.is_number: s for s in collected}
    by_edition = {_edition_key(s.is_number): s for s in collected}
    report: dict[str, list[str]] = {"enriched": [], "reyeared": [], "unmatched": []}

    for record in curated:
        exact = by_number.get(record.is_number)
        if exact is not None:
            merged, changed = _overlay(exact, record)
            by_number[record.is_number] = merged
            if changed:
                report["enriched"].append(record.is_number)
            continue

        current = by_edition.get(_edition_key(record.is_number))
        if current is not None:
            merged, _ = _overlay(current, record)
            # Keep the edition we are replacing in the version lineage.
            lineage = list(dict.fromkeys([*merged.supersedes, record.is_number]))
            merged = merged.model_copy(update={"supersedes": lineage})
            by_number[current.is_number] = merged
            report["reyeared"].append(f"{record.is_number} -> {current.is_number}")
            continue

        # The portal does not publish this number in any edition. It may be
        # withdrawn, or merged into another standard (IS 8112 and IS 12269 were
        # both absorbed by IS 269:2015). Keep it — it still carries curated
        # depth — but say so, because it is a verification lead.
        by_number[record.is_number] = record
        report["unmatched"].append(record.is_number)

    return sorted(by_number.values(), key=lambda s: s.is_number), report


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect the published BIS catalogue.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum records to fetch.")
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Skip the network and re-merge cached pages in data/raw/.",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Write the collected records alone, discarding curated scope/QCO data.",
    )
    args = parser.parse_args()

    settings = get_settings()
    print(f"Source: {API_URL}")
    rows = load_cached_pages() if args.from_cache else fetch_pages(limit=args.limit)
    if not rows:
        raise SystemExit("No records collected — nothing written.")

    collected = [s for s in (to_standard(row) for row in rows) if s is not None]
    # The API can repeat a standard across amendment rows; keep one per number.
    collected = list({s.is_number: s for s in collected}.values())

    # Subject classification, if `python -m app.ingestion.taxonomy` has run.
    taxonomy = taxonomy_module.load()
    if taxonomy:
        classified = apply_taxonomy(collected, rows, taxonomy)
        print(f"  applied BIS subject taxonomy to {classified} records")
    else:
        print("  no taxonomy.json — run `python -m app.ingestion.taxonomy` for "
              "sector/sub-sector classification")

    if args.no_merge:
        merged = sorted(collected, key=lambda s: s.is_number)
    else:
        curated = load_jsonl(settings.seed_corpus)
        merged, report = merge_with_curated(collected, curated)
        print(f"\n  merged {len(curated)} curated records:")
        print(f"    {len(report['enriched']):>3} matched exactly and kept their curated depth")
        print(f"    {len(report['reyeared']):>3} had a stale year, corrected from the portal:")
        for line in report["reyeared"]:
            print(f"          {line}")
        print(f"    {len(report['unmatched']):>3} are not published in any edition on the portal")
        print("          (withdrawn, or absorbed into another standard — verify these):")
        for number in report["unmatched"]:
            print(f"          {number}")

    write_jsonl(merged, settings.processed_corpus)

    departments = {s.department_code() for s in merged if s.department_code()}
    with_scope = sum(1 for s in merged if s.scope)
    mandatory = sum(1 for s in merged if s.qco_mandatory)

    print(f"\n{len(rows)} raw rows -> {len(merged)} unique standards")
    print(f"  departments covered : {len(departments)} of {len(bis.DEPARTMENTS)}")
    print(f"  with scope text     : {with_scope}")
    print(f"  with BIS subject    : {sum(1 for s in merged if s.bis_sector)}")
    print(f"  under a QCO         : {mandatory}")
    print(f"\nWritten to {settings.processed_corpus}")
    print("\nNext:")
    print("  python -m app.ingestion.build_index --rebuild")
    print("  python -m app.ingestion.calibrate      # floors move at this scale")


if __name__ == "__main__":
    main()
