"""Collect the BIS sector / sub-sector taxonomy and map every standard onto it.

This is the classification the main catalogue API does not give you. On
`standards.bis.gov.in/website/catalogue-list` each sector's "No. of Standards"
is a hyperlink; the Excel exports of that page drop the link and keep only the
counts. This module rebuilds what the link leads to.

Two endpoints, both on the same proposal-service host as the catalogue itself:

    POST getSectorsWithSubSectorsAndCounts   {"mode": "sector"|"subsector", ...}
        -> 210 sectors, or 1,009 sector/sub-sector pairs, each with an
           *encrypted* id and a standards count.

    POST getStandardsBySectorId  {"sectorId", "subSectorId", "mode", page, pageSize}
        -> the standards in that bucket, carrying `standardId`, `sectorName`
           and `subSectorName`.

`standardId` is the join key back to the records `collector.py` already holds.

**Why both modes.** They are disjoint views, not nested ones. Sector mode
reaches 2,889 standards (the ones filed directly against a sector) and
sub-sector mode reaches ~17,431 (those filed against a sub-sector). Crawling
only one leaves most of the catalogue unclassified, which is why both run here.

Output: `data/processed/taxonomy.json`, a `{standardId: {sector, subsector}}`
map that `collector.py` overlays onto the corpus.

Usage:
    python -m app.ingestion.taxonomy              # crawl and write the map
    python -m app.ingestion.taxonomy --sectors-only   # quick partial run
"""

import argparse
import json
import time
from typing import Any

import httpx

from app.config import get_settings
from app.ingestion.collector import HEADERS, REQUEST_DELAY_SECONDS

BASE = "https://standardsadmin.bis.gov.in/proposal-service/"
BUCKETS_URL = BASE + "getSectorsWithSubSectorsAndCounts"
STANDARDS_URL = BASE + "getStandardsBySectorId"

# This endpoint honours larger pages than the catalogue list does, and the
# biggest bucket holds ~200 standards, so one request per bucket is the norm.
PAGE_SIZE = 500
BUCKET_PAGE = 200


def _post(client: httpx.Client, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def fetch_buckets(client: httpx.Client, mode: str) -> list[dict[str, Any]]:
    """Every sector (mode='sector') or sector/sub-sector pair (mode='subsector')."""
    key = "sectorWise" if mode == "sector" else "subsectorWise"
    buckets: list[dict[str, Any]] = []
    offset = 0

    while True:
        payload = {
            "mode": mode,
            "offset": offset,
            "limit": BUCKET_PAGE,
            "searchTerm": "",
            "sectorIds": [],
        }
        data = _post(client, BUCKETS_URL, payload).get("data") or {}
        page = data.get(key) or []
        if not page:
            break
        buckets.extend(page)
        if len(page) < BUCKET_PAGE:
            break
        offset += BUCKET_PAGE
        time.sleep(REQUEST_DELAY_SECONDS)

    return buckets


def fetch_bucket_standards(
    client: httpx.Client, bucket: dict[str, Any], mode: str
) -> list[dict[str, Any]]:
    """Standards inside one sector or sub-sector, following pagination."""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = {
            "sectorId": bucket.get("sectorId"),
            "subSectorId": bucket.get("subSectorId") if mode == "subsector" else None,
            "mode": mode,
            "page": page,
            "pageSize": PAGE_SIZE,
        }
        try:
            body = _post(client, STANDARDS_URL, payload)
        except (httpx.HTTPError, ValueError):
            # One unreachable bucket must not abandon the other thousand.
            return rows

        batch = body.get("data") or []
        rows.extend(batch)
        total = body.get("totalRecord") or 0
        if len(rows) >= total or not batch:
            break
        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)
    return rows


def crawl(sectors_only: bool = False) -> dict[str, dict[str, str]]:
    """Build `{standardId: {"sector": ..., "subsector": ...}}` for the catalogue."""
    mapping: dict[str, dict[str, str]] = {}

    with httpx.Client(headers=HEADERS, timeout=90.0, follow_redirects=True) as client:
        modes = ["sector"] if sectors_only else ["sector", "subsector"]
        for mode in modes:
            buckets = fetch_buckets(client, mode)
            print(f"  {mode}: {len(buckets)} buckets")

            for index, bucket in enumerate(buckets, start=1):
                for row in fetch_bucket_standards(client, bucket, mode):
                    standard_id = row.get("standardId")
                    if standard_id is None:
                        continue
                    entry = mapping.setdefault(str(standard_id), {})
                    # Sub-sector mode carries the richer label, so let it win.
                    sector = (row.get("sectorName") or "").strip()
                    subsector = (row.get("subSectorName") or "").strip()
                    if sector:
                        entry["sector"] = sector
                    if subsector:
                        entry["subsector"] = subsector

                if index % 100 == 0 or index == len(buckets):
                    print(f"    {index}/{len(buckets)} buckets, {len(mapping)} standards mapped")
                time.sleep(REQUEST_DELAY_SECONDS)

    return mapping


def load() -> dict[str, dict[str, str]]:
    """Read the cached taxonomy map, or an empty map when it has not been built."""
    path = get_settings().processed_corpus.parent / "taxonomy.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sectors-only",
        action="store_true",
        help="Crawl sector buckets only — faster, but reaches ~12%% of the catalogue.",
    )
    args = parser.parse_args()

    settings = get_settings()
    path = settings.processed_corpus.parent / "taxonomy.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Source: {BUCKETS_URL}")
    mapping = crawl(sectors_only=args.sectors_only)
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    sectors = {v.get("sector") for v in mapping.values() if v.get("sector")}
    subsectors = {v.get("subsector") for v in mapping.values() if v.get("subsector")}
    with_sub = sum(1 for v in mapping.values() if v.get("subsector"))

    print(f"\n{len(mapping)} standards classified")
    print(f"  distinct sectors     : {len(sectors)}")
    print(f"  distinct sub-sectors : {len(subsectors)}")
    print(f"  with a sub-sector    : {with_sub}")
    print(f"\nWritten to {path}")
    print("\nNext:")
    print("  python -m app.ingestion.collector --from-cache")
    print("  python -m app.ingestion.build_index --rebuild")
    print("  python -m app.ingestion.calibrate")


if __name__ == "__main__":
    main()
