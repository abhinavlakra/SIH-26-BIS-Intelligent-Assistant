"""Certification pathway guidance: which BIS scheme applies, and what it takes.

SIH26107 asks the assistant to "offer direction on certification pathways" and
"describe conformity verification procedures". That is not a retrieval problem —
it is a small, stable decision tree over the six BIS conformity assessment
schemes, so it is modelled explicitly rather than left to a language model to
improvise.

Nothing here states a fee or a processing time. Those change, we cannot cite
them, and a wrong number in front of a BIS jury is worse than no number.
"""

from app import bis_reference as bis
from app.models import CertificationResponse
from rag import vectorstore

# When a standard carries no explicit scheme, fall back on what the department
# usually implies. Electronics and IT goods run through CRS; most physical
# product standards run through the ISI Mark scheme.
_DEPARTMENT_DEFAULT: dict[str, str] = {
    "LITD": "crs",
    "ETD": "scheme_i",
    "CED": "scheme_i",
    "MTD": "scheme_i",
    "CHD": "scheme_i",
    "FAD": "scheme_i",
    "PGD": "scheme_i",
    "TXD": "scheme_i",
    "MED": "scheme_x",
    "MHD": "scheme_i",
    "TED": "scheme_i",
    "PCD": "scheme_i",
    "MSD": "",  # management-system standards are certified by third parties, not BIS product schemes
    "SSD": "",
    "EED": "",
    "WRD": "",
    "AYD": "scheme_i",
}

_MANAGEMENT_SYSTEM_NOTE = (
    "This is a management-system standard, not a product standard. Conformity is "
    "assessed by a certification body accredited for that scheme rather than "
    "through a BIS product certification licence."
)


def pathway(is_number: str) -> CertificationResponse | None:
    standard = vectorstore.get_one(is_number)
    if standard is None:
        return None

    scheme_key = standard.certification_scheme or _DEPARTMENT_DEFAULT.get(
        standard.department_code(), ""
    )
    scheme = bis.SCHEMES_BY_KEY.get(scheme_key or "")

    if scheme is None:
        return CertificationResponse(
            is_number=standard.is_number,
            title=standard.title,
            mandatory=standard.qco_mandatory,
            qco_name=standard.qco_name,
            note=_MANAGEMENT_SYSTEM_NOTE
            if standard.department_code() in {"MSD", "SSD"}
            else (
                "No BIS product certification scheme is mapped to this standard. "
                + bis.VOLUNTARY_NOTE
            ),
        )

    if standard.qco_mandatory:
        note = (
            f"Conformity is MANDATORY: this product is covered by {standard.qco_name}. "
            if standard.qco_name
            else "Conformity is MANDATORY under a notified Quality Control Order. "
        ) + "Confirm the current QCO position on the BIS portal before you rely on this."
    else:
        note = bis.VOLUNTARY_NOTE

    return CertificationResponse(
        is_number=standard.is_number,
        title=standard.title,
        mandatory=standard.qco_mandatory,
        qco_name=standard.qco_name,
        scheme_key=scheme.key,
        scheme_name=scheme.name,
        applies_to=scheme.applies_to,
        steps=list(scheme.steps),
        note=note,
    )
