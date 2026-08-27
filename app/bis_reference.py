"""Authoritative BIS reference data.

Static, verifiable facts about the Bureau of Indian Standards, kept apart from
the corpus so that coverage can be reported against real denominators rather
than against our own index size.

Source: BIS *Standard catalogue — July '25* (published via SESEI, the Seconded
European Standardization Expert in India), cross-checked against PIB release
PRID 1998858. Figures are as of **June 2025**: 23,461 published standards across
17 technical departments and 405+ sectional committees.
"""

from typing import NamedTuple

CATALOGUE_AS_OF = "June 2025"
TOTAL_PUBLISHED_STANDARDS = 23461
TOTAL_SECTIONAL_COMMITTEES = 405


class Department(NamedTuple):
    """One BIS technical department."""

    code: str
    name: str
    published: int  # standards published by this department, as of CATALOGUE_AS_OF


# Ordered largest-first, matching how BIS reports the catalogue.
#
# Naming traps that cost time if you guess: Electronics and Information
# Technology is LITD (not "EITD"), and Management and Systems is MSD (not "MND").
DEPARTMENTS: tuple[Department, ...] = (
    Department("PGD", "Production and General Engineering", 2589),
    Department("FAD", "Food and Agriculture", 2338),
    Department("CHD", "Chemical", 2101),
    Department("CED", "Civil Engineering", 2005),
    Department("ETD", "Electrotechnical", 1954),
    Department("MTD", "Metallurgical Engineering", 1774),
    Department("MHD", "Medical Equipment and Hospital Planning", 1743),
    Department("LITD", "Electronics and Information Technology", 1604),
    Department("TXD", "Textiles", 1547),
    Department("PCD", "Petroleum, Coal and Related Products", 1525),
    Department("MED", "Mechanical Engineering", 1453),
    Department("TED", "Transport Engineering", 1363),
    Department("MSD", "Management and Systems", 544),
    Department("WRD", "Water Resources", 462),
    Department("AYD", "Ayush", 178),
    Department("SSD", "Service Sector", 163),
    Department("EED", "Environment and Ecology", 118),
)

BY_CODE: dict[str, Department] = {d.code: d for d in DEPARTMENTS}
BY_NAME: dict[str, Department] = {d.name: d for d in DEPARTMENTS}


def department_for_committee(committee: str) -> Department | None:
    """Resolve 'CHD 13' -> the Chemical department.

    Sectional committee codes are the department code followed by a number, so
    the prefix is the department. Longest-prefix first, because 'LITD' would
    otherwise never match against a naive scan that hits nothing.
    """
    token = (committee or "").strip().split()[0].upper() if committee.strip() else ""
    return BY_CODE.get(token)


def resolve_department(sector: str = "", committee: str = "") -> Department | None:
    """Best-effort department, preferring the committee code over the sector name."""
    return department_for_committee(committee) or BY_NAME.get((sector or "").strip())


# --- Conformity assessment schemes ---------------------------------------
#
# All are built on the principles of IS/ISO/IEC 17067 and are operated through
# 5 regional offices and 41 branch offices. Certification is VOLUNTARY by
# default; it becomes mandatory only when the Central Government notifies a
# Quality Control Order (QCO) for that product.


class Scheme(NamedTuple):
    key: str
    name: str
    applies_to: str
    steps: tuple[str, ...]


SCHEMES: tuple[Scheme, ...] = (
    Scheme(
        key="scheme_i",
        name="Scheme I — Product Certification (ISI Mark)",
        applies_to=(
            "Indian manufacturers seeking a licence to apply the ISI Standard Mark "
            "to a product covered by an Indian Standard."
        ),
        steps=(
            "Confirm the Indian Standard that covers your product.",
            "Ensure in-house testing facilities and a factory quality plan are in place.",
            "Apply to the BIS branch office through the Manakonline portal.",
            "BIS inspects the factory and draws samples for independent testing.",
            "On conformity, BIS grants a licence to use the ISI Mark.",
            "Maintain conformity — BIS carries out surveillance inspections.",
        ),
    ),
    Scheme(
        key="fmcs",
        name="FMCS — Foreign Manufacturers Certification Scheme",
        applies_to=(
            "Manufacturers located outside India who want to apply the ISI Mark to "
            "goods exported into the Indian market."
        ),
        steps=(
            "Confirm the Indian Standard that covers your product.",
            "Nominate an Authorised Indian Representative (AIR).",
            "Apply to BIS headquarters under FMCS.",
            "BIS carries out a factory inspection at the overseas plant.",
            "Samples are tested in a BIS-recognised laboratory.",
            "On conformity, BIS grants the licence; surveillance continues annually.",
        ),
    ),
    Scheme(
        key="crs",
        name="Scheme II — Compulsory Registration Scheme (CRS)",
        applies_to=(
            "Products notified under a QCO — predominantly electronics and IT "
            "goods. Registration is by self-declaration backed by a test report."
        ),
        steps=(
            "Confirm the product is in the CRS notified list and identify its IS.",
            "Have the product tested at a BIS-recognised laboratory.",
            "Submit the test report and application on the BIS CRS portal.",
            "BIS grants a registration number for the Standard Mark.",
            "Label the product with the registration number before sale.",
        ),
    ),
    Scheme(
        key="hallmarking",
        name="Hallmarking Scheme",
        applies_to=(
            "Gold and silver articles. Hallmarking of gold jewellery is mandatory "
            "in notified districts and is tracked by a 6-digit HUID."
        ),
        steps=(
            "Register as a jeweller with BIS.",
            "Send articles to a BIS-recognised Assaying and Hallmarking Centre.",
            "The centre assays purity and applies the hallmark with a unique HUID.",
            "Display the BIS registration and the purity grades stocked.",
            "Consumers can verify any HUID in the BIS Care app.",
        ),
    ),
    Scheme(
        key="scheme_x",
        name="Scheme X — Machinery and Electrical Equipment",
        applies_to=(
            "Machinery and electrical equipment notified under the Omnibus "
            "Technical Regulation, covering both domestic and foreign makers."
        ),
        steps=(
            "Identify the applicable Indian Standard and conformity level.",
            "Apply to BIS under Scheme X of the BIS (Conformity Assessment) Regulations.",
            "BIS assesses the type test report and the factory quality system.",
            "A certificate of conformity is issued for the equipment type.",
            "Affix the Standard Mark as permitted by the certificate.",
        ),
    ),
    Scheme(
        key="eco_mark",
        name="Eco Mark Scheme",
        applies_to=(
            "Products meeting the environmental criteria notified for their "
            "category, in addition to the relevant Indian Standard."
        ),
        steps=(
            "Confirm the product's Indian Standard and Eco Mark criteria.",
            "Obtain an ISI licence for the product.",
            "Demonstrate the additional environmental criteria are met.",
            "BIS endorses the licence to permit the Eco Mark.",
        ),
    ),
)

SCHEMES_BY_KEY: dict[str, Scheme] = {s.key: s for s in SCHEMES}

VOLUNTARY_NOTE = (
    "BIS certification is voluntary by default. It becomes mandatory only when "
    "the Central Government notifies a Quality Control Order (QCO) covering the "
    "product. Always confirm the current QCO position on the BIS portal before "
    "relying on this."
)
