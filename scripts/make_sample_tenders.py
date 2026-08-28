"""Generate the sample tender PDFs used to demo and test the tender checker.

Each document is built to make one thing happen, so a demo can move through
them deliberately rather than hoping a single file shows everything:

    01-building-rcc         outdated citations + missing normative references
    02-electrical-substation mandatory certification, CRS and ISI together
    03-water-supply         mandatory packaged-water standards
    04-well-specified       a *good* tender — high completeness, for contrast
    05-no-citations         a tender citing nothing; recommendations still land
    06-messy-boq            the reflow stress test: tables, headers, mixed numbering
    07-scanned              no text layer, to show the refusal path

Run from the project root:

    python scripts/make_sample_tenders.py

Output: samples/tenders/*.pdf  (committed — they are demo fixtures, not data)
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT_DIR = Path(__file__).resolve().parent.parent / "samples" / "tenders"

LEFT = 56
TOP = 790
LEADING = 15.5
BODY_SIZE = 10
MONO = "Helvetica"


# --- the documents ---------------------------------------------------------
#
# Written as page-strings so the line breaks are the ones a real extractor
# would see: clauses wrap mid-sentence, headings sit on their own line, and
# running headers/footers repeat. That is the input the reflow has to survive.

BUILDING_RCC = [
    """Municipal Corporation of Pune
Tender No. MCP/2026/CIV/114 - Ward Office Building
1. SCOPE OF WORK
1.1 Construction of a four-storey reinforced concrete office
building including all civil, electrical and plumbing works at
the Kothrud ward office site.
1.2 Concrete work shall conform to IS 456:2000 throughout the
structure.
1.3 The contractor shall submit a quality assurance plan before
commencement of any structural work.
Page 1 of 2""",
    """Municipal Corporation of Pune
Tender No. MCP/2026/CIV/114 - Ward Office Building
2. STRUCTURAL DESIGN
2.1 Seismic design of the moment resisting frame shall follow
IS 1893:2002 and ductile detailing shall be as per IS 13920.
2.2 All structural steelwork to be hot rolled medium tensile
steel of approved make.
2.3 Foundation design shall account for the safe bearing
capacity established by site investigation.
2.4 Formwork shall be maintained until the concrete attains the
specified characteristic strength.
Page 2 of 2""",
]

ELECTRICAL = [
    """Maharashtra State Electricity Distribution Co. Ltd.
Tender No. MSEDCL/2026/ELE/207 - Substation Ancillaries
1. GENERAL
1.1 Supply and installation of internal electrical wiring and
distribution boards for the substation control room.
1.2 All PVC insulated cables shall conform to IS 694.
1.3 Electrical wiring installation practice shall follow
IS 732:2019 in its entirety.
Page 1 of 2""",
    """Maharashtra State Electricity Distribution Co. Ltd.
Tender No. MSEDCL/2026/ELE/207 - Substation Ancillaries
2. PROTECTION AND EARTHING
2.1 Earthing of the installation shall be carried out as per
IS 3043.
2.2 Miniature circuit breakers for final circuits shall comply
with IS 8828.
2.3 Residual current operated circuit breakers shall be
provided on all socket outlet circuits.
2.4 Three phase induction motors supplied under this contract
shall be of energy efficiency class IE3 or better.
2.5 Self-ballasted LED lamps for area lighting shall carry a
valid BIS registration.
Page 2 of 2""",
]

WATER_SUPPLY = [
    """Pune Municipal Water Supply Department
Tender No. PMWS/2026/WAT/058 - Rural Bottling and Distribution
1. SCOPE
1.1 Establishment of a packaged drinking water bottling unit
with a capacity of 12,000 litres per day.
1.2 Packaged drinking water shall conform to IS 14543 and the
source water shall meet IS 10500.
1.3 Supply and laying of electrically welded steel pipes for
the raw water transmission main.
2. MECHANICAL
2.1 Copper alloy gate and globe valves shall be provided at all
chamber locations.
2.2 Sluice valves of 150 mm size shall be installed on the
distribution header.
2.3 Rotodynamic pumps shall be selected for the duty point
established in the hydraulic design report.
Page 1 of 1""",
]

# Deliberately good: current editions, and the normative chain spelled out.
# Gives the completeness gauge something high to show, which makes the low
# scores elsewhere mean something.
WELL_SPECIFIED = [
    """Central Public Works Department
Tender No. CPWD/2026/STR/311 - Laboratory Block
1. STRUCTURAL SPECIFICATION
1.1 Plain and reinforced concrete work shall conform to
IS 456:2000 in design, materials and workmanship.
1.2 Ordinary Portland cement shall conform to IS 269:2015.
1.3 Coarse and fine aggregate shall conform to IS 383:2016.
1.4 High strength deformed reinforcement bars shall conform to
IS 1786:2008 and shall carry a valid BIS licence.
1.5 Concrete admixtures, where used, shall conform to
IS 9103:1999.
1.6 Earthquake resistant design shall follow
IS 1893 (Part 1):2016 with ductile detailing to IS 13920:2016.
Page 1 of 1""",
]

# The opposite case: a real-world tender that names no standard at all. The
# recommender still has to be useful here, which is the point of showing it.
NO_CITATIONS = [
    """Zilla Parishad, Satara
Tender No. ZPS/2026/GEN/042 - School Refurbishment
1. SCHEDULE OF WORK
1.1 Supply and installation of galvanized steel roofing sheets
over the existing classroom block.
1.2 Provision of protective helmets for all site personnel
engaged in overhead work.
1.3 Supply of stainless steel drinking water containers for the
school kitchen.
1.4 Internal electrical wiring for six classrooms including
switches and socket outlets.
1.5 Supply of portable fire extinguishers for each floor
landing as per the fire safety plan.
1.6 Painting of internal masonry and plaster surfaces with
washable emulsion paint.
Page 1 of 1""",
]

# Everything that breaks naive extraction, in one file: a contents page with
# dot leaders, a running header and footer, a schedule-of-rates table, and
# three different numbering conventions in the same document.
MESSY_BOQ = [
    """Public Works Department, Government of Maharashtra
Tender Document PWD/2026/BR/0091
TABLE OF CONTENTS
Section 1 - Instructions to Bidders ................ 2
Section 2 - Technical Specification ................ 4
Section 3 - Schedule of Rates ...................... 9
Section 4 - Contract Conditions ................... 14
Page 1 of 3""",
    """Public Works Department, Government of Maharashtra
Tender Document PWD/2026/BR/0091
SECTION 2 - TECHNICAL SPECIFICATION
2.1 Structural concrete for the bridge deck shall conform to
IS 456:2000 and shall attain the specified characteristic
compressive strength at 28 days.
(a) Cement shall be ordinary Portland cement of 53 grade.
(b) Reinforcement shall be high strength deformed bars.
- Cover blocks shall be of the same grade as the parent concrete.
- Construction joints shall be located as shown on the drawings.
2.2 Hot rolled structural steel sections shall conform to
IS 2062 for all bearing assemblies.
Page 2 of 3""",
    """Public Works Department, Government of Maharashtra
Tender Document PWD/2026/BR/0091
SECTION 3 - SCHEDULE OF RATES
Sl No Description Unit Qty Rate Amount
1 Cement OPC 53 grade MT 420 385 161700
2 TMT reinforcement bars MT 68 62500 4250000
3 Structural steel sections MT 44 71200 3132800
4 Coarse aggregate 20 mm CUM 610 1240 756400
5 Ready mixed concrete M30 CUM 980 5600 5488000
Total 13788900
3.1 Rates quoted shall be inclusive of all taxes and duties.
3.2 The quantities shown above are provisional and subject to
measurement on completion.
Page 3 of 3""",
]


def _draw(pdf: canvas.Canvas, pages: list[str]) -> None:
    for page in pages:
        pdf.setFont(MONO, BODY_SIZE)
        y = TOP
        for line in page.splitlines():
            pdf.drawString(LEFT, y, line)
            y -= LEADING
        pdf.showPage()


def write_text_pdf(name: str, pages: list[str], title: str) -> Path:
    path = OUT_DIR / name
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle(title)
    _draw(pdf, pages)
    pdf.save()
    return path


def write_scanned_pdf(name: str, title: str) -> Path:
    """A PDF with no text layer, to exercise the scanned-document refusal.

    Drawing only vector shapes gives a file that is structurally valid and
    extracts to nothing — which is exactly what a scan looks like to pypdf,
    without needing an image dependency.
    """
    path = OUT_DIR / name
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle(title)
    for _ in range(2):
        pdf.rect(LEFT, 120, 480, 640)
        y = TOP - 40
        # Grey bars standing in for scanned lines of text.
        pdf.setFillGray(0.75)
        for row in range(26):
            width = 430 if row % 4 else 250
            pdf.rect(LEFT + 22, y, width, 7, stroke=0, fill=1)
            y -= 22
        pdf.setFillGray(0)
        pdf.showPage()
    pdf.save()
    return path


DOCUMENTS = [
    ("01-building-rcc.pdf", BUILDING_RCC, "RCC office building - outdated citations"),
    ("02-electrical-substation.pdf", ELECTRICAL, "Substation - mandatory certification"),
    ("03-water-supply.pdf", WATER_SUPPLY, "Packaged drinking water bottling unit"),
    ("04-well-specified.pdf", WELL_SPECIFIED, "A well-specified tender"),
    ("05-no-citations.pdf", NO_CITATIONS, "A tender citing no standards"),
    ("06-messy-boq.pdf", MESSY_BOQ, "Contents page, BOQ table, mixed numbering"),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, pages, title in DOCUMENTS:
        path = write_text_pdf(name, pages, title)
        print(f"  {path.name:<30} {len(pages)} page(s)  {title}")
    path = write_scanned_pdf("07-scanned.pdf", "Scanned tender - no text layer")
    print(f"  {path.name:<30} 2 page(s)  no text layer (must be refused)")
    print(f"\nWrote {len(DOCUMENTS) + 1} files to {OUT_DIR}")


if __name__ == "__main__":
    main()
