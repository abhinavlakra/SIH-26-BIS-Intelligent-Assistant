"""Multilingual support for query and answer.

Both problem statements require multilingual interaction. There is a catch that
determines the design: the embedding model is `all-MiniLM-L6-v2`, which is
**English-only**. A Hindi query embedded directly lands nowhere near the right
region of vector space, so retrieval — not generation — is the part that breaks
first.

So the query is translated to English *before* retrieval, and the answer is
generated in the requested language afterwards. Retrieval stays local and
English; only the two text transforms touch the model.

Degradation has two stages rather than one, because relying on a hosted call
for *retrieval* would make Hindi the one feature that stops working offline —
and the whole point of local embeddings is that nothing essential does:

1. Translate with the LLM when it is reachable. Best quality.
2. Otherwise fall back to a small **domain glossary**: map the Hindi terms this
   catalogue actually deals in onto their English equivalents and retrieve on
   those. Crude, entirely offline, and enough to land on the right standard for
   the vocabulary that matters here.
3. If neither works, say so rather than returning confident nonsense from a
   mis-embedded query.

Stage 2 is not hypothetical insurance. Anthropic-compatible routers can and do
refuse translation-shaped prompts — agentrouter.org returns `content-blocked`
for exactly this request — so on some deployments stage 1 never succeeds.

To make retrieval natively multilingual instead, swap the embedding model for
`paraphrase-multilingual-MiniLM-L12-v2` (same architecture, ~470 MB, still
fully local) and re-run `python -m app.ingestion.calibrate`.
"""

import re

from app.rag.llm import LLMUnavailable, get_provider

SUPPORTED = {"en": "English", "hi": "Hindi"}

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Hindi -> English for the vocabulary this catalogue is actually about:
# materials, products, processes and the compliance words around them. Scoped
# deliberately — a general dictionary would add noise, and the embedding only
# needs the content words to land in the right region.
_GLOSSARY: dict[str, str] = {
    # compliance & process
    "मानक": "standard",
    "भारतीय": "Indian",
    "प्रमाणन": "certification",
    "प्रमाणपत्र": "certificate",
    "अनिवार्य": "mandatory",
    "स्वैच्छिक": "voluntary",
    "गुणवत्ता": "quality",
    "परीक्षण": "test",
    "जाँच": "inspection",
    "सुरक्षा": "safety",
    "विनिर्देश": "specification",
    "आवश्यकता": "requirement",
    "अनुपालन": "compliance",
    "लाइसेंस": "licence",
    "पंजीकरण": "registration",
    "निर्माण": "manufacture construction",
    "निर्माता": "manufacturer",
    "उत्पाद": "product",
    "निविदा": "tender",
    "खरीद": "procurement",
    "उपभोक्ता": "consumer",
    "हॉलमार्किंग": "hallmarking",
    "हॉलमार्क": "hallmark",
    # materials
    "इस्पात": "steel",
    "स्टील": "steel",
    "लोहा": "iron",
    "सीमेंट": "cement",
    "कंक्रीट": "concrete",
    "ठोस": "concrete",
    "सरिया": "reinforcement bar",
    "ईंट": "brick",
    "रेत": "sand aggregate",
    "एल्युमिनियम": "aluminium",
    "तांबा": "copper",
    "प्लास्टिक": "plastic",
    "रबर": "rubber",
    "कपड़ा": "textile fabric",
    "वस्त्र": "textile",
    "कपास": "cotton",
    "सोना": "gold",
    "चांदी": "silver",
    "काग़ज़": "paper",
    "लकड़ी": "timber wood",
    "पेंट": "paint",
    "रंग": "paint colour",
    # products & domains
    "पानी": "water",
    "जल": "water",
    "पेयजल": "drinking water",
    "बोतल": "bottle",
    "दूध": "milk",
    "भोजन": "food",
    "खाद्य": "food",
    "तेल": "oil",
    "शहद": "honey",
    "हेलमेट": "helmet",
    "दोपहिया": "two wheeler motorcycle",
    "वाहन": "vehicle",
    "बिजली": "electrical",
    "विद्युत": "electrical",
    "तार": "cable wire",
    "केबल": "cable",
    "स्विच": "switch",
    "बल्ब": "lamp bulb",
    "एलईडी": "LED",
    "बैटरी": "battery",
    "मोटर": "motor",
    "पंप": "pump",
    "वाल्व": "valve",
    "पाइप": "pipe",
    "कुकर": "pressure cooker",
    "बर्तन": "utensils",
    "खिलौना": "toy",
    "खिलौने": "toys",
    "मास्क": "face mask",
    "दस्ताने": "gloves",
    "चिकित्सा": "medical",
    "अस्पताल": "hospital",
    "इमारत": "building",
    "भवन": "building",
    "भूकंप": "earthquake seismic",
    "भूकंपरोधी": "earthquake resistant",
    "नींव": "foundation",
    "पुल": "bridge",
    "सड़क": "road",
    "नहर": "canal",
    "बांध": "dam reservoir",
    "सिंचाई": "irrigation",
    "अग्नि": "fire",
    "आग": "fire",
    "प्रदूषण": "pollution",
    "पर्यावरण": "environment",
    "अपशिष्ट": "waste",
    "पुनर्चक्रण": "recycling",
    "सौर": "solar",
    "गैस": "gas LPG",
    "सिलेंडर": "cylinder",
    "पेट्रोल": "petrol petroleum",
    "डीज़ल": "diesel",
    "उर्वरक": "fertilizer",
    "साबुन": "soap detergent",
    "डिटर्जेंट": "detergent",
    "सूचना": "information",
    "प्रौद्योगिकी": "technology",
    "कंप्यूटर": "computer",
    "सॉफ़्टवेयर": "software",
}

# Grammatical particles worth dropping before the glossary lookup so they do
# not survive into the retrieval query as noise.
_HINDI_STOPWORDS = frozenset(
    """
    का की के को में से पर है हैं था थे और या यह वह क्या कौन कैसे कहाँ कब क्यों
    लिए एक हम मैं मेरा हमारा आप कोई सभी बहुत नहीं कर करना करने होता होती
    """.split()
)

_TRANSLATE_SYSTEM = (
    "You translate short product and standards-related queries into English. "
    "Reply with the translation only — no quotes, no explanation, no preamble. "
    "Keep any IS number, code or measurement exactly as written."
)


def normalise(lang: str | None) -> str:
    code = (lang or "en").strip().lower()[:2]
    return code if code in SUPPORTED else "en"


def is_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text or ""))


def answer_instruction(lang: str) -> str:
    """Appended to a system prompt so the answer comes back in the right language."""
    if normalise(lang) == "en":
        return ""
    return (
        f"\n\nRespond entirely in {SUPPORTED[normalise(lang)]}. Keep IS numbers, "
        "standard titles and technical terms in their original form — do not "
        "translate or transliterate them."
    )


def glossary_translate(query: str) -> str:
    """Map the Hindi domain terms in a query onto English. Offline, no model.

    Returns "" when nothing recognisable was found, so the caller can tell the
    difference between "translated approximately" and "could not translate".
    """
    words = re.findall(r"[\wऀ-ॿ]+", query)
    mapped: list[str] = []
    for word in words:
        if word in _HINDI_STOPWORDS:
            continue
        english = _GLOSSARY.get(word)
        if english:
            mapped.append(english)
        elif not _DEVANAGARI.search(word):
            # Latin tokens (an IS number, a brand, an English word) pass through.
            mapped.append(word)
    return " ".join(mapped)


def prepare_query(query: str, lang: str = "en") -> tuple[str, str]:
    """Return `(query_for_retrieval, note)`.

    `note` is empty when nothing needed saying. It is non-empty when the query
    could only be handled approximately, so the caller can be honest about why
    the results may be poor instead of silently returning noise.
    """
    # Latin script needs no transformation for retrieval, whatever language the
    # *answer* is meant to come back in.
    if not is_devanagari(query):
        return query, ""

    provider = get_provider()
    if provider.available:
        try:
            translated = provider.generate(_TRANSLATE_SYSTEM, query).strip()
            # Empty or absurdly long output is not a translation.
            if translated and len(translated) <= max(240, len(query) * 4):
                return translated, ""
        except LLMUnavailable:
            pass  # fall through to the offline glossary

    approximate = glossary_translate(query)
    if approximate:
        return approximate, (
            "Translated offline from a BIS domain glossary rather than by a "
            "language model, so retrieval is approximate. Ask in English for "
            "the most precise match."
        )

    return query, (
        "The retrieval index is English-only and this query could not be "
        "translated, so it was searched as written. Results may be incomplete "
        "— try the same question in English."
    )
