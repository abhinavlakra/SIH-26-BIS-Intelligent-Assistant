"""Curated knowledge about BIS *services*, as opposed to Indian Standards.

SIH26107 asks the assistant to cover four things the standards catalogue simply
does not contain: consumer-protection queries, hallmarking guidance, testing
laboratories, and the certification schemes. The catalogue holds IS numbers and
titles — ask it "how do I complain about a fake ISI mark" and it correctly
finds nothing, which reads as a failure even though the refusal is honest.

So this is a second, small knowledge base, kept deliberately separate from the
catalogue:

- Every entry carries a **source URL on bis.gov.in**, so answers stay
  source-backed and checkable — the thing the problem statement asks for and
  the reviewer's note singles out.
- No fees and no processing times. Those change, we cannot cite them, and a
  stale number in front of a BIS jury is worse than no number.
- Facts here were checked against the BIS site (hallmarking FAQ, BIS Care app
  page, laboratory pages) rather than written from memory.

Retrieval over these lives in `services/knowledge.py`.
"""

from typing import NamedTuple

BIS_ROOT = "https://www.bis.gov.in"


class ServiceEntry(NamedTuple):
    key: str
    topic: str  # hallmarking | laboratories | consumer | services
    question: str
    answer: str
    source: str
    keywords: tuple[str, ...]

    def embedding_text(self) -> str:
        return f"{self.question}\n{self.answer}\nKeywords: {', '.join(self.keywords)}"


HALLMARKING: tuple[ServiceEntry, ...] = (
    ServiceEntry(
        key="hallmark-what",
        topic="hallmarking",
        question="What is a BIS hallmark and what marks appear on hallmarked gold jewellery?",
        answer=(
            "A hallmark certifies the purity of a precious metal article. Hallmarked "
            "gold jewellery carries three marks: the BIS logo, the purity or fineness "
            "grade (for example 916 for 22 carat), and a six-digit alphanumeric "
            "Hallmark Unique Identification (HUID) number. Hallmarking is applied at a "
            "BIS-recognised Assaying and Hallmarking Centre, not by the jeweller."
        ),
        source=f"{BIS_ROOT}/hallmarking-overview/hallmarking-faqs/hallmarking-faq/",
        keywords=("hallmark", "gold", "jewellery", "purity", "BIS logo", "assaying"),
    ),
    ServiceEntry(
        key="hallmark-huid",
        topic="hallmarking",
        question="What is HUID and how do I check the HUID on my jewellery?",
        answer=(
            "HUID stands for Hallmark Unique Identification. It is a six-digit "
            "alphanumeric number, unique to each hallmarked article and traceable back "
            "to the hallmarking centre and the jeweller. You can verify it yourself "
            "using the 'Verify HUID' feature of the free BIS Care mobile app — if the "
            "app does not recognise the number, or returns a different article "
            "description, raise it with the jeweller and lodge a complaint with BIS."
        ),
        source=f"{BIS_ROOT}/bis-apps/",
        keywords=("HUID", "verify", "BIS Care", "unique identification", "traceable"),
    ),
    ServiceEntry(
        key="hallmark-purity",
        topic="hallmarking",
        question="Which gold purity grades can be hallmarked in India?",
        answer=(
            "Gold jewellery is hallmarked at these fineness grades: 999 (24 carat), "
            "958 (23 carat), 916 (22 carat), 750 (18 carat), 585 (14 carat) and 375 "
            "(9 carat). The number stamped on the article is the fineness in parts per "
            "thousand — 916 means 91.6% gold. Silver articles may also be hallmarked."
        ),
        source=f"{BIS_ROOT}/hallmarking-overview/hallmarking-faqs/hallmarking-faq/",
        keywords=("purity", "carat", "karat", "916", "fineness", "22 carat", "silver"),
    ),
    ServiceEntry(
        key="hallmark-mandatory",
        topic="hallmarking",
        question="Is hallmarking of gold jewellery mandatory?",
        answer=(
            "Hallmarking of gold jewellery and artefacts is mandatory for jewellers in "
            "the districts notified by the Government, and the notified list has been "
            "expanded in phases. Hallmarking of silver remains voluntary. Because the "
            "notified districts change, confirm the current position on the BIS "
            "hallmarking pages before relying on this."
        ),
        source=f"{BIS_ROOT}/hallmarking-overview/",
        keywords=("mandatory", "compulsory", "notified districts", "jeweller", "silver"),
    ),
    ServiceEntry(
        key="hallmark-jeweller",
        topic="hallmarking",
        question="How does a jeweller register with BIS for hallmarking?",
        answer=(
            "A jeweller registers with BIS through the hallmarking portal. Registration "
            "is granted against the premises and the purity grades the jeweller deals "
            "in. Registered jewellers must get articles hallmarked at a recognised "
            "Assaying and Hallmarking Centre before sale, and must display their BIS "
            "registration and the grades they stock."
        ),
        source=f"{BIS_ROOT}/hallmarking-overview/",
        keywords=("jeweller registration", "register", "hallmarking centre", "AHC"),
    ),
)

LABORATORIES: tuple[ServiceEntry, ...] = (
    ServiceEntry(
        key="lab-find",
        topic="laboratories",
        question="Where can I get my product tested? How do I find a BIS-recognised laboratory?",
        answer=(
            "BIS publishes a list of recognised and empanelled laboratories, including "
            "an Indian-Standard-wise list so you can look up laboratories by the IS "
            "number your product is tested against. The BIS Care app also has a 'Know "
            "Your Standards' feature that shows the laboratories available for a given "
            "product, and the locations of BIS laboratories and offices."
        ),
        source=f"{BIS_ROOT}/laboratorys/list-of-bis-recognized-lab/",
        keywords=(
            "laboratory", "lab", "testing", "test my product", "where to test",
            "recognised lab", "empanelled",
        ),
    ),
    ServiceEntry(
        key="lab-lrs",
        topic="laboratories",
        question="What is the BIS Laboratory Recognition Scheme?",
        answer=(
            "The Laboratory Recognition Scheme lets independent laboratories be "
            "recognised by BIS to test samples against Indian Standards on its behalf. "
            "Recognition is granted per product and per standard, against the "
            "laboratory's demonstrated test facilities and competence. Recognised "
            "laboratory test reports are accepted in BIS certification work."
        ),
        source=f"{BIS_ROOT}/laboratorys/",
        keywords=("laboratory recognition scheme", "LRS", "recognition", "accredited"),
    ),
    ServiceEntry(
        key="lab-bis-own",
        topic="laboratories",
        question="Does BIS run its own testing laboratories?",
        answer=(
            "Yes. BIS operates its own central and regional laboratories that test "
            "samples drawn during certification and surveillance, alongside the network "
            "of recognised and empanelled private laboratories. Test facilities and "
            "testing charges are published on the BIS laboratory pages."
        ),
        source=f"{BIS_ROOT}/laboratorys/",
        keywords=("BIS laboratory", "central lab", "regional lab", "testing charges"),
    ),
    ServiceEntry(
        key="lab-for-licence",
        topic="laboratories",
        question="Do I need a laboratory test report to get an ISI licence or CRS registration?",
        answer=(
            "Yes, testing is central to both. Under the Compulsory Registration Scheme "
            "the applicant submits a test report from a BIS-recognised laboratory with "
            "the application. Under the ISI mark scheme BIS inspects the factory and "
            "draws samples for independent testing, and the manufacturer is also "
            "expected to have in-house testing facilities and a factory quality plan."
        ),
        source=f"{BIS_ROOT}/product-certification/",
        keywords=("test report", "ISI licence", "CRS", "registration", "sample testing"),
    ),
)

CONSUMER: tuple[ServiceEntry, ...] = (
    ServiceEntry(
        key="consumer-complaint",
        topic="consumer",
        question="How do I complain about a defective product carrying the ISI mark?",
        answer=(
            "Complaints about a product bearing the Standard Mark can be lodged with "
            "BIS through the BIS Care app or the complaint facility on the BIS website, "
            "and at any BIS branch or regional office. Give the IS number, the licence "
            "or registration number printed on the product, and the batch details. BIS "
            "can draw samples, test them, and act against the licensee where the "
            "product does not conform."
        ),
        source=f"{BIS_ROOT}/consumer-affairs/",
        keywords=(
            "complaint", "complain", "grievance", "defective", "faulty", "ISI mark",
            "substandard", "redressal",
        ),
    ),
    ServiceEntry(
        key="consumer-biscare",
        topic="consumer",
        question="What is the BIS Care app and what can I do with it?",
        answer=(
            "BIS Care is the free BIS mobile app for consumers. It lets you verify the "
            "authenticity of an ISI-marked product with 'Verify Licence Details', check "
            "hallmarked jewellery with 'Verify HUID', look up any Indian Standard along "
            "with the licences issued against it and the laboratories that test for it "
            "with 'Know Your Standards', find BIS laboratory and office locations, and "
            "lodge a complaint."
        ),
        source=f"{BIS_ROOT}/bis-apps/",
        keywords=("BIS Care", "app", "mobile", "verify licence", "verify HUID"),
    ),
    ServiceEntry(
        key="consumer-verify-mark",
        topic="consumer",
        question="How do I check whether an ISI mark or a CRS registration is genuine?",
        answer=(
            "A genuine Standard Mark carries the IS number it is licensed against and "
            "the licence number (ISI) or the registration number (CRS, shown as "
            "'R-' followed by digits). Enter that number in the BIS Care app under "
            "'Verify Licence Details' — it will show the licensee and the product "
            "covered. A mark with no number, or a number the app does not recognise, "
            "should be reported to BIS."
        ),
        source=f"{BIS_ROOT}/bis-apps/",
        keywords=(
            "verify", "genuine", "fake ISI", "counterfeit", "licence number",
            "registration number", "standard mark",
        ),
    ),
    ServiceEntry(
        key="consumer-standard-mark",
        topic="consumer",
        question="What is the Standard Mark and what does it tell me?",
        answer=(
            "The Standard Mark is BIS's certification mark. Its presence means the "
            "manufacturer holds a valid BIS licence or registration for that product "
            "against a named Indian Standard, and that BIS carries out surveillance "
            "including sample testing. The ISI mark is the Standard Mark used under the "
            "product certification scheme; goods under the Compulsory Registration "
            "Scheme instead carry the standard mark with a registration number."
        ),
        source=f"{BIS_ROOT}/product-certification/",
        keywords=("standard mark", "ISI mark", "what does ISI mean", "certification mark"),
    ),
    ServiceEntry(
        key="consumer-awareness",
        topic="consumer",
        question="What does BIS do for consumer awareness and education?",
        answer=(
            "BIS runs consumer awareness programmes, supports Standards Clubs in "
            "schools and colleges to build standards awareness among students, and "
            "publishes consumer-facing guidance. Consumer associations are also "
            "represented on the technical committees that write Indian Standards."
        ),
        source=f"{BIS_ROOT}/consumer-affairs/",
        keywords=("consumer awareness", "standards club", "education", "students"),
    ),
)

OTHER_SERVICES: tuple[ServiceEntry, ...] = (
    ServiceEntry(
        key="services-overview",
        topic="services",
        question="What services does BIS provide besides publishing standards?",
        answer=(
            "Beyond standards formulation, BIS operates product certification (the ISI "
            "mark), the Foreign Manufacturers Certification Scheme, the Compulsory "
            "Registration Scheme, hallmarking of precious metals, laboratory services "
            "and the Laboratory Recognition Scheme, sale of Indian Standards, training "
            "through its national institute, consumer affairs activities, and it acts "
            "as India's WTO-TBT enquiry point."
        ),
        source=f"{BIS_ROOT}/",
        keywords=("services", "what does BIS do", "schemes", "WTO TBT", "training"),
    ),
    ServiceEntry(
        key="services-buy-standard",
        topic="services",
        question="How do I obtain or buy a copy of an Indian Standard?",
        answer=(
            "Indian Standards are sold by BIS and can be purchased through the BIS "
            "standards portal or from BIS offices. This assistant indexes only public "
            "catalogue metadata — IS number, title, scope summary and classification — "
            "because the full texts are copyrighted, so it can tell you which standard "
            "applies but cannot reproduce its clauses."
        ),
        source="https://standards.bis.gov.in/",
        keywords=("buy", "purchase", "copy of standard", "download", "obtain", "price"),
    ),
    ServiceEntry(
        key="services-standards-club",
        topic="services",
        question="What is a BIS Standards Club?",
        answer=(
            "A Standards Club is a BIS-supported group in a school or college that "
            "introduces students to standardisation and quality through activities, "
            "visits and projects. Institutions apply to BIS to form one, and BIS "
            "supports the club's activities."
        ),
        source=f"{BIS_ROOT}/",
        keywords=("standards club", "school", "college", "students", "membership"),
    ),
)

def _scheme_entries() -> tuple[ServiceEntry, ...]:
    """Turn each conformity assessment scheme into an askable entry.

    Derived from `bis_reference.SCHEMES` rather than restated here, so the
    scheme steps a user reads in chat are the same ones
    `/api/certification/{is}` returns. Two hand-maintained copies of the same
    procedure is how they drift apart.
    """
    from app import bis_reference

    # The hallmarking scheme belongs under hallmarking, not under the generic
    # services bucket — it outranks the hand-written hallmarking entries for a
    # question like "is my hallmark genuine", and labelling it "BIS services"
    # there would put the wrong topic tag on a correct answer.
    topic_for = {"hallmarking": "hallmarking"}

    entries = []
    for scheme in bis_reference.SCHEMES:
        steps = " ".join(f"{i}. {s}" for i, s in enumerate(scheme.steps, start=1))
        entries.append(
            ServiceEntry(
                key=f"scheme-{scheme.key}",
                topic=topic_for.get(scheme.key, "services"),
                question=f"What is {scheme.name}, and who needs it?",
                answer=(
                    f"{scheme.name}. Applies to: {scheme.applies_to} "
                    f"The steps are: {steps} "
                    "BIS certification is voluntary unless a Quality Control "
                    "Order makes conformity to that standard mandatory."
                ),
                source=f"{BIS_ROOT}/product-certification/",
                keywords=(
                    scheme.key.replace("_", " "),
                    scheme.name,
                    "scheme",
                    "certification",
                    "licence",
                    "how to apply",
                ),
            )
        )
    return tuple(entries)


CERTIFICATION_SCHEMES: tuple[ServiceEntry, ...] = _scheme_entries()

ALL_ENTRIES: tuple[ServiceEntry, ...] = (
    HALLMARKING + LABORATORIES + CONSUMER + OTHER_SERVICES + CERTIFICATION_SCHEMES
)

# Built from the entries themselves so a scheme filed under a different topic
# lands in the right bucket without a second list to keep in step.
BY_TOPIC: dict[str, tuple[ServiceEntry, ...]] = {
    topic: tuple(e for e in ALL_ENTRIES if e.topic == topic)
    for topic in ("hallmarking", "laboratories", "consumer", "services")
}

TOPIC_LABELS: dict[str, str] = {
    "hallmarking": "Hallmarking",
    "laboratories": "Testing laboratories",
    "consumer": "Consumer protection",
    "services": "BIS services",
}
