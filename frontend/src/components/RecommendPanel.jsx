import { useState } from "react";

import { recommendStandards } from "../api.js";
import {
  ConfidenceLegend,
  DownloadCsvButton,
  ErrorNote,
  ExampleChips,
  Meter,
  Skeleton,
  StandardNumber,
  StatusTag,
} from "./Shared.jsx";

const EXAMPLES = [
  {
    label: "Earthquake-resistant flats",
    value:
      "We are designing an earthquake resistant reinforced concrete apartment block in a hilly seismic zone",
  },
  {
    label: "Steel water bottles",
    value:
      "I manufacture stainless steel insulated water bottles for retail sale",
  },
  {
    label: "Two-wheeler helmets",
    value: "My company makes protective helmets for motorcycle riders",
  },
  {
    label: "LED bulb factory",
    value: "Our MSME assembles LED bulbs and power adapters for household lighting",
  },
];

export default function RecommendPanel({ onModel, onOpen, lang, t }) {
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event?.preventDefault();
    const trimmed = description.trim();
    if (trimmed.length < 5 || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await recommendStandards({ description: trimmed, lang });
      setResult(response);
      onModel?.(response.used_model);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  };

  const pickExample = (value) => {
    setDescription(value);
    setResult(null);
    setError(null);
  };

  // The split that makes this actionable: an obligation is not the same thing
  // as a suggestion, and the user needs to see which is which at a glance.
  const mandatory = result?.recommendations.filter((item) => item.qco_mandatory) ?? [];
  const voluntary = result?.recommendations.filter((item) => !item.qco_mandatory) ?? [];

  return (
    <section className="panel">
      <div className="panel__intro">
        <h2>{t("recommend.title")}</h2>
        <p>{t("recommend.lead")}</p>
      </div>

      <form className="form" onSubmit={submit}>
        <label className="sr-only" htmlFor="recommend-input">
          {t("recommend.title")}
        </label>
        <textarea
          id="recommend-input"
          className="input input--area"
          rows={3}
          placeholder={t("recommend.placeholder")}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) submit(event);
          }}
        />
        <div className="form__row">
          <ExampleChips
            examples={EXAMPLES}
            onPick={pickExample}
            disabled={loading}
            label={t("common.try")}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={loading || description.trim().length < 5}
          >
            {loading ? t("recommend.submitting") : t("recommend.submit")}
          </button>
        </div>
        <p className="form__hint">{t("common.submitHint")}</p>
      </form>

      {loading && <Skeleton rows={3} label={t("recommend.submitting")} />}
      <ErrorNote error={error} onRetry={submit} t={t} />

      {result && !loading && (
        <div className="result">
          {result.recommendations.length === 0 ? (
            <div className="note note--empty">
              <strong>{t("recommend.empty")}</strong>
              <p>{t("recommend.emptyBody")}</p>
            </div>
          ) : (
            <>
              <div className="result__head">
                <p className="result__count" aria-live="polite">
                  <strong>{result.recommendations.length}</strong>{" "}
                  {t("browse.results")}
                </p>
                <div className="result__actions">
                  <DownloadCsvButton
                    rows={result.recommendations.map((item) => ({
                      is_number: item.is_number,
                      title: item.title,
                      confidence: item.confidence,
                      mandatory: item.qco_mandatory ? "yes" : "no",
                      qco: item.qco_name,
                      why: item.why,
                    }))}
                    filename="manakmitra-recommendations.csv"
                    t={t}
                  />
                  <span className="answer__model">{result.used_model}</span>
                </div>
              </div>

              {mandatory.length > 0 && (
                <Group
                  title={t("recommend.mandatory")}
                  note={t("recommend.mandatoryNote")}
                  tone="mandatory"
                  items={mandatory}
                  onOpen={onOpen}
                  t={t}
                />
              )}

              {voluntary.length > 0 && (
                <Group
                  title={t("recommend.voluntary")}
                  note={t("recommend.voluntaryNote")}
                  tone="voluntary"
                  items={voluntary}
                  onOpen={onOpen}
                  t={t}
                />
              )}

              <ConfidenceLegend t={t} />
              <p className="result__footnote">{t("footer.note")}</p>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function Group({ title, note, tone, items, onOpen, t }) {
  return (
    <section className={`group group--${tone}`}>
      <header className="group__head">
        <h3 className="group__title">
          {title} <span className="group__count">({items.length})</span>
        </h3>
        <p className="group__note">{note}</p>
      </header>

      <ol className="cards cards--ranked">
        {items.map((item, index) => (
          <li key={item.is_number} className="card card--rank">
            <span className="card__rank" aria-hidden="true">
              {index + 1}
            </span>
            <div className="card__body">
              <div className="card__top">
                <StandardNumber onOpen={onOpen}>{item.is_number}</StandardNumber>
                <StatusTag status={item.status} />
                {item.via !== "semantic" && (
                  <span className="tag tag--via" title={`Pulled in as a normative reference of ${item.via}`}>
                    {t("recommend.viaGraph")}
                  </span>
                )}
                <Meter value={item.confidence} caption={t("common.confidence")} t={t} />
              </div>

              <h4 className="card__title">{item.title}</h4>
              <p className="card__why">
                <span className="card__why-label">Why</span> {item.why}
              </p>

              {item.qco_mandatory && item.qco_name && (
                <p className="card__qco">
                  <span className="card__qco-label">QCO</span> {item.qco_name}
                </p>
              )}

              {item.normative_refs?.length > 0 && (
                <p className="card__refs">
                  <span className="card__refs-label">Requires</span>
                  {item.normative_refs.map((ref) => (
                    <button
                      key={ref}
                      type="button"
                      className="is-number is-number--sm is-number--link"
                      onClick={() => onOpen(ref)}
                    >
                      {ref}
                    </button>
                  ))}
                </p>
              )}

              {item.sector && <p className="card__meta">{item.sector}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
