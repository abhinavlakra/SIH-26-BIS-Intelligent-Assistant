/**
 * Minimal two-language dictionary — English and Hindi.
 *
 * No i18n library and no external font: the UI must render fully offline, and
 * the stylesheet already carries "Noto Sans Devanagari" in its font stack.
 *
 * Only the interface chrome lives here. Answer text is translated server-side
 * by the model (see backend/app/services/language.py), because the catalogue
 * itself is English and IS numbers must never be transliterated.
 */

const STRINGS = {
  en: {
    "app.tagline": "AI assistant & recommendation engine for Indian Standards",
    "app.ministry": "Bureau of Indian Standards · Ministry of Consumer Affairs",

    "nav.overview": "Overview",
    "nav.recommend": "Find my standards",
    "nav.ask": "Ask a question",
    "nav.browse": "Browse catalogue",
    "nav.spec": "Check a tender",
    "nav.hint.overview": "What is indexed, and how much of BIS it covers",
    "nav.hint.recommend": "Product description → applicable IS codes",
    "nav.hint.ask": "Q&A grounded in the catalogue",
    "nav.hint.browse": "Filter the indexed standards",
    "nav.hint.spec": "Find outdated and incomplete references",
    "nav.recent": "Recent",
    "nav.clearRecent": "Clear",

    "status.indexed": "standards indexed",
    "status.departments": "BIS departments",
    "status.mandatory": "under a QCO",
    "status.extractive": "Extractive mode",
    "status.offline": "Backend offline — start it with",
    "status.connecting": "Connecting to backend…",
    "status.retry": "Retry",

    "overview.title": "What is in this catalogue",
    "overview.lead":
      "The full published BIS catalogue, collected from the official standards portal and indexed locally. Shown against the last published departmental totals so the scale is checkable.",
    "overview.kpi.indexed": "Standards indexed",
    "overview.kpi.departments": "Departments covered",
    "overview.kpi.mandatory": "Under a Quality Control Order",
    "overview.kpi.links": "Reference links mapped",
    "overview.coverage": "Coverage by BIS technical department",
    "overview.coverageNote":
      "Solid bar: indexed here. Faint bar: the official BIS published count. That figure is a June 2025 snapshot, so a current catalogue can exceed it.",
    "overview.icsNote":
      "ICS codes are not published by the BIS portal API, so this covers only the {n} hand-curated records of {total}.",
    "overview.ics": "Subject areas (ICS)",
    "overview.analytics": "What people are asking",
    "overview.unanswered": "Queries the catalogue could not answer",
    "overview.unansweredNote":
      "A standards-development gap signal for BIS, generated from real demand. Only query text and timing are stored — no IP address, no user identifier.",
    "overview.noQueries": "No queries yet. Ask something and it will appear here.",

    "recommend.title": "Find the standards for your product",
    "recommend.lead":
      "Describe what you make or procure, in plain language. You get the Indian Standards that apply, ranked, each with a reason, a confidence level and its certification obligation.",
    "recommend.placeholder":
      "e.g. I manufacture stainless steel insulated water bottles for retail sale",
    "recommend.submit": "Find standards",
    "recommend.submitting": "Matching…",
    "recommend.mandatory": "Certification required",
    "recommend.mandatoryNote":
      "A Quality Control Order makes conformity to these compulsory before sale.",
    "recommend.voluntary": "Also applicable",
    "recommend.voluntaryNote": "Conformity to these is voluntary unless a QCO is notified.",
    "recommend.empty": "No applicable standard found",
    "recommend.emptyBody":
      "Nothing in the indexed catalogue is close to that description. Try describing the physical product or material.",
    "recommend.viaGraph": "via reference graph",

    "ask.title": "Ask about a standard",
    "ask.lead":
      "Answered only from the indexed BIS catalogue, with the IS numbers it relied on. If the catalogue does not cover your question, it says so instead of guessing.",
    "ask.placeholder": "e.g. What standard covers drinking water quality?",
    "ask.submit": "Ask",
    "ask.submitting": "Searching…",
    "ask.answer": "Answer",
    "ask.cited": "Cited standards",
    "ask.sources": "BIS service guidance",
    "ask.servicesNote":
      "This is a BIS service question, so it is answered from BIS service documentation rather than from the standards catalogue. Confirm the current position on bis.gov.in.",
    "ask.declined": "Not covered by the indexed catalogue",
    "ask.declinedNote":
      "This is deliberate. Rather than answer with loosely-related standards, the assistant declines — a relevance threshold calibrated against the corpus sits between real matches and noise.",

    "browse.title": "Browse the indexed catalogue",
    "browse.lead":
      "Every standard we hold, filterable. This is a plain text filter — for meaning-based search use Find my standards or Ask a question.",
    "browse.search": "Filter by IS number, title or keyword",
    "browse.department": "Department",
    "browse.subject": "Subject sector",
    "browse.status": "Status",
    "browse.all": "All",
    "browse.mandatoryOnly": "Under a QCO only",
    "browse.results": "standards",
    "browse.none": "Nothing matches those filters.",
    "browse.clear": "Clear filters",
    "browse.prev": "Previous",
    "browse.next": "Next",
    "browse.page": "Page",

    "spec.title": "Check a tender specification",
    "spec.lead":
      "Paste a specification or tender text, one line item per line. Finds the standards each line needs, flags citations that are out of date, and lists normative references the document is missing.",
    "spec.placeholder":
      "1. Concrete work shall conform to IS 456:2000.\n2. Seismic design shall follow IS 1893:2002.\n3. Structural steelwork to be hot rolled medium tensile steel.",
    "spec.submit": "Analyse specification",
    "spec.uploadCta": "Upload a tender PDF",
    "spec.uploadHint": "or drag and drop it here — digital PDFs only, up to 10 MB",
    "spec.uploadPrivacy":
      "The file is read in memory and never stored. Scanned PDFs cannot be read.",
    "spec.sourcePages": "{n} page(s) read",
    "spec.sourceTruncated": "long document — only the first line items were analysed",
    "spec.submitting": "Analysing…",
    "spec.completeness": "Specification completeness",
    "spec.outdated": "Out-of-date references",
    "spec.outdatedNote":
      "These citations name a superseded edition, or omit the year entirely — the ambiguity that causes procurement disputes.",
    "spec.missing": "Missing normative references",
    "spec.missingNote":
      "Standards that the citations above normatively require, but this document never mentions.",
    "spec.mandatory": "Mandatory certification applies",
    "spec.lineItems": "Line items",
    "spec.cited": "Standards cited in the document",
    "spec.supersededBy": "superseded by",
    "spec.notIndexed": "not in our index",

    "detail.scope": "Scope",
    "detail.classification": "Classification",
    "detail.department": "Department",
    "detail.subject": "BIS subject sector",
    "detail.committee": "Technical committee",
    "detail.ics": "ICS codes",
    "detail.year": "Year",
    "detail.amendments": "Amendments",
    "detail.certification": "Certification pathway",
    "detail.mandatory": "Certification is mandatory",
    "detail.voluntary": "Certification is voluntary",
    "detail.appliesTo": "Applies to",
    "detail.steps": "How to get certified",
    "detail.graph": "Reference graph",
    "detail.graphNote":
      "Standards this one depends on. Dashed nodes are referenced by the standard but not in our index.",
    "detail.related": "Related standards",
    "detail.citedBy": "Referenced by",
    "detail.obtain": "Obtain this standard from the BIS portal",
    "detail.close": "Close",
    "detail.unverified": "Not yet verified against the official BIS catalogue",
    "detail.verified": "Verified against an official BIS publication",

    "common.try": "Try:",
    "common.submitHint": "Ctrl+Enter to submit",
    "common.copy": "Copy",
    "common.copied": "Copied",
    "common.export": "Export CSV",
    "common.confidence": "Confidence",
    "common.relevance": "Relevance",
    "common.high": "High",
    "common.medium": "Medium",
    "common.review": "Review needed",
    "common.mandatory": "Mandatory",
    "common.error": "Something went wrong",
    "common.tryAgain": "Try again",
    "common.of": "of",
    "common.language": "Language",

    "footer.note":
      "Indexes public BIS catalogue metadata (IS number, title, scope summary, sector). Full standard texts are copyrighted and not reproduced here.",
  },

  hi: {
    "app.tagline": "भारतीय मानकों के लिए एआई सहायक एवं अनुशंसा इंजन",
    "app.ministry": "भारतीय मानक ब्यूरो · उपभोक्ता मामले मंत्रालय",

    "nav.overview": "अवलोकन",
    "nav.recommend": "मेरे मानक खोजें",
    "nav.ask": "प्रश्न पूछें",
    "nav.browse": "सूची देखें",
    "nav.spec": "निविदा जाँचें",
    "nav.hint.overview": "क्या अनुक्रमित है, और बीआईएस का कितना भाग",
    "nav.hint.recommend": "उत्पाद विवरण → लागू आईएस कोड",
    "nav.hint.ask": "सूची पर आधारित प्रश्नोत्तर",
    "nav.hint.browse": "अनुक्रमित मानकों को छाँटें",
    "nav.hint.spec": "पुराने और अधूरे संदर्भ खोजें",
    "nav.recent": "हाल के",
    "nav.clearRecent": "साफ़ करें",

    "status.indexed": "मानक अनुक्रमित",
    "status.departments": "बीआईएस विभाग",
    "status.mandatory": "क्यूसीओ के अंतर्गत",
    "status.extractive": "निष्कर्षण मोड",
    "status.offline": "बैकएंड बंद है — इससे शुरू करें",
    "status.connecting": "बैकएंड से जुड़ रहे हैं…",
    "status.retry": "पुनः प्रयास",

    "overview.title": "इस सूची में क्या है",
    "overview.lead":
      "संपूर्ण प्रकाशित बीआईएस सूची, आधिकारिक मानक पोर्टल से एकत्रित और स्थानीय रूप से अनुक्रमित। पैमाना जाँचने योग्य रहे, इसलिए अंतिम प्रकाशित विभागीय संख्या के सापेक्ष दिखाई गई है।",
    "overview.kpi.indexed": "मानक अनुक्रमित",
    "overview.kpi.departments": "विभाग सम्मिलित",
    "overview.kpi.mandatory": "गुणवत्ता नियंत्रण आदेश के अंतर्गत",
    "overview.kpi.links": "संदर्भ लिंक मानचित्रित",
    "overview.coverage": "बीआईएस तकनीकी विभाग के अनुसार कवरेज",
    "overview.coverageNote":
      "गहरी पट्टी: यहाँ अनुक्रमित। हल्की पट्टी: आधिकारिक बीआईएस प्रकाशित संख्या, जो जून 2025 का आँकड़ा है — वर्तमान सूची इससे अधिक हो सकती है।",
    "overview.icsNote":
      "बीआईएस पोर्टल एपीआई आईसीएस कोड प्रकाशित नहीं करता, इसलिए यह केवल {total} में से {n} क्यूरेटेड रिकॉर्ड को कवर करता है।",
    "overview.ics": "विषय क्षेत्र (आईसीएस)",
    "overview.analytics": "लोग क्या पूछ रहे हैं",
    "overview.unanswered": "जिन प्रश्नों का उत्तर सूची नहीं दे सकी",
    "overview.unansweredNote":
      "बीआईएस के लिए मानक-विकास अंतराल का संकेत, वास्तविक माँग से उत्पन्न। केवल प्रश्न-पाठ और समय संग्रहित — कोई आईपी पता या उपयोगकर्ता पहचान नहीं।",
    "overview.noQueries": "अभी कोई प्रश्न नहीं। कुछ पूछें और वह यहाँ दिखेगा।",

    "recommend.title": "अपने उत्पाद के मानक खोजें",
    "recommend.lead":
      "आप जो बनाते या खरीदते हैं उसका सरल भाषा में वर्णन करें। आपको लागू भारतीय मानक क्रमबद्ध रूप से मिलेंगे — कारण, विश्वास स्तर और प्रमाणन दायित्व सहित।",
    "recommend.placeholder":
      "जैसे: मैं खुदरा बिक्री के लिए स्टेनलेस स्टील की इंसुलेटेड पानी की बोतलें बनाता हूँ",
    "recommend.submit": "मानक खोजें",
    "recommend.submitting": "मिलान हो रहा है…",
    "recommend.mandatory": "प्रमाणन अनिवार्य",
    "recommend.mandatoryNote":
      "गुणवत्ता नियंत्रण आदेश के कारण बिक्री से पूर्व इनका अनुपालन अनिवार्य है।",
    "recommend.voluntary": "अन्य लागू मानक",
    "recommend.voluntaryNote":
      "जब तक क्यूसीओ अधिसूचित न हो, इनका अनुपालन स्वैच्छिक है।",
    "recommend.empty": "कोई लागू मानक नहीं मिला",
    "recommend.emptyBody":
      "अनुक्रमित सूची में उस विवरण के निकट कुछ नहीं है। भौतिक उत्पाद या सामग्री का वर्णन करके देखें।",
    "recommend.viaGraph": "संदर्भ ग्राफ़ से",

    "ask.title": "मानक के बारे में पूछें",
    "ask.lead":
      "उत्तर केवल अनुक्रमित बीआईएस सूची से, प्रयुक्त आईएस संख्याओं सहित। यदि सूची में उत्तर नहीं है, तो अनुमान लगाने के बजाय वह स्पष्ट कह देता है।",
    "ask.placeholder": "जैसे: पेयजल गुणवत्ता किस मानक में आती है?",
    "ask.submit": "पूछें",
    "ask.submitting": "खोज रहे हैं…",
    "ask.answer": "उत्तर",
    "ask.cited": "उद्धृत मानक",
    "ask.sources": "बीआईएस सेवा मार्गदर्शन",
    "ask.servicesNote":
      "यह बीआईएस सेवा से जुड़ा प्रश्न है, इसलिए उत्तर मानक सूची के बजाय बीआईएस सेवा दस्तावेज़ों से दिया गया है। वर्तमान स्थिति bis.gov.in पर देखें।",
    "ask.declined": "अनुक्रमित सूची में सम्मिलित नहीं",
    "ask.declinedNote":
      "यह जानबूझकर है। ढीले-ढाले संबंधित मानकों से उत्तर देने के बजाय सहायक मना कर देता है — सूची के अनुसार अंशांकित एक प्रासंगिकता सीमा वास्तविक मिलान और शोर के बीच स्थित है।",

    "browse.title": "अनुक्रमित सूची देखें",
    "browse.lead":
      "हमारे पास मौजूद सभी मानक, छाँटने योग्य। यह सामान्य पाठ फ़िल्टर है — अर्थ-आधारित खोज के लिए 'मेरे मानक खोजें' या 'प्रश्न पूछें' का उपयोग करें।",
    "browse.search": "आईएस संख्या, शीर्षक या कीवर्ड से छाँटें",
    "browse.department": "विभाग",
    "browse.subject": "विषय क्षेत्र",
    "browse.status": "स्थिति",
    "browse.all": "सभी",
    "browse.mandatoryOnly": "केवल क्यूसीओ के अंतर्गत",
    "browse.results": "मानक",
    "browse.none": "इन फ़िल्टरों से कुछ मेल नहीं खाता।",
    "browse.clear": "फ़िल्टर हटाएँ",
    "browse.prev": "पिछला",
    "browse.next": "अगला",
    "browse.page": "पृष्ठ",

    "spec.title": "निविदा विनिर्देश जाँचें",
    "spec.lead":
      "विनिर्देश या निविदा पाठ चिपकाएँ, प्रति पंक्ति एक मद। प्रत्येक पंक्ति के लिए आवश्यक मानक खोजता है, पुराने उद्धरण चिह्नित करता है, और अनुपस्थित सामान्य संदर्भ सूचीबद्ध करता है।",
    "spec.placeholder":
      "1. कंक्रीट कार्य IS 456:2000 के अनुरूप होगा।\n2. भूकंपीय डिज़ाइन IS 1893:2002 के अनुसार।\n3. संरचनात्मक इस्पात कार्य हॉट रोल्ड मध्यम तन्य इस्पात।",
    "spec.submit": "विनिर्देश जाँचें",
    "spec.uploadCta": "निविदा पीडीएफ़ अपलोड करें",
    "spec.uploadHint": "या यहाँ खींचकर छोड़ें — केवल डिजिटल पीडीएफ़, अधिकतम 10 एमबी",
    "spec.uploadPrivacy":
      "फ़ाइल केवल मेमोरी में पढ़ी जाती है, कभी संग्रहीत नहीं होती। स्कैन की गई पीडीएफ़ नहीं पढ़ी जा सकती।",
    "spec.sourcePages": "{n} पृष्ठ पढ़े गए",
    "spec.sourceTruncated": "लंबा दस्तावेज़ — केवल आरंभिक मदें जाँची गईं",
    "spec.submitting": "जाँच हो रही है…",
    "spec.completeness": "विनिर्देश पूर्णता",
    "spec.outdated": "पुराने संदर्भ",
    "spec.outdatedNote":
      "ये उद्धरण अधिक्रमित संस्करण का नाम लेते हैं, या वर्ष पूरी तरह छोड़ देते हैं — यही अस्पष्टता खरीद विवाद उत्पन्न करती है।",
    "spec.missing": "अनुपस्थित सामान्य संदर्भ",
    "spec.missingNote":
      "जिन मानकों की उपरोक्त उद्धरणों को आवश्यकता है, पर इस दस्तावेज़ में उल्लेख नहीं है।",
    "spec.mandatory": "अनिवार्य प्रमाणन लागू",
    "spec.lineItems": "पंक्ति मदें",
    "spec.cited": "दस्तावेज़ में उद्धृत मानक",
    "spec.supersededBy": "द्वारा अधिक्रमित",
    "spec.notIndexed": "हमारे सूचकांक में नहीं",

    "detail.scope": "क्षेत्र",
    "detail.classification": "वर्गीकरण",
    "detail.department": "विभाग",
    "detail.subject": "बीआईएस विषय क्षेत्र",
    "detail.committee": "तकनीकी समिति",
    "detail.ics": "आईसीएस कोड",
    "detail.year": "वर्ष",
    "detail.amendments": "संशोधन",
    "detail.certification": "प्रमाणन मार्ग",
    "detail.mandatory": "प्रमाणन अनिवार्य है",
    "detail.voluntary": "प्रमाणन स्वैच्छिक है",
    "detail.appliesTo": "किस पर लागू",
    "detail.steps": "प्रमाणन कैसे प्राप्त करें",
    "detail.graph": "संदर्भ ग्राफ़",
    "detail.graphNote":
      "जिन मानकों पर यह निर्भर है। बिंदुदार नोड मानक द्वारा संदर्भित हैं पर हमारे सूचकांक में नहीं।",
    "detail.related": "संबंधित मानक",
    "detail.citedBy": "द्वारा संदर्भित",
    "detail.obtain": "यह मानक बीआईएस पोर्टल से प्राप्त करें",
    "detail.close": "बंद करें",
    "detail.unverified": "आधिकारिक बीआईएस सूची के विरुद्ध अभी सत्यापित नहीं",
    "detail.verified": "आधिकारिक बीआईएस प्रकाशन से सत्यापित",

    "common.try": "आज़माएँ:",
    "common.submitHint": "भेजने के लिए Ctrl+Enter",
    "common.copy": "कॉपी",
    "common.copied": "कॉपी हो गया",
    "common.export": "सीएसवी निर्यात",
    "common.confidence": "विश्वास",
    "common.relevance": "प्रासंगिकता",
    "common.high": "उच्च",
    "common.medium": "मध्यम",
    "common.review": "समीक्षा आवश्यक",
    "common.mandatory": "अनिवार्य",
    "common.error": "कुछ गड़बड़ हुई",
    "common.tryAgain": "पुनः प्रयास करें",
    "common.of": "में से",
    "common.language": "भाषा",

    "footer.note":
      "सार्वजनिक बीआईएस सूची मेटाडेटा अनुक्रमित करता है (आईएस संख्या, शीर्षक, क्षेत्र सारांश, प्रभाग)। पूर्ण मानक पाठ कॉपीराइट हैं और यहाँ पुनरुत्पादित नहीं किए गए।",
  },
};

export const LANGUAGES = [
  { code: "en", label: "English", short: "EN" },
  { code: "hi", label: "हिन्दी", short: "हिं" },
];

/** Returns a `t(key)` lookup that falls back to English, then to the key. */
export function translator(lang) {
  const primary = STRINGS[lang] ?? STRINGS.en;
  return (key) => primary[key] ?? STRINGS.en[key] ?? key;
}
