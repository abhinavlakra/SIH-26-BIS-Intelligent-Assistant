"""Multilingual handling (tests run with no LLM, so the offline path is exercised)."""

from app.rag.retriever import search
from app.services import language


def test_english_queries_pass_through_untouched():
    query = "drinking water quality limits"
    assert language.prepare_query(query, "en") == (query, "")
    # An English query with a Hindi *answer* language still needs no transform.
    assert language.prepare_query(query, "hi") == (query, "")


def test_devanagari_is_detected():
    assert language.is_devanagari("पेयजल की गुणवत्ता")
    assert not language.is_devanagari("drinking water quality")
    assert not language.is_devanagari("IS 10500:2012")


def test_unsupported_languages_fall_back_to_english():
    assert language.normalise("fr") == "en"
    assert language.normalise(None) == "en"
    assert language.normalise("HI") == "hi"


def test_answer_instruction_is_empty_for_english():
    assert language.answer_instruction("en") == ""
    assert "Hindi" in language.answer_instruction("hi")


# --- the offline glossary path -------------------------------------------


def test_glossary_maps_domain_terms_to_english():
    assert language.glossary_translate("पेयजल की गुणवत्ता") == "drinking water quality"
    assert language.glossary_translate("स्टील के बर्तन") == "steel utensils"


def test_glossary_drops_grammatical_particles():
    """'के', 'लिए', 'है' carry no retrieval signal and must not survive."""
    result = language.glossary_translate("क्या हेलमेट के लिए प्रमाणन अनिवार्य है?")
    assert result == "helmet certification mandatory"


def test_glossary_passes_latin_tokens_through():
    """An IS number inside a Hindi sentence must survive intact."""
    assert "456" in language.glossary_translate("IS 456 के लिए मानक")


def test_glossary_returns_empty_when_nothing_is_recognised():
    assert language.glossary_translate("क्ष त्र ज्ञ") == ""


def test_hindi_query_retrieves_the_right_standard_with_no_llm():
    """The point of the offline path: Hindi must work with the network off."""
    retrieval_query, note = language.prepare_query(
        "पेयजल की गुणवत्ता किस मानक में आती है?", "hi"
    )
    assert "drinking water" in retrieval_query
    # The approximation is disclosed rather than passed off as a translation.
    assert "glossary" in note

    hits = search(retrieval_query)
    assert hits, "expected the translated query to retrieve something"
    assert hits[0][0].is_number == "IS 10500:2012"


def test_hindi_query_for_something_uncovered_still_declines():
    """Translation must not become a way around the relevance floor.

    There is no helmet standard in the test corpus, so the honest answer is
    still "nothing matches" even though the query translated cleanly.
    """
    retrieval_query, _note = language.prepare_query(
        "क्या दोपहिया हेलमेट के लिए प्रमाणन अनिवार्य है?", "hi"
    )
    assert "helmet" in retrieval_query
    assert search(retrieval_query) == []


def test_untranslatable_devanagari_is_reported_honestly():
    _query, note = language.prepare_query("क्ष त्र ज्ञ", "hi")
    assert "could not be translated" in note
