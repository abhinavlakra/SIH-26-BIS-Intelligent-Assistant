"""Normalize heterogeneous catalogue rows into the `Standard` schema.

Public BIS catalogue exports use inconsistent column names across sources, so
field lookup is alias-based rather than positional.
"""

import json
import re
from pathlib import Path
from typing import Any, Iterable

from app.models import Standard

_ALIASES: dict[str, tuple[str, ...]] = {
    "is_number": ("is_number", "is_no", "standard_no", "standard_number", "isno", "id"),
    "title": ("title", "standard_title", "name", "subject"),
    "scope": ("scope", "abstract", "description", "summary"),
    "sector": ("sector", "division", "department", "subject_group"),
    "technical_committee": ("technical_committee", "committee", "tc", "sectional_committee"),
    "status": ("status", "standard_status"),
    "year": ("year", "year_of_publication", "published", "publication_year"),
    "ics_codes": ("ics_codes", "ics", "ics_code", "classification"),
    "keywords": ("keywords", "keyword", "tags"),
    "normative_refs": ("normative_refs", "normative_references", "references", "refers"),
    "test_methods": ("test_methods", "test_method", "methods_of_test"),
    "supersedes": ("supersedes", "replaces", "supersedes_is"),
    "superseded_by": ("superseded_by", "replaced_by", "revised_by"),
    "amendment_count": ("amendment_count", "no_of_amendments", "amendments", "amds"),
    "qco_name": ("qco_name", "qco", "quality_control_order"),
    "certification_scheme": ("certification_scheme", "scheme"),
}


def _pick(row: dict[str, Any], field: str) -> Any:
    lowered = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}
    for alias in _ALIASES[field]:
        if lowered.get(alias) not in (None, ""):
            return lowered[alias]
    return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in re.split(r"[;,|]", str(value)) if part.strip()]


def _as_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group()) if match else None


def _as_status(value: Any) -> str:
    text = str(value or "active").strip().lower()
    if "withdraw" in text:
        return "withdrawn"
    if "supersed" in text or "revis" in text:
        return "superseded"
    return "active"


def _as_int(value: Any) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else 0


def _as_scheme(value: Any) -> str | None:
    """Map free-text scheme names onto our scheme keys."""
    text = str(value or "").strip().lower()
    if not text:
        return None
    if "hallmark" in text:
        return "hallmarking"
    if "crs" in text or "registration" in text or "scheme ii" in text:
        return "crs"
    if "fmcs" in text or "foreign" in text:
        return "fmcs"
    if "scheme x" in text or "omnibus" in text:
        return "scheme_x"
    if "eco" in text:
        return "eco_mark"
    if "isi" in text or "scheme i" in text or "product certification" in text:
        return "scheme_i"
    return None


def normalize_row(row: dict[str, Any]) -> Standard | None:
    """Convert one raw catalogue row; returns None if it has no usable identity."""
    is_number = _pick(row, "is_number")
    title = _pick(row, "title")
    if not is_number or not title:
        return None

    qco_name = str(_pick(row, "qco_name") or "").strip()

    return Standard(
        is_number=str(is_number).strip(),
        title=str(title).strip(),
        scope=str(_pick(row, "scope") or "").strip(),
        ics_codes=_as_list(_pick(row, "ics_codes")),
        sector=str(_pick(row, "sector") or "").strip(),
        technical_committee=str(_pick(row, "technical_committee") or "").strip(),
        status=_as_status(_pick(row, "status")),
        year=_as_year(_pick(row, "year")) or _as_year(is_number),
        keywords=_as_list(_pick(row, "keywords")),
        # A QCO name in the source is itself the evidence that it is mandatory.
        qco_mandatory=bool(qco_name),
        qco_name=qco_name,
        certification_scheme=_as_scheme(_pick(row, "certification_scheme")),
        normative_refs=_as_list(_pick(row, "normative_refs")),
        test_methods=_as_list(_pick(row, "test_methods")),
        supersedes=_as_list(_pick(row, "supersedes")),
        superseded_by=str(_pick(row, "superseded_by") or "").strip(),
        amendment_count=_as_int(_pick(row, "amendment_count")),
    )


def normalize_rows(rows: Iterable[dict[str, Any]]) -> list[Standard]:
    """Normalize and de-duplicate by IS number, keeping the richest entry."""
    best: dict[str, Standard] = {}
    for row in rows:
        standard = normalize_row(row)
        if standard is None:
            continue
        existing = best.get(standard.is_number)
        if existing is None or len(standard.scope) > len(existing.scope):
            best[standard.is_number] = standard
    return sorted(best.values(), key=lambda s: s.is_number)


def load_jsonl(path: Path) -> list[Standard]:
    """Read a corpus file written in JSON Lines format."""
    standards: list[Standard] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                standards.append(Standard.model_validate(json.loads(line)))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number} is not a valid Standard: {exc}") from exc
    return standards


def write_jsonl(standards: list[Standard], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for standard in standards:
            handle.write(json.dumps(standard.model_dump(), ensure_ascii=False) + "\n")
