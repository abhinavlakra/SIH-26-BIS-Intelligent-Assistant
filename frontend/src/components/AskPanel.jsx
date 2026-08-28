import { useState } from "react";

import { askQuestion } from "../api.js";
import {
  ConfidenceLegend,
  CopyButton,
  ErrorNote,
  ExampleChips,
  Meter,
  Skeleton,
  StandardNumber,
  StatusTag,
} from "./Shared.jsx";

const EXAMPLES = {
  en: [
    {
      label: "Drinking water quality",
      value: "What standard covers drinking water quality?",
    },
    {
      label: "Earthquake design",
      value: "Which standards apply to earthquake resistant building design?",
    },
    {
      label: "Helmet certification",
      value: "Is BIS certification mandatory for two wheeler helmets?",
    },
    {
      // A BIS *service* question: answered from bis.gov.in documentation
      // rather than the catalogue, which holds no such content.
      label: "Check my hallmark",
      value: "How do I check if my gold jewellery hallmark is genuine?",
    },
    {
      label: "Find a test lab",
      value: "Which laboratory can test my product for BIS certification?",
    },
    {
      label: "Off-topic (declines)",
      value: "What are the customs duty rates for importing textiles into Brazil?",
    },
  ],
  hi: [
    {
      label: "पेयजल गुणवत्ता",
      value: "पेयजल की गुणवत्ता किस मानक में आती है?",
    },
    {
      label: "भूकंपरोधी डिज़ाइन",
      value: "भूकंपरोधी भवन डिज़ाइन पर कौन से मानक लागू होते हैं?",
    },
    {
      label: "हेलमेट प्रमाणन",
      value: "क्या दोपहिया हेलमेट के लिए बीआईएस प्रमाणन अनिवार्य है?",
    },
    {
      label: "हॉलमार्क जाँचें",
      value: "मैं कैसे जाँचूँ कि मेरे सोने के गहनों का हॉलमार्क असली है?",
    },
    {
      label: "परीक्षण प्रयोगशाला",
      value: "मेरे उत्पाद का परीक्षण किस प्रयोगशाला में हो सकता है?",
    },
    {
      label: "विषय से बाहर",
      value: "ब्राज़ील में कपड़ा आयात पर सीमा शुल्क दरें क्या हैं?",
    },
  ],
};

export default function AskPanel({ onModel, onOpen, lang, t }) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event?.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 3 || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await askQuestion({ query: trimmed, lang });
      setResult(response);
      onModel?.(response.used_model);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  };

  const pickExample = (value) => {
    setQuery(value);
    setResult(null);
    setError(null);
  };

  return (
    <section className="panel">
      <div className="panel__intro">
        <h2>{t("ask.title")}</h2>
        <p>{t("ask.lead")}</p>
      </div>

      <form className="form" onSubmit={submit}>
        <label className="sr-only" htmlFor="ask-input">
          {t("ask.title")}
        </label>
        <textarea
          id="ask-input"
          className="input input--area"
          rows={3}
          placeholder={t("ask.placeholder")}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) submit(event);
          }}
        />
        <div className="form__row">
          <ExampleChips
            examples={EXAMPLES[lang] ?? EXAMPLES.en}
            onPick={pickExample}
            disabled={loading}
            label={t("common.try")}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={loading || query.trim().length < 3}
          >
            {loading ? t("ask.submitting") : t("ask.submit")}
          </button>
        </div>
        <p className="form__hint">{t("common.submitHint")}</p>
      </form>

      {loading && <Skeleton rows={2} label={t("ask.submitting")} />}
      <ErrorNote error={error} onRetry={submit} t={t} />

      {result && !loading && (
        <div className="result">
          {result.grounded ? (
            <>
              <div className="answer">
                <div className="answer__header">
                  <h3>{t("ask.answer")}</h3>
                  <div className="result__actions">
                    <CopyButton text={result.answer} t={t} />
                    <span
                      className="answer__model"
                      title="Which engine produced this answer"
                    >
                      {result.used_model}
                    </span>
                  </div>
                </div>
                <div className="answer__body" aria-live="polite">
                  {result.answer.split("\n").map((line, index) =>
                    line.trim() ? <p key={index}>{line}</p> : null,
                  )}
                </div>
              </div>

              {/* A question about a BIS *service* is grounded in bis.gov.in
                  documentation rather than in an IS number, so its sources are
                  shown as links instead of standard cards. */}
              {result.services?.length > 0 && (
                <>
                  <h3 className="result__subhead">
                    {t("ask.sources")} <span>({result.services.length})</span>
                  </h3>
                  <ul className="cards">
                    {result.services.map((entry) => (
                      <li key={entry.key} className="card">
                        <div className="card__top">
                          <span className="tag tag--service">{entry.topic_label}</span>
                          <Meter value={entry.score} caption={t("common.relevance")} t={t} />
                        </div>
                        <h4 className="card__title">{entry.question}</h4>
                        <p className="card__scope">{entry.answer}</p>
                        <a
                          className="card__source"
                          href={entry.source}
                          target="_blank"
                          rel="noreferrer noopener"
                        >
                          {entry.source.replace("https://", "")}
                        </a>
                      </li>
                    ))}
                  </ul>
                  <p className="note__aside">{t("ask.servicesNote")}</p>
                </>
              )}

              {result.citations.length > 0 && (
                <>
              <h3 className="result__subhead">
                {t("ask.cited")} <span>({result.citations.length})</span>
              </h3>
              <ul className="cards">
                {result.citations.map((citation) => (
                  <li key={citation.is_number} className="card">
                    <div className="card__top">
                      <StandardNumber onOpen={onOpen}>{citation.is_number}</StandardNumber>
                      <StatusTag status={citation.status} />
                      <Meter value={citation.score} caption={t("common.relevance")} t={t} />
                    </div>
                    <h4 className="card__title">{citation.title}</h4>
                    {citation.scope && <p className="card__scope">{citation.scope}</p>}
                    {citation.sector && <p className="card__meta">{citation.sector}</p>}
                  </li>
                ))}
              </ul>
              <ConfidenceLegend t={t} />
                </>
              )}
            </>
          ) : (
            <div className="note note--empty">
              <strong>{t("ask.declined")}</strong>
              <p>{result.answer}</p>
              <p className="note__aside">{t("ask.declinedNote")}</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
