"""PDF tender ingestion: extraction limits and the reflow heuristics.

The reflow tests operate on page *text* rather than real PDF bytes, because the
thing under test is the segmentation, not pypdf. Every fixture below is shaped
like genuine pypdf output — wrapped clauses, running headers, page numbers and
a schedule-of-rates table.
"""

import pytest

from app.services import pdfdoc

TENDER_PAGES = [
    """Municipal Corporation of Pune
Tender No. MCP/2026/CIV/114
1. SCOPE OF WORK
1.1 Construction of a four-storey reinforced concrete office
building including all civil, electrical and plumbing works
at the Kothrud ward office site.
1.2 Concrete work shall conform to IS 456:2000 throughout
the structure.
Page 1 of 3""",
    """Municipal Corporation of Pune
Tender No. MCP/2026/CIV/114
2. MATERIALS
2.1 Seismic design of the frame shall follow IS 1893:2002 and
ductile detailing as per IS 13920.
Sl No Item Qty Rate
1 Cement OPC 53 grade 420 385
2 TMT reinforcement bars 68 62500
2.2 All structural steelwork to be hot rolled medium tensile
steel of approved make.
Page 2 of 3""",
]


def _texts(pages, limit=120):
    lines, _ = pdfdoc.reflow(pages, limit)
    return [line.text for line in lines]


def test_wrapped_clause_is_rejoined_into_one_line_item():
    """A clause spanning three visual lines must become one retrieval query."""
    texts = _texts(TENDER_PAGES)
    assert any(
        "four-storey reinforced concrete office building" in t
        and "Kothrud ward office site" in t
        for t in texts
    ), texts


def test_clause_numbering_is_stripped():
    # "1.1 Construction of..." would otherwise carry the numbering into the
    # embedding, where it is pure noise.
    assert all(not t[0].isdigit() for t in _texts(TENDER_PAGES))


def test_running_headers_and_page_numbers_are_dropped():
    texts = _texts(TENDER_PAGES)
    assert not any("Municipal Corporation of Pune" in t for t in texts)
    assert not any("Page 1 of 3" in t for t in texts)


def test_schedule_of_rates_rows_are_dropped():
    """BOQ rows read as prose but carry no requirement."""
    texts = _texts(TENDER_PAGES)
    assert not any("420 385" in t for t in texts)
    assert not any(t.startswith("Cement OPC") for t in texts)
    assert not any("Sl No Item Qty Rate" in t for t in texts)


def test_completed_clause_does_not_absorb_the_next_heading():
    """A clause ending in a full stop is finished.

    Without this the next page's header glues onto the end of it, which is how
    'the structure. Municipal Corporation of Pune' happens.
    """
    texts = _texts(TENDER_PAGES)
    concrete = [t for t in texts if "IS 456:2000" in t]
    assert concrete, texts
    assert concrete[0].endswith("throughout the structure.")


def test_page_provenance_is_preserved():
    lines, _ = pdfdoc.reflow(TENDER_PAGES, 120)
    by_page = {line.page for line in lines}
    assert by_page == {1, 2}
    seismic = next(line for line in lines if "IS 1893" in line.text)
    assert seismic.page == 2


def test_citations_survive_reflow():
    """The whole point: an IS number split across a wrap must still be found."""
    joined = "\n".join(_texts(TENDER_PAGES))
    from app.services.spec import extract_citations

    cited = extract_citations(joined)
    assert "IS 456:2000" in cited
    assert "IS 1893:2002" in cited
    assert "IS 13920" in cited


def test_limit_is_respected_and_reported():
    lines, truncated = pdfdoc.reflow(TENDER_PAGES, 2)
    assert len(lines) == 2
    assert truncated is True


def test_unnumbered_document_keeps_one_item_per_line():
    """A spec with no numbering should behave as the pasted-text path does."""
    pages = [
        "Supply of galvanized steel sheets for roofing work.\n"
        "Installation of internal electrical wiring throughout.\n"
        "Provision of packaged drinking water at the site office."
    ]
    assert len(_texts(pages)) == 3


def test_rejects_a_file_that_is_not_a_pdf():
    with pytest.raises(pdfdoc.PdfError, match="not a PDF"):
        pdfdoc.extract_pages(b"PK\x03\x04 this is a zip")


def test_rejects_an_empty_upload():
    with pytest.raises(pdfdoc.PdfError, match="empty"):
        pdfdoc.extract_pages(b"")


def test_rejects_an_oversized_upload():
    oversized = b"%PDF-1.4" + b"\0" * (pdfdoc.MAX_UPLOAD_BYTES + 1)
    with pytest.raises(pdfdoc.PdfError, match="limit is"):
        pdfdoc.extract_pages(oversized)


def test_scanned_pdf_is_detected():
    """An image-only PDF extracts to almost nothing and must be reported.

    Returning an empty analysis instead would read as "your document is clean",
    which is the worst possible answer for a tender that was never parsed.
    """
    assert pdfdoc.is_scanned(["", "  ", "\n"]) is True
    assert pdfdoc.is_scanned([]) is True


def test_a_real_text_layer_is_not_mistaken_for_a_scan():
    assert pdfdoc.is_scanned(TENDER_PAGES) is False


def test_upload_endpoint_rejects_a_non_pdf_with_a_readable_message():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/analyze-spec/upload",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
    )
    assert response.status_code == 422
    assert "not a PDF" in response.json()["detail"]


def test_upload_endpoint_analyses_a_real_pdf(tmp_path):
    """End-to-end: real PDF bytes in, per-line standards out."""
    pytest.importorskip("reportlab", reason="needs a PDF writer to build a fixture")
    from fastapi.testclient import TestClient
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from app.main import app

    path = tmp_path / "tender.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for line in TENDER_PAGES[0].splitlines():
        pdf.drawString(60, y, line)
        y -= 16
    pdf.save()

    client = TestClient(app)
    response = client.post(
        "/api/analyze-spec/upload",
        files={"file": ("tender.pdf", path.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"]["kind"] == "pdf"
    assert body["source"]["filename"] == "tender.pdf"
    assert body["source"]["pages"] == 1
    assert body["line_count"] >= 2
    assert all(line["page"] == 1 for line in body["lines"])
    assert any(c["cited_as"] == "IS 456:2000" for c in body["cited_standards"])


def test_all_caps_section_headings_are_dropped():
    """A heading matched to a standard is worse than no match at all.

    "2. MATERIALS AND WORKMANSHIP" survived prefix-stripping and retrieved a
    refractory test-piece standard on a stray keyword.
    """
    pages = [
        "2. MATERIALS AND WORKMANSHIP\n"
        "2.1 All structural steelwork to be hot rolled medium tensile steel."
    ]
    texts = _texts(pages)
    assert not any("MATERIALS AND WORKMANSHIP" in t for t in texts), texts
    assert any("hot rolled medium tensile steel" in t for t in texts)


def test_ordinary_requirement_text_is_not_mistaken_for_a_heading():
    assert pdfdoc._is_heading("Concrete work shall conform to IS 456:2000.") is False
    assert pdfdoc._is_heading("Supply of TMT bars to the site store") is False
    assert pdfdoc._is_heading("SCOPE OF WORK") is True
