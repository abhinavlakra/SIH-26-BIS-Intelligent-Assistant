"""Curated enrichment pass over the seed corpus.

Two jobs, both idempotent — run it as many times as you like:

1. **Patch** existing records with the v2 fields: the normative-reference graph,
   test methods, QCO/certification status, amendment counts and version
   lineage. These relationships come from the public front matter of each
   standard (the "References" clause), not from its copyrighted body text.
2. **Extend** coverage across BIS technical departments. The original 51 records
   were 51% Civil Engineering against a real catalogue that is 8.5% Civil, and
   nine of the seventeen departments had no record at all — so any question
   about textiles, machinery, medical devices or transport returned
   "not in the catalogue", which looks like the honesty guard working when it is
   really a coverage hole.

Run:
    python -m app.ingestion.enrich            # report what would change
    python -m app.ingestion.enrich --write    # rewrite data/seed/standards.jsonl
    python -m app.ingestion.build_index --rebuild

**On `verification`:** every record here is marked `unverified` unless it was
taken directly from an official BIS publication. IS numbers and titles are drawn
from domain knowledge of real, well-known Indian Standards, but years, committee
codes and QCO status still need a pass against the official catalogue before
this is presented. `verify.py` tracks that pass. Nothing in the UI claims a
record is verified when it is not.
"""

import argparse
import json
from typing import Any

from app.config import get_settings
from ingestion.normalize import load_jsonl, write_jsonl
from app.models import Standard

# ---------------------------------------------------------------------------
# Patches to existing records.
#
# `normative_refs` are standards a record *requires* — walking these one hop out
# from a semantic hit surfaces standards no embedding would ever match (a query
# about concrete design should surface the *cement* standard).
#
# QCO flags are set only where the Quality Control Order is well established and
# nameable. A wrong "certification is mandatory" claim is worse than an absent
# one, so anything uncertain is left False.
# ---------------------------------------------------------------------------

CEMENT_QCO = "Cement (Quality Control) Order, 2003"
STEEL_QCO = "Steel and Steel Products (Quality Control) Order"
ELECTRONICS_QCO = (
    "Electronics and Information Technology Goods "
    "(Requirements for Compulsory Registration) Order, 2021"
)
TOYS_QCO = "Toys (Quality Control) Order, 2020"
WATER_QCO = "Packaged Drinking Water — mandatory BIS certification"

ENRICHMENT: dict[str, dict[str, Any]] = {
    # --- Water ---------------------------------------------------------
    "IS 10500:2012": {
        "test_methods": ["IS 3025"],
        "amendment_count": 1,
    },
    "IS 14543:2016": {
        "qco_mandatory": True,
        "qco_name": WATER_QCO,
        "certification_scheme": "scheme_i",
        "normative_refs": ["IS 10500:2012"],
        "test_methods": ["IS 3025"],
    },
    "IS 13428:2005": {
        "qco_mandatory": True,
        "qco_name": WATER_QCO,
        "certification_scheme": "scheme_i",
        "test_methods": ["IS 3025"],
    },
    "IS 3025": {"year": 1987},
    # --- Concrete cluster ------------------------------------------------
    # IS 456 is the hub of the civil-engineering graph: it normatively pulls in
    # cement, aggregate, reinforcement and test-method standards. This one
    # cluster is the clearest demonstration of graph expansion in the demo.
    "IS 456:2000": {
        # IS 8112 (43 grade) and IS 12269 (53 grade) are deliberately absent:
        # IS 269:2015 unified the 33/43/53 OPC grades and superseded both, and
        # the BIS portal publishes neither in any edition. Listing them here
        # made the tender checker advise procurement officers to cite withdrawn
        # standards — the exact defect the feature is meant to catch.
        "normative_refs": [
            "IS 269:2015",
            "IS 383:2016",
            "IS 1786:2008",
            "IS 9103:1999",
        ],
        "test_methods": ["IS 516:2021", "IS 2386", "IS 4031"],
        "amendment_count": 4,
    },
    "IS 10262:2019": {
        "normative_refs": ["IS 456:2000", "IS 383:2016", "IS 269:2015"],
        "test_methods": ["IS 516:2021"],
        "supersedes": ["IS 10262:2009"],
    },
    "IS 383:2016": {
        "test_methods": ["IS 2386"],
        "supersedes": ["IS 383:1970"],
    },
    "IS 2386": {"year": 1963},
    "IS 269:2015": {
        "qco_mandatory": True,
        "qco_name": CEMENT_QCO,
        "certification_scheme": "scheme_i",
        "test_methods": ["IS 4031"],
        "supersedes": ["IS 269:1989"],
    },
    "IS 8112:2013": {
        "qco_mandatory": True,
        "qco_name": CEMENT_QCO,
        "certification_scheme": "scheme_i",
        "test_methods": ["IS 4031"],
        # Absorbed into IS 269:2015, which unified the OPC grades. The BIS
        # portal publishes no edition of this number — the collector reports it
        # in its `unmatched` list. Kept in the corpus so a tender still citing
        # it resolves and gets told what replaced it.
        "status": "superseded",
        "superseded_by": "IS 269:2015",
    },
    "IS 12269:2013": {
        "qco_mandatory": True,
        "qco_name": CEMENT_QCO,
        "certification_scheme": "scheme_i",
        "test_methods": ["IS 4031"],
        # Absorbed into IS 269:2015, which unified the OPC grades. The BIS
        # portal publishes no edition of this number — the collector reports it
        # in its `unmatched` list. Kept in the corpus so a tender still citing
        # it resolves and gets told what replaced it.
        "status": "superseded",
        "superseded_by": "IS 269:2015",
    },
    "IS 1489 (Part 1):2015": {
        "qco_mandatory": True,
        "qco_name": CEMENT_QCO,
        "certification_scheme": "scheme_i",
        "normative_refs": ["IS 3812 (Part 1):2013"],
        "test_methods": ["IS 4031"],
    },
    "IS 455:2015": {
        "qco_mandatory": True,
        "qco_name": CEMENT_QCO,
        "certification_scheme": "scheme_i",
        "test_methods": ["IS 4031"],
    },
    "IS 3812 (Part 1):2013": {"test_methods": ["IS 4031"]},
    "IS 4031": {"year": 1988},
    "IS 516:2021": {"supersedes": ["IS 516:1959"]},
    "IS 9103:1999": {"normative_refs": ["IS 456:2000"]},
    # --- Structural steel -------------------------------------------------
    "IS 1786:2008": {
        "qco_mandatory": True,
        "qco_name": STEEL_QCO,
        "certification_scheme": "scheme_i",
        "amendment_count": 4,
    },
    "IS 2062:2011": {
        "qco_mandatory": True,
        "qco_name": STEEL_QCO,
        "certification_scheme": "scheme_i",
        "amendment_count": 2,
    },
    "IS 800:2007": {
        "normative_refs": ["IS 2062:2011", "IS 875 (Part 3):2015", "IS 1893 (Part 1):2016"],
        "supersedes": ["IS 800:1984"],
    },
    "IS 1239 (Part 1):2004": {
        "qco_mandatory": True,
        "qco_name": STEEL_QCO,
        "certification_scheme": "scheme_i",
    },
    "IS 277:2018": {
        "qco_mandatory": True,
        "qco_name": STEEL_QCO,
        "certification_scheme": "scheme_i",
    },
    "IS 6911:2017": {
        "qco_mandatory": True,
        "qco_name": STEEL_QCO,
        "certification_scheme": "scheme_i",
    },
    "IS 5522:2014": {
        "normative_refs": ["IS 6911:2017"],
        "certification_scheme": "scheme_i",
    },
    "IS 513 (Part 1):2016": {
        "qco_mandatory": True,
        "qco_name": STEEL_QCO,
        "certification_scheme": "scheme_i",
    },
    # --- Seismic / loads --------------------------------------------------
    "IS 1893 (Part 1):2016": {
        "normative_refs": ["IS 456:2000", "IS 875 (Part 3):2015", "IS 13920:2016"],
        "supersedes": ["IS 1893 (Part 1):2002"],
        "amendment_count": 2,
    },
    "IS 13920:2016": {
        "normative_refs": ["IS 456:2000", "IS 1893 (Part 1):2016", "IS 1786:2008"],
        "supersedes": ["IS 13920:1993"],
        "amendment_count": 2,
    },
    "IS 4326:2013": {
        "normative_refs": ["IS 1893 (Part 1):2016", "IS 456:2000", "IS 13920:2016"],
    },
    "IS 875 (Part 3):2015": {"supersedes": ["IS 875 (Part 3):1987"]},
    # --- Geotechnical -----------------------------------------------------
    "IS 2720": {"year": 1983},
    "IS 1904:1986": {"test_methods": ["IS 2720"], "normative_refs": ["IS 456:2000"]},
    "IS 2911 (Part 1/Sec 1):2010": {
        "normative_refs": ["IS 456:2000", "IS 1904:1986"],
        "test_methods": ["IS 2720"],
    },
    "IS 1200": {"year": 1992},
    "IS 1077:1992": {"amendment_count": 5},
    # --- Electrotechnical -------------------------------------------------
    "IS 302 (Part 1):2008": {
        "qco_mandatory": True,
        "qco_name": ELECTRONICS_QCO,
        "certification_scheme": "scheme_i",
    },
    "IS 1293:2019": {
        "qco_mandatory": True,
        "qco_name": "Electrical Accessories (Quality Control) Order",
        "certification_scheme": "scheme_i",
    },
    "IS 694:2010": {
        "qco_mandatory": True,
        "qco_name": "Electric Cables (Quality Control) Order",
        "certification_scheme": "scheme_i",
    },
    "IS 732:2019": {
        "normative_refs": ["IS 694:2010", "IS 3043:2018"],
        "supersedes": ["IS 732:1989"],
    },
    "IS 3043:2018": {"supersedes": ["IS 3043:1987"]},
    "IS 13252 (Part 1):2010": {
        "qco_mandatory": True,
        "qco_name": ELECTRONICS_QCO,
        "certification_scheme": "crs",
    },
    "IS 16102 (Part 1):2012": {
        "qco_mandatory": True,
        "qco_name": ELECTRONICS_QCO,
        "certification_scheme": "crs",
    },
    "IS 16046 (Part 2):2018": {
        "qco_mandatory": True,
        "qco_name": ELECTRONICS_QCO,
        "certification_scheme": "crs",
    },
    # --- Safety / other ---------------------------------------------------
    "IS 9873 (Part 1):2019": {
        "qco_mandatory": True,
        "qco_name": TOYS_QCO,
        "certification_scheme": "scheme_i",
    },
    "IS 2190:2010": {"normative_refs": ["IS 15683:2018"]},
    "IS 15700:2018": {"certification_scheme": "scheme_i"},
}


# ---------------------------------------------------------------------------
# New records, chosen to put every BIS technical department on the map.
#
# Ayush (AYD) is deliberately left uncovered: I could not confirm specific IS
# numbers for it to the standard the rest of this corpus is held to, and an
# invented record is worse than an honest gap. The coverage dashboard reports
# it as 0 — which is also a working demonstration of the coverage feature.
# ---------------------------------------------------------------------------

NEW_STANDARDS: list[dict[str, Any]] = [
    # =============== PGD — Production and General Engineering ===============
    {
        "is_number": "IS 1367 (Part 3):2017",
        "title": (
            "Technical Supply Conditions for Threaded Steel Fasteners — Part 3: "
            "Mechanical Properties of Fasteners Made of Carbon Steel and Alloy Steel"
        ),
        "scope": (
            "Mechanical and physical properties of bolts, screws and studs made of "
            "carbon steel and alloy steel, including property classes, tensile "
            "strength, proof load and hardness requirements for threaded fasteners."
        ),
        "ics_codes": ["21.060.10"],
        "sector": "Production and General Engineering",
        "technical_committee": "PGD 31",
        "year": 2017,
        "keywords": ["fasteners", "bolts", "screws", "property class", "studs", "nuts"],
        "normative_refs": ["IS 1363 (Part 1):2019"],
    },
    {
        "is_number": "IS 1363 (Part 1):2019",
        "title": (
            "Hexagon Head Bolts, Screws and Nuts of Product Grade C — Part 1: "
            "Hexagon Head Bolts"
        ),
        "scope": (
            "Dimensions, tolerances and designation for hexagon head bolts of "
            "product grade C in the thread size range M5 to M64, for general "
            "engineering assembly work."
        ),
        "ics_codes": ["21.060.10"],
        "sector": "Production and General Engineering",
        "technical_committee": "PGD 31",
        "year": 2019,
        "keywords": ["hexagon bolt", "fastener dimensions", "grade C", "machine screws"],
    },
    {
        "is_number": "IS 2347:2017",
        "title": "Domestic Pressure Cooker — Specification",
        "scope": (
            "Requirements for domestic pressure cookers including material of the "
            "body, safety devices, gasket, pressure regulating device, burst "
            "pressure and performance tests for household cooking use."
        ),
        "ics_codes": ["97.040.60"],
        "sector": "Production and General Engineering",
        "technical_committee": "PGD 25",
        "year": 2017,
        "keywords": ["pressure cooker", "kitchenware", "domestic appliance", "safety valve"],
        "qco_mandatory": True,
        "qco_name": "Domestic Pressure Cooker (Quality Control) Order, 2020",
        "certification_scheme": "scheme_i",
        "normative_refs": ["IS 5522:2014"],
    },
    {
        "is_number": "IS 210:2009",
        "title": "Grey Iron Castings — Specification",
        "scope": (
            "Grades, chemical composition, mechanical properties and testing of "
            "grey iron castings used in general engineering applications, "
            "classified by minimum tensile strength."
        ),
        "ics_codes": ["77.140.80"],
        "sector": "Production and General Engineering",
        "technical_committee": "PGD 10",
        "year": 2009,
        "keywords": ["grey iron", "castings", "foundry", "cast iron", "tensile strength"],
    },
    {
        "is_number": "IS 3589:2001",
        "title": "Steel Pipes for Water and Sewage — Specification",
        "scope": (
            "Requirements for electrically welded steel pipes of nominal size 168.3 "
            "mm to 2540 mm outside diameter used for conveying water, sewage and "
            "other liquids, covering dimensions, tolerances and hydrostatic testing."
        ),
        "ics_codes": ["23.040.10"],
        "sector": "Production and General Engineering",
        "technical_committee": "PGD 9",
        "year": 2001,
        "keywords": ["steel pipe", "water pipeline", "sewage", "welded pipe", "penstock"],
        "normative_refs": ["IS 2062:2011"],
    },
    {
        "is_number": "IS 919 (Part 1):1993",
        "title": "ISO System of Limits and Fits — Part 1: Bases of Tolerances, Deviations and Fits",
        "scope": (
            "The ISO system of limits and fits as adopted in India: tolerance "
            "grades, fundamental deviations and the hole-basis and shaft-basis fit "
            "systems used across mechanical engineering drawings."
        ),
        "ics_codes": ["17.040.10"],
        "sector": "Production and General Engineering",
        "technical_committee": "PGD 22",
        "year": 1993,
        "keywords": ["limits and fits", "tolerance", "engineering drawing", "clearance fit"],
    },
    # ===================== MED — Mechanical Engineering =====================
    {
        "is_number": "IS 778:1984",
        "title": (
            "Copper Alloy Gate, Globe and Check Valves for Waterworks Purposes — "
            "Specification"
        ),
        "scope": (
            "Requirements for copper alloy gate, globe and check valves of nominal "
            "sizes 8 mm to 80 mm for waterworks service, covering pressure class, "
            "materials, dimensions and hydrostatic testing."
        ),
        "ics_codes": ["23.060.01"],
        "sector": "Mechanical Engineering",
        "technical_committee": "MED 6",
        "year": 1984,
        "keywords": ["valve", "gate valve", "globe valve", "waterworks", "plumbing", "brass"],
    },
    {
        "is_number": "IS 780:1984",
        "title": "Sluice Valves for Waterworks Purposes (50 to 300 mm Size) — Specification",
        "scope": (
            "Requirements for cast iron double flanged sluice valves of 50 mm to 300 "
            "mm size used in water supply systems, including body materials, "
            "operating mechanism and pressure testing."
        ),
        "ics_codes": ["23.060.30"],
        "sector": "Mechanical Engineering",
        "technical_committee": "MED 6",
        "year": 1984,
        "keywords": ["sluice valve", "water supply", "cast iron valve", "pipeline fittings"],
        "normative_refs": ["IS 210:2009"],
    },
    {
        "is_number": "IS 5120:1977",
        "title": "Technical Requirements for Rotodynamic Special Purpose Pumps",
        "scope": (
            "Technical requirements, construction features and performance criteria "
            "for rotodynamic pumps used in special purpose service, including "
            "materials of construction and acceptance conditions."
        ),
        "ics_codes": ["23.080"],
        "sector": "Mechanical Engineering",
        "technical_committee": "MED 20",
        "year": 1977,
        "keywords": ["pump", "centrifugal pump", "rotodynamic", "pumping machinery"],
    },
    {
        "is_number": "IS 807:2006",
        "title": (
            "Design, Erection and Testing (Structural Portion) of Cranes and Hoists "
            "— Code of Practice"
        ),
        "scope": (
            "Structural design, fabrication, erection and testing requirements for "
            "the structural portion of cranes and hoists, including load "
            "classification, permissible stresses and deflection limits."
        ),
        "ics_codes": ["53.020.20"],
        "sector": "Mechanical Engineering",
        "technical_committee": "MED 14",
        "year": 2006,
        "keywords": ["crane", "hoist", "material handling", "gantry", "lifting equipment"],
        "normative_refs": ["IS 800:2007", "IS 2062:2011"],
    },
    # ============ MHD — Medical Equipment and Hospital Planning =============
    {
        "is_number": "IS 13450 (Part 1):2018",
        "title": (
            "Medical Electrical Equipment — Part 1: General Requirements for Basic "
            "Safety and Essential Performance"
        ),
        "scope": (
            "General requirements for basic safety and essential performance of "
            "medical electrical equipment, covering protection against electrical, "
            "mechanical, radiation and thermal hazards to the patient and operator."
        ),
        "ics_codes": ["11.040.01"],
        "sector": "Medical Equipment and Hospital Planning",
        "technical_committee": "MHD 14",
        "year": 2018,
        "keywords": [
            "medical device",
            "medical electrical equipment",
            "patient safety",
            "hospital equipment",
        ],
    },
    {
        "is_number": "IS 4148:2011",
        "title": "Surgical Rubber Gloves — Specification",
        "scope": (
            "Requirements for sterile and non-sterile surgical rubber gloves "
            "including dimensions, tensile strength before and after ageing, "
            "freedom from holes, powder residue and packaging."
        ),
        "ics_codes": ["11.140"],
        "sector": "Medical Equipment and Hospital Planning",
        "technical_committee": "MHD 9",
        "year": 2011,
        "keywords": ["surgical gloves", "rubber gloves", "medical consumables", "sterile"],
    },
    {
        "is_number": "IS 16289:2014",
        "title": "Medical Textiles — Surgical Face Masks — Specification",
        "scope": (
            "Requirements for surgical face masks used in healthcare settings, "
            "covering bacterial filtration efficiency, differential pressure, "
            "splash resistance and biocompatibility."
        ),
        "ics_codes": ["11.140"],
        "sector": "Medical Equipment and Hospital Planning",
        "technical_committee": "MHD 9",
        "year": 2014,
        "keywords": ["face mask", "surgical mask", "PPE", "filtration efficiency", "hospital"],
    },
    # ===================== TED — Transport Engineering ======================
    {
        "is_number": "IS 4151:2015",
        "title": "Protective Helmets for Two Wheeler Riders — Specification",
        "scope": (
            "Requirements for protective helmets worn by riders of two wheeled "
            "motor vehicles, covering shell construction, impact absorption, "
            "retention system strength, field of vision and visor requirements."
        ),
        "ics_codes": ["13.340.20"],
        "sector": "Transport Engineering",
        "technical_committee": "TED 8",
        "year": 2015,
        "keywords": ["helmet", "two wheeler", "motorcycle helmet", "rider safety", "ISI helmet"],
        "qco_mandatory": True,
        "qco_name": "Helmet for Riders of Two Wheeled Motor Vehicles (Quality Control) Order, 2020",
        "certification_scheme": "scheme_i",
    },
    {
        "is_number": "IS 14664:1999",
        "title": "Automotive Vehicles — Rear View Mirrors — Specification",
        "scope": (
            "Requirements for rear view mirrors fitted to automotive vehicles, "
            "covering reflecting surface, field of vision, mounting stability and "
            "impact behaviour."
        ),
        "ics_codes": ["43.040.60"],
        "sector": "Transport Engineering",
        "technical_committee": "TED 6",
        "year": 1999,
        "keywords": ["rear view mirror", "automotive", "vehicle safety", "field of vision"],
    },
    # ========================= TXD — Textiles ===============================
    {
        "is_number": "IS 1969 (Part 1):2018",
        "title": (
            "Textiles — Tensile Properties of Fabrics — Part 1: Determination of "
            "Maximum Force and Elongation at Maximum Force Using the Strip Method"
        ),
        "scope": (
            "Method for determining the maximum force and elongation at maximum "
            "force of textile fabrics using the strip method, applicable to woven "
            "fabrics and other non-extensible textile materials."
        ),
        "ics_codes": ["59.080.30"],
        "sector": "Textiles",
        "technical_committee": "TXD 1",
        "year": 2018,
        "keywords": ["fabric testing", "tensile strength", "textile test method", "strip method"],
    },
    {
        "is_number": "IS 667:1981",
        "title": "Cotton Sewing Threads — Specification",
        "scope": (
            "Requirements for cotton sewing threads including count, ply, twist, "
            "breaking strength, colour fastness and packaging for industrial and "
            "domestic sewing use."
        ),
        "ics_codes": ["59.080.20"],
        "sector": "Textiles",
        "technical_committee": "TXD 3",
        "year": 1981,
        "keywords": ["sewing thread", "cotton yarn", "garment manufacturing", "textile"],
    },
    {
        "is_number": "IS 7016 (Part 1):2016",
        "title": (
            "Methods of Test for Coated and Treated Fabrics — Part 1: Determination "
            "of Length, Width, Thickness and Mass"
        ),
        "scope": (
            "Test methods for determining the physical dimensions and mass per unit "
            "area of coated and treated fabrics such as tarpaulins, rexine and "
            "waterproof textile materials."
        ),
        "ics_codes": ["59.080.40"],
        "sector": "Textiles",
        "technical_committee": "TXD 9",
        "year": 2016,
        "keywords": ["coated fabric", "tarpaulin", "textile testing", "waterproof fabric"],
    },
    # ================= PCD — Petroleum, Coal and Related ====================
    {
        "is_number": "IS 1448",
        "title": "Methods of Test for Petroleum and Its Products",
        "scope": (
            "Multi-part series (P: series) giving standard test methods for "
            "petroleum products — flash point, viscosity, distillation, density, "
            "sulphur content and other characteristics used in product specifications."
        ),
        "ics_codes": ["75.080"],
        "sector": "Petroleum, Coal and Related Products",
        "technical_committee": "PCD 1",
        "year": 1968,
        "keywords": ["petroleum testing", "flash point", "viscosity", "fuel test", "distillation"],
    },
    {
        "is_number": "IS 4576:1999",
        "title": "Liquefied Petroleum Gases — Specification",
        "scope": (
            "Requirements for commercial liquefied petroleum gas (LPG) including "
            "vapour pressure, volatility, copper strip corrosion, sulphur content "
            "and the odorant requirement for domestic and industrial supply."
        ),
        "ics_codes": ["75.160.30"],
        "sector": "Petroleum, Coal and Related Products",
        "technical_committee": "PCD 3",
        "year": 1999,
        "keywords": ["LPG", "cooking gas", "liquefied petroleum gas", "cylinder", "fuel"],
        "test_methods": ["IS 1448"],
    },
    {
        "is_number": "IS 3400 (Part 1):2021",
        "title": (
            "Methods of Test for Vulcanized Rubbers — Part 1: Tensile Stress-Strain "
            "Properties"
        ),
        "scope": (
            "Method for determining tensile strength, elongation at break and "
            "modulus of vulcanized and thermoplastic rubbers using dumb-bell and "
            "ring test pieces."
        ),
        "ics_codes": ["83.060"],
        "sector": "Petroleum, Coal and Related Products",
        "technical_committee": "PCD 13",
        "year": 2021,
        "keywords": ["rubber testing", "vulcanized rubber", "tensile", "elastomer"],
    },
    # ==================== FAD — Food and Agriculture ========================
    {
        "is_number": "IS 548 (Part 1):1964",
        "title": "Methods of Sampling and Test for Oils and Fats — Part 1: Sampling",
        "scope": (
            "Procedures for drawing representative samples of edible and industrial "
            "oils and fats from bulk containers, tanks and packaged consignments "
            "for analysis."
        ),
        "ics_codes": ["67.200.10"],
        "sector": "Food and Agriculture",
        "technical_committee": "FAD 13",
        "year": 1964,
        "keywords": ["edible oil", "fats", "sampling", "food testing", "vegetable oil"],
    },
    {
        "is_number": "IS 4941:1994",
        "title": "Extracted Honey — Specification",
        "scope": (
            "Requirements for extracted honey including moisture content, reducing "
            "sugars, sucrose, ash, acidity, fructose-glucose ratio and freedom from "
            "adulteration and fermentation."
        ),
        "ics_codes": ["67.180.10"],
        "sector": "Food and Agriculture",
        "technical_committee": "FAD 15",
        "year": 1994,
        "keywords": ["honey", "apiary", "food specification", "adulteration", "sugars"],
    },
    # ========================= CHD — Chemical ===============================
    {
        "is_number": "IS 101 (Part 1/Sec 1):1986",
        "title": (
            "Methods of Sampling and Test for Paints, Varnishes and Related Products "
            "— Part 1: Tests on Liquid Paints (General and Physical) — Section 1: "
            "Sampling"
        ),
        "scope": (
            "Procedures for sampling liquid paints, varnishes, lacquers and related "
            "products from containers and bulk supplies to obtain representative "
            "test portions."
        ),
        "ics_codes": ["87.040"],
        "sector": "Chemical",
        "technical_committee": "CHD 20",
        "year": 1986,
        "keywords": ["paint", "varnish", "coating", "sampling", "surface finish"],
    },
    {
        "is_number": "IS 4955:2001",
        "title": "Household Laundry Detergent Powders — Specification",
        "scope": (
            "Requirements for household laundry detergent powders including active "
            "detergent content, alkalinity, moisture, phosphate limits, detergency "
            "performance and packaging."
        ),
        "ics_codes": ["71.100.40"],
        "sector": "Chemical",
        "technical_committee": "CHD 25",
        "year": 2001,
        "keywords": ["detergent", "washing powder", "surfactant", "household chemicals"],
    },
    # ==================== MSD — Management and Systems ======================
    {
        "is_number": "IS/ISO 9001:2015",
        "title": "Quality Management Systems — Requirements",
        "scope": (
            "Requirements for a quality management system where an organization "
            "needs to demonstrate its ability to consistently provide products and "
            "services meeting customer and regulatory requirements. Identical "
            "adoption of ISO 9001:2015."
        ),
        "ics_codes": ["03.100.70"],
        "sector": "Management and Systems",
        "technical_committee": "MSD 2",
        "year": 2015,
        "keywords": ["QMS", "quality management", "ISO 9001", "certification", "process approach"],
    },
    {
        "is_number": "IS/ISO 14001:2015",
        "title": "Environmental Management Systems — Requirements with Guidance for Use",
        "scope": (
            "Requirements for an environmental management system that an "
            "organization can use to enhance its environmental performance, fulfil "
            "compliance obligations and achieve environmental objectives. Identical "
            "adoption of ISO 14001:2015."
        ),
        "ics_codes": ["13.020.10"],
        "sector": "Management and Systems",
        "technical_committee": "MSD 2",
        "year": 2015,
        "keywords": ["EMS", "environmental management", "ISO 14001", "sustainability"],
    },
    {
        "is_number": "IS/ISO 45001:2018",
        "title": (
            "Occupational Health and Safety Management Systems — Requirements with "
            "Guidance for Use"
        ),
        "scope": (
            "Requirements for an occupational health and safety management system "
            "to enable organizations to provide safe workplaces, prevent work-"
            "related injury and ill health, and improve OH&S performance."
        ),
        "ics_codes": ["13.100"],
        "sector": "Management and Systems",
        "technical_committee": "MSD 3",
        "year": 2018,
        "keywords": ["occupational safety", "OHSMS", "ISO 45001", "workplace safety"],
    },
    {
        "is_number": "IS/ISO/IEC 27001:2022",
        "title": (
            "Information Security, Cybersecurity and Privacy Protection — "
            "Information Security Management Systems — Requirements"
        ),
        "scope": (
            "Requirements for establishing, implementing, maintaining and "
            "continually improving an information security management system, "
            "including a set of information security controls."
        ),
        "ics_codes": ["35.030"],
        "sector": "Management and Systems",
        "technical_committee": "MSD 2",
        "year": 2022,
        "keywords": ["ISMS", "information security", "ISO 27001", "cybersecurity", "data protection"],
    },
    # ============ LITD — Electronics and Information Technology =============
    {
        "is_number": "IS 17802 (Part 1):2021",
        "title": "Accessibility for the ICT Products and Services — Part 1: Requirements",
        "scope": (
            "Functional accessibility requirements for information and "
            "communication technology products and services, covering hardware, "
            "software, web content and support documentation. Modified adoption of "
            "EN 301 549."
        ),
        "ics_codes": ["35.240.99"],
        "sector": "Electronics and Information Technology",
        "technical_committee": "LITD 35",
        "year": 2021,
        "keywords": [
            "accessibility",
            "ICT",
            "assistive technology",
            "digital inclusion",
            "EN 301 549",
        ],
        "amendment_count": 1,
        "verification": "verified",
    },
    {
        "is_number": "IS 18595:2024",
        "title": (
            "Electronic Signatures and Infrastructures (ESI) — Policy and Security "
            "Requirements for Applications for Signature Creation and Signature "
            "Validation"
        ),
        "scope": (
            "Policy and security requirements for applications that create and "
            "validate electronic signatures. Modified adoption of ETSI TS 119 101."
        ),
        "ics_codes": ["35.040"],
        "sector": "Service Sector",
        "technical_committee": "SSD 10",
        "year": 2024,
        "keywords": ["electronic signature", "digital signature", "e-sign", "trust services"],
        "verification": "verified",
    },
    # ===================== SSD — Service Sector =============================
    {
        "is_number": "IS 19155:2025",
        "title": (
            "Electronic Signatures and Infrastructures (ESI) — General Policy "
            "Requirements for Trust Service Providers"
        ),
        "scope": (
            "General policy requirements applicable to trust service providers "
            "issuing electronic signature certificates and related trust services. "
            "Modified adoption of ETSI EN 319 401."
        ),
        "ics_codes": ["35.040"],
        "sector": "Service Sector",
        "technical_committee": "SSD 10",
        "year": 2025,
        "keywords": ["trust service provider", "PKI", "certificate authority", "e-signature"],
        "verification": "verified",
    },
    {
        "is_number": "IS 19156:2025",
        "title": "Electronic Signatures and Infrastructures (ESI) — Cryptographic Suites",
        "scope": (
            "Cryptographic algorithms, key sizes and parameters recommended for use "
            "with electronic signatures and related trust services. Modified "
            "adoption of ETSI TS 119 312."
        ),
        "ics_codes": ["35.030"],
        "sector": "Service Sector",
        "technical_committee": "SSD 10",
        "year": 2025,
        "keywords": ["cryptography", "cipher suite", "key length", "electronic signature"],
        "verification": "verified",
    },
    # ================ EED — Environment and Ecology =========================
    {
        "is_number": "IS 5182 (Part 1):2006",
        "title": "Methods for Measurement of Air Pollution — Part 1: Sulphur Dioxide",
        "scope": (
            "Method for the determination of sulphur dioxide in ambient air by the "
            "modified West and Gaeke procedure, including sampling train, reagents "
            "and calculation of concentration."
        ),
        "ics_codes": ["13.040.20"],
        "sector": "Environment and Ecology",
        "technical_committee": "EED 1",
        "year": 2006,
        "keywords": ["air pollution", "ambient air quality", "sulphur dioxide", "emission testing"],
    },
    {
        "is_number": "IS 17088:2021",
        "title": "Compostable Plastics — Specification",
        "scope": (
            "Requirements and test methods for plastics designed to be composted in "
            "municipal and industrial composting facilities, covering "
            "biodegradation, disintegration, heavy metal limits and labelling."
        ),
        "ics_codes": ["83.080.01"],
        "sector": "Environment and Ecology",
        "technical_committee": "EED 3",
        "year": 2021,
        "keywords": [
            "compostable plastic",
            "biodegradable",
            "single use plastic",
            "packaging",
            "circular economy",
        ],
    },
    {
        "is_number": "IS 14534:1998",
        "title": "Guidelines for Recycling of Plastics",
        "scope": (
            "Guidelines for the collection, segregation, cleaning and reprocessing "
            "of plastic waste, including a code marking system for identifying "
            "plastic types to support recycling."
        ),
        "ics_codes": ["13.030.50"],
        "sector": "Environment and Ecology",
        "technical_committee": "EED 3",
        "year": 1998,
        "keywords": ["plastic recycling", "waste management", "resin code", "segregation"],
    },
    # ===================== WRD — Water Resources ============================
    {
        "is_number": "IS 5477 (Part 1):1999",
        "title": (
            "Methods for Fixing the Capacities of Reservoirs — Part 1: General "
            "Requirements"
        ),
        "scope": (
            "General requirements and terminology for determining reservoir "
            "capacities in river valley projects, covering dead storage, live "
            "storage, flood control storage and sedimentation allowance."
        ),
        "ics_codes": ["93.160"],
        "sector": "Water Resources",
        "technical_committee": "WRD 9",
        "year": 1999,
        "keywords": ["reservoir", "dam", "storage capacity", "river valley project", "irrigation"],
    },
    {
        "is_number": "IS 4701:1982",
        "title": "Code of Practice for Earthwork on Canals",
        "scope": (
            "Requirements for setting out, excavation, embankment construction, "
            "compaction and finishing of earthwork for irrigation canals, including "
            "material selection and quality control."
        ),
        "ics_codes": ["93.160"],
        "sector": "Water Resources",
        "technical_committee": "WRD 13",
        "year": 1982,
        "keywords": ["canal", "irrigation", "earthwork", "embankment", "compaction"],
        "test_methods": ["IS 2720"],
    },
    {
        "is_number": "IS 4410 (Part 1):1991",
        "title": (
            "Glossary of Terms Relating to River Valley Projects — Part 1: General "
            "Terms"
        ),
        "scope": (
            "Definitions of general terms used in the planning, design, "
            "construction and operation of river valley projects, providing a "
            "common vocabulary across water resources documents."
        ),
        "ics_codes": ["01.040.93", "93.160"],
        "sector": "Water Resources",
        "technical_committee": "WRD 1",
        "year": 1991,
        "keywords": ["glossary", "river valley", "water resources terminology", "hydrology"],
    },
    # =================== ETD — Electrotechnical (widen) =====================
    {
        "is_number": "IS 325:2023",
        "title": "Three Phase Induction Motors — Specification",
        "scope": (
            "Requirements for three phase AC induction motors including ratings, "
            "performance, efficiency classes, temperature rise, insulation and "
            "testing for industrial drive applications."
        ),
        "ics_codes": ["29.160.30"],
        "sector": "Electrotechnical",
        "technical_committee": "ETD 15",
        "year": 2023,
        "keywords": ["induction motor", "three phase motor", "efficiency class", "IE2", "drive"],
        "qco_mandatory": True,
        "qco_name": "Electric Motors (Quality Control) Order",
        "certification_scheme": "scheme_i",
    },
    {
        "is_number": "IS 8828:2019",
        "title": (
            "Electrical Accessories — Circuit Breakers for Overcurrent Protection "
            "for Household and Similar Installations — Specification"
        ),
        "scope": (
            "Requirements for miniature circuit breakers (MCBs) for overcurrent "
            "protection in household and similar installations, covering rated "
            "current, breaking capacity, tripping characteristics and endurance."
        ),
        "ics_codes": ["29.120.50"],
        "sector": "Electrotechnical",
        "technical_committee": "ETD 7",
        "year": 2019,
        "keywords": ["MCB", "circuit breaker", "overcurrent", "distribution board", "switchgear"],
        "qco_mandatory": True,
        "qco_name": "Electrical Accessories (Quality Control) Order",
        "certification_scheme": "scheme_i",
        "normative_refs": ["IS 732:2019"],
    },
    {
        "is_number": "IS 12640 (Part 1):2016",
        "title": (
            "Residual Current Operated Circuit-Breakers for Household and Similar "
            "Uses — Part 1: Circuit-Breakers Without Integral Overcurrent Protection"
        ),
        "scope": (
            "Requirements for residual current operated circuit-breakers (RCCBs) "
            "without integral overcurrent protection, used for protection against "
            "electric shock in household and similar installations."
        ),
        "ics_codes": ["29.120.50"],
        "sector": "Electrotechnical",
        "technical_committee": "ETD 7",
        "year": 2016,
        "keywords": ["RCCB", "earth leakage", "shock protection", "residual current", "ELCB"],
        "normative_refs": ["IS 732:2019", "IS 3043:2018"],
    },
    {
        "is_number": "IS 14665 (Part 2/Sec 1):2000",
        "title": (
            "Electric Traction Lifts — Part 2: Code of Practice for Installation, "
            "Operation and Maintenance — Section 1: Passenger and Goods Lifts"
        ),
        "scope": (
            "Code of practice for the installation, operation and maintenance of "
            "electric traction passenger and goods lifts, covering machine room, "
            "shaft, safety gear and periodic inspection."
        ),
        "ics_codes": ["91.140.90"],
        "sector": "Electrotechnical",
        "technical_committee": "ETD 25",
        "year": 2000,
        "keywords": ["lift", "elevator", "traction lift", "building services", "safety gear"],
    },
    # ================ MTD — Metallurgical Engineering (widen) ===============
    {
        "is_number": "IS 1030:1998",
        "title": "Carbon Steel Castings for General Engineering Purposes — Specification",
        "scope": (
            "Grades, chemical composition, mechanical properties, heat treatment "
            "and testing of carbon steel castings used in general engineering "
            "applications."
        ),
        "ics_codes": ["77.140.80"],
        "sector": "Metallurgical Engineering",
        "technical_committee": "MTD 17",
        "year": 1998,
        "keywords": ["steel casting", "carbon steel", "foundry", "heat treatment"],
    },
]


def _apply(standard: Standard, patch: dict[str, Any]) -> tuple[Standard, list[str]]:
    """Return a patched copy plus the names of the fields that actually changed."""
    data = standard.model_dump()
    changed = []
    for field, value in patch.items():
        if data.get(field) != value:
            data[field] = value
            changed.append(field)
    return Standard.model_validate(data), changed


def enrich(standards: list[Standard]) -> tuple[list[Standard], dict[str, list[str]]]:
    """Apply patches and append new records. Idempotent."""
    by_number = {s.is_number: s for s in standards}
    changes: dict[str, list[str]] = {}

    for is_number, patch in ENRICHMENT.items():
        current = by_number.get(is_number)
        if current is None:
            changes[is_number] = ["MISSING — patch has no matching record"]
            continue
        patched, changed = _apply(current, patch)
        if changed:
            by_number[is_number] = patched
            changes[is_number] = changed

    for entry in NEW_STANDARDS:
        is_number = entry["is_number"]
        if is_number in by_number:
            continue
        by_number[is_number] = Standard.model_validate(entry)
        changes[is_number] = ["NEW"]

    return sorted(by_number.values(), key=lambda s: s.is_number), changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Rewrite the seed corpus in place.")
    args = parser.parse_args()

    settings = get_settings()
    path = settings.seed_corpus
    standards = load_jsonl(path)
    enriched, changes = enrich(standards)

    new = [k for k, v in changes.items() if v == ["NEW"]]
    patched = {k: v for k, v in changes.items() if v != ["NEW"]}

    print(f"Corpus:   {path}")
    print(f"Before:   {len(standards)} records")
    print(f"After:    {len(enriched)} records  (+{len(new)} new, {len(patched)} patched)")

    if patched:
        print("\nPatched:")
        for is_number, fields in sorted(patched.items()):
            print(f"  {is_number:<30} {', '.join(fields)}")

    if not args.write:
        print("\n(dry run — pass --write to apply)")
        return

    write_jsonl(enriched, path)
    print(f"\nWrote {len(enriched)} records to {path}")
    print("Next: python -m app.ingestion.build_index --rebuild")


if __name__ == "__main__":
    main()
