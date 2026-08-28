"""Measure the signal/noise score distributions the relevance floors sit between.

The two floors in `rag/retriever.py` are not arbitrary - they sit in the empty
gap between the scores of genuinely relevant queries and the scores of off-topic
ones. That gap moves when the corpus changes: more documents means more chances
for a spurious near-match, which raises the noise ceiling.

Run this after any material change to the corpus, and move the floors if the
gap has shifted. Do not carry the constants over blindly.

    python -m app.ingestion.calibrate
"""

from rag.retriever import RECOMMEND_FLOOR, RELEVANCE_FLOOR, search

# Questions a user would genuinely ask of this catalogue.
RELEVANT_QUERIES = [
    "drinking water quality limits",
    "reinforced concrete design code",
    "earthquake resistant building design",
    "stainless steel for food utensils",
    "electrical wiring installation practice",
    "miniature circuit breaker requirements",
    "surgical face mask requirements",
    "two wheeler helmet standard",
    "pressure cooker safety",
    "quality management system requirements",
    "compostable plastic specification",
    "cotton sewing thread",
    "LPG cylinder gas specification",
    "canal earthwork irrigation",
    "steel fasteners mechanical properties",
]

# Verbose, first-person product descriptions - the recommend endpoint's real
# input shape, which scores markedly lower than a terse query.
PRODUCT_DESCRIPTIONS = [
    "I manufacture stainless steel insulated water bottles for retail sale",
    "We are setting up a small packaged drinking water bottling plant in a rural district",
    "Our MSME assembles LED bulbs and power adapters for household lighting",
    "We are designing an earthquake resistant reinforced concrete apartment block",
    "My company makes protective helmets for motorcycle riders",
    "We produce compostable carry bags for a municipal corporation tender",
]

# Nothing in a standards catalogue should answer these.
OFF_TOPIC_QUERIES = [
    "who won the 2018 football world cup",
    "best pizza recipe with sourdough base",
    "python asyncio event loop debugging",
    "how do I train a puppy to sit",
    "cheapest flights from delhi to singapore",
    "what is the capital of argentina",
    "recommend a good restaurant in mumbai for dinner",
    "how do I reset my email password",
]

# Queries whose *subject* is outside the catalogue but whose *wording* overlaps
# it. These are the hard cases and they set the real ceiling the chat floor has
# to clear — a question about customs duty is not answerable from a standards
# catalogue, but it says "textiles", and at 24k records there are 1,634 textile
# standards for it to land on.
#
# Kept separate from the list above because conflating them hides what is
# actually happening: the clearly off-topic band tops out around 0.29, the
# domain-adjacent band around 0.49, and only the second one constrains the
# chat floor.
DOMAIN_ADJACENT_QUERIES = [
    "customs duty rates for importing textiles into Brazil",
    "lyrics to a popular hindi film song",
    "import tariff paperwork for shipping steel overseas",
]


def _top_score(query: str, floor: float) -> tuple[float, str]:
    hits = search(query, floor=floor)
    if not hits:
        return 0.0, "-"
    standard, score = hits[0]
    return score, standard.is_number


def _report(label: str, queries: list[str], floor: float) -> list[float]:
    print(f"\n{label}")
    print("-" * 78)
    scores = []
    for query in queries:
        # Score with the floor open so the true distribution is visible.
        score, is_number = _top_score(query, floor=0.0)
        scores.append(score)
        flag = " " if score >= floor else "!"
        print(f"  {flag} {score:.3f}  {query[:46]:<46} {is_number}")
    return scores


def main() -> None:
    relevant = _report("RELEVANT QUERIES (want: comfortably above the chat floor)",
                       RELEVANT_QUERIES, RELEVANCE_FLOOR)
    products = _report("PRODUCT DESCRIPTIONS (want: above the recommend floor)",
                       PRODUCT_DESCRIPTIONS, RECOMMEND_FLOOR)
    noise = _report("CLEARLY OFF-TOPIC (want: below both floors)",
                    OFF_TOPIC_QUERIES, RECOMMEND_FLOOR)
    adjacent = _report("DOMAIN-ADJACENT (want: below the chat floor)",
                       DOMAIN_ADJACENT_QUERIES, RELEVANCE_FLOOR)

    signal_floor = min(relevant)
    product_floor = min(products)
    noise_ceiling = max(noise)
    adjacent_ceiling = max(adjacent)

    print("\n" + "=" * 78)
    print(f"  relevant queries      {min(relevant):.3f} - {max(relevant):.3f}")
    print(f"  product descriptions  {min(products):.3f} - {max(products):.3f}")
    print(f"  domain-adjacent       {min(adjacent):.3f} - {adjacent_ceiling:.3f}")
    print(f"  clearly off-topic     {min(noise):.3f} - {noise_ceiling:.3f}")
    print()
    print(f"  RELEVANCE_FLOOR  = {RELEVANCE_FLOOR}   (chat)")
    print(f"  RECOMMEND_FLOOR  = {RECOMMEND_FLOOR}   (recommend)")
    print()

    ok = True

    # Chat refuses rather than guesses, so its floor has to clear the hard
    # cases, not just the easy ones.
    if adjacent_ceiling >= signal_floor:
        print("  FAIL: NO GAP for chat: the weakest relevant query scores below the")
        print("        strongest domain-adjacent one. No floor separates them —")
        print("        improve retrieval before touching the constants.")
        ok = False
    else:
        print(f"  chat gap:      {adjacent_ceiling:.3f} ... {signal_floor:.3f}"
              f"   (width {signal_floor - adjacent_ceiling:.3f})")
        if not (adjacent_ceiling < RELEVANCE_FLOOR < signal_floor):
            print(f"  FAIL: RELEVANCE_FLOOR is outside that gap - set it near "
                  f"{(adjacent_ceiling + signal_floor) / 2:.2f}")
            ok = False

    # Recommend is deliberately recall-biased: its input is a product
    # description, not a question, and returning a weak candidate with a visibly
    # low confidence beats refusing a real product. So it only has to clear the
    # *clearly* off-topic band — it may well answer a domain-adjacent query, and
    # that is the intended trade-off, not a defect.
    if noise_ceiling >= product_floor:
        print("  FAIL: NO GAP for recommend: the weakest product description scores")
        print("        below the strongest off-topic query.")
        ok = False
    else:
        print(f"  recommend gap: {noise_ceiling:.3f} ... {product_floor:.3f}"
              f"   (width {product_floor - noise_ceiling:.3f})")
        if not (noise_ceiling < RECOMMEND_FLOOR <= product_floor):
            print(f"  FAIL: RECOMMEND_FLOOR is outside that window - set it near "
                  f"{(noise_ceiling + product_floor) / 2:.2f}")
            ok = False

    print("\n  " + ("OK: both floors sit correctly" if ok else "FAIL: adjust the floors above"))


if __name__ == "__main__":
    main()
