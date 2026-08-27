"""Turn an uploaded tender PDF into analysable line items.

Extracting the text is the easy 10%. The problem is that a PDF's text has
*visual* lines, not *logical* ones: a single tender clause wraps across three
lines, headers and footers repeat on every page, and BOQ tables arrive as one
line per cell row. Feeding that straight into the analyser produces a "line
item" like `"3 Electrotechnical Department (ETD) 1954"` and cheerfully matches
three standards to it.

So this module reflows before it segments:

1. Extract per page, keeping page numbers — provenance in a 40-page tender has
   to be "page 14, item 4.2", not "line 812".
2. Drop furniture: lines that repeat on most pages (running headers/footers),
   bare page numbers, dot-leader table-of-contents rows.
3. Rejoin wrapped lines onto the clause they belong to, using the document's own
   numbering scheme as the boundary signal.
4. Drop what is left that is a heading or a table row rather than a requirement.

All deterministic and offline — no model call — because the spec analyser has to
work with no API key, same as everything else here.

Scanned PDFs have no text layer at all. They are detected and reported rather
than silently returning an empty analysis, which would look like a clean
document. Real OCR needs a system Tesseract install and is deliberately out of
scope; see the README.
"""

import io
import re
from collections import Counter
from dataclasses import dataclass

# Uploads are capped well below anything that would strain the process. A tender
# larger than this is almost always a scanned bundle, which we cannot read anyway.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PAGES = 120

# Below this many characters per page, on average, there is no usable text layer.
_SCANNED_CHARS_PER_PAGE = 60


class PdfError(Exception):
    """Raised for a PDF we cannot or should not read. Message is user-facing."""


@dataclass
class Line:
    """One logical line item, with where it came from."""

    page: int
    line_no: int  # 1-based within the whole document, after reflow
    text: str


@dataclass
class ParsedPdf:
    pages: int
    text: str
    lines: list[Line]
    truncated: bool = False


# A clause opener: "4.", "4.2", "4.2.1", "(a)", "iv)", "Item 12", "Clause 7".
#
# The trailing punctuation on a bare number is REQUIRED. Without it, every
# statistics-table row ("1 Service Sector Department (SSD) 163") opens a new
# "clause", and the analyser then matches standards to table cells. A
# multi-level number ("4.2") is unambiguous enough to stand without it.
_CLAUSE_START = re.compile(
    r"""^\s*(?:
        (?:clause|item|para(?:graph)?|sl\.?\s*no\.?)\s*[.:]?\s*\d+   # Clause 7
      | \(?[ivxlc]{1,5}[.)]                                          # (iv)
      | \(?[a-z][.)]                                                 # (a)
      | \d{1,3}(?:\.\d{1,3}){1,3}[.)]?                               # 4.2 / 4.2.1
      | \d{1,3}[.)]                                                  # 4. / 4)
      | [-*•–—]                                                      # bullets
    )\s+""",
    re.IGNORECASE | re.VERBOSE,
)

# Strip that opener once we have used it as a boundary signal. Mirrors
# _CLAUSE_START exactly — if the two drift apart, numbering survives into the
# retrieval query as noise ("1.1 Construction of...").
_CLAUSE_PREFIX = re.compile(
    r"""^\s*(?:
        (?:clause|item|para(?:graph)?|sl\.?\s*no\.?)\s*[.:]?\s*\d+[.):]?
      | \(?[ivxlc]{1,5}[.)]
      | \(?[a-z][.)]
      | \d{1,3}(?:\.\d{1,3}){1,3}[.)]?
      | \d{1,3}[.)]
      | [-*•–—]
    )\s+""",
    re.IGNORECASE | re.VERBOSE,
)

# Column headings of a BOQ / schedule-of-rates table.
_TABLE_HEADING = re.compile(
    r"^(?:sl\.?\s*no|s\.?\s*no|item\s*(?:no|code)?|description|qty|quantity|"
    r"rate|unit|amount|particulars)\b",
    re.IGNORECASE,
)

_PAGE_NUMBER = re.compile(r"^\s*(?:page\s*)?\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?\s*$", re.I)
_DOT_LEADER = re.compile(r"\.{4,}\s*\d{1,4}\s*$")  # "Scope ......... 12"

# A row of mostly numbers and short tokens — a BOQ/summary table, not a clause.
_TABLE_ROW = re.compile(r"^[\W\d]*(?:\S+\s+){0,3}\d[\d.,%]*\s*$")

# Standalone numeric tokens, ignoring any that belong to an IS reference — a
# line citing "IS 456:2000" is the most valuable kind of line here.
_IS_REF = re.compile(r"\bIS(?:/(?:ISO|IEC))?\s*\d[\d\s():/]*", re.IGNORECASE)
_NUMERIC_TOKEN = re.compile(r"(?<![\w.])\d[\d,.]*(?![\w])")

def _is_heading(text: str) -> bool:
    """A section heading rather than a requirement.

    Indian tender documents head their sections in capitals — "2. MATERIALS AND
    WORKMANSHIP". Those survive prefix-stripping as respectable-looking line
    items and then match a standard on a stray keyword: the heading above
    retrieved a *refractory test-piece preparation* standard.

    Only all-caps is treated as a heading. Title Case is too common in ordinary
    requirement text to use as a signal without dropping real line items.
    """
    if len(text) > 70 or text.endswith((".", ";", "?", "!")):
        return False
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return False
    return sum(c.isupper() for c in letters) / len(letters) > 0.8


# Lines shorter than this carry no retrievable signal.
_MIN_LINE_CHARS = 15
# Longer than this and it is a merged paragraph; the embedding turns to mush.
_MAX_LINE_CHARS = 400


def _is_table_row(line: str) -> bool:
    """A tabulated data row rather than a requirement.

    Tenders and BIS documents both carry tables that survive extraction as
    "label ... number" lines. They read as prose to a regex but carry no
    requirement, and matching standards against them is pure noise.

    The test: ends in a bare number, holds two or more numbers, and has no
    sentence-ending punctuation. "1 Service Sector Department (SSD) 163" is
    caught; "Concrete work shall conform to IS 456:2000." is not.
    """
    if line.endswith((".", ";", ":", "?", "!")):
        return False
    stripped = _IS_REF.sub(" ", line)
    if not re.search(r"\d\s*$", stripped):
        return False
    return len(_NUMERIC_TOKEN.findall(stripped)) >= 2



def extract_pages(data: bytes) -> list[str]:
    """Raw text per page. Raises `PdfError` with something a user can act on."""
    if not data:
        raise PdfError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise PdfError(
            f"That PDF is {len(data) / 1e6:.1f} MB. The limit is "
            f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB — paste the relevant section instead."
        )
    if not data.lstrip()[:5].startswith(b"%PDF"):
        raise PdfError("That file is not a PDF.")

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise PdfError("PDF support is not installed on the server.") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # An empty user password is common and harmless to try.
            try:
                reader.decrypt("")
            except Exception:
                raise PdfError("That PDF is password-protected. Remove the password and retry.")
        return [(page.extract_text() or "") for page in reader.pages[:MAX_PAGES]]
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError(f"That PDF could not be read ({type(exc).__name__}).") from exc


def _furniture(pages: list[str]) -> set[str]:
    """Lines repeating across most pages — running headers and footers."""
    # Two pages is enough to spot a running header; below that there is no
    # repetition to measure.
    if len(pages) < 2:
        return set()
    seen = Counter()
    for page in pages:
        # Count each distinct line once per page, so a word repeated within one
        # page does not look like a header.
        for line in {ln.strip() for ln in page.splitlines() if ln.strip()}:
            seen[line] += 1
    threshold = max(2, int(len(pages) * 0.5))
    return {line for line, count in seen.items() if count >= threshold}


def _is_noise(line: str, furniture: set[str]) -> bool:
    if line in furniture:
        return True
    if _PAGE_NUMBER.match(line):
        return True
    if _DOT_LEADER.search(line):
        return True
    if _TABLE_ROW.match(line) or _is_table_row(line):
        return True
    if _TABLE_HEADING.match(line) and len(line) < 80:
        return True
    # Mostly punctuation or digits: rule lines, table borders, page furniture.
    letters = sum(ch.isalpha() for ch in line)
    return letters < max(6, len(line) * 0.35)


def reflow(pages: list[str], limit: int) -> tuple[list[Line], bool]:
    """Rejoin wrapped text into logical line items, keeping page provenance.

    A new item starts at a clause marker; anything else continues the previous
    one. When a document has no numbering at all, each non-empty line stands on
    its own — which is exactly how a pasted plain-text spec already behaved.
    """
    furniture = _furniture(pages)
    items: list[Line] = []
    buffer = ""
    buffer_page = 1

    def flush() -> None:
        nonlocal buffer
        text = re.sub(r"\s+", " ", buffer).strip()
        buffer = ""
        if len(text) < _MIN_LINE_CHARS or _is_heading(text):
            return
        items.append(Line(page=buffer_page, line_no=len(items) + 1, text=text[:_MAX_LINE_CHARS]))

    for page_number, page in enumerate(pages, start=1):
        for raw in page.splitlines():
            line = raw.strip()
            if not line or _is_noise(line, furniture):
                continue

            starts_clause = bool(_CLAUSE_START.match(line))
            # A clause that already ends in sentence punctuation is finished.
            # Without this, the next page's running header — or a table heading
            # the furniture filter missed — gets glued onto the end of it.
            complete = buffer.rstrip().endswith((".", ";", "?", "!"))
            if starts_clause or complete or not buffer:
                flush()
                if len(items) >= limit:
                    return items, True
                buffer_page = page_number
                buffer = _CLAUSE_PREFIX.sub("", line, count=1)
            else:
                buffer = f"{buffer} {line}"
                # A merged paragraph this long has stopped being one requirement.
                if len(buffer) > _MAX_LINE_CHARS:
                    flush()
                    if len(items) >= limit:
                        return items, True

    flush()
    return items[:limit], len(items) > limit


def is_scanned(pages: list[str]) -> bool:
    """True when the PDF carries no usable text layer.

    An image-only PDF extracts to almost nothing. Detecting that is what lets
    us say "this is a scan" instead of returning an empty analysis, which would
    read as "your document is clean".
    """
    if not pages:
        return True
    return sum(len(p.strip()) for p in pages) / len(pages) < _SCANNED_CHARS_PER_PAGE


def parse(data: bytes, limit: int) -> ParsedPdf:
    """Full pipeline: bytes -> logical line items."""
    pages = extract_pages(data)
    if not pages:
        raise PdfError("That PDF has no pages.")

    if is_scanned(pages):
        raise PdfError(
            "This PDF has no text layer — it looks like a scan or an image. "
            "Paste the specification text instead, or supply a digital PDF. "
            "(Optical character recognition is not enabled on this deployment.)"
        )

    lines, truncated = reflow(pages, limit)
    if not lines:
        raise PdfError("No specification line items could be read from that PDF.")

    return ParsedPdf(
        pages=len(pages),
        text="\n".join(pages),
        lines=lines,
        truncated=truncated,
    )
