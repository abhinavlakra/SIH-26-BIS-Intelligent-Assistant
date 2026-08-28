import { useRef, useState } from "react";

import { analyzeSpec, analyzeSpecFile } from "../api.js";
import {
  DownloadCsvButton,
  ErrorNote,
  ExampleChips,
  QcoBadge,
  Skeleton,
  StandardNumber,
} from "./Shared.jsx";

const SAMPLE = `1. Construction of a four-storey reinforced concrete office building.
2. Concrete work shall conform to IS 456:2000 throughout the structure.
3. Seismic design of the frame shall follow IS 1893:2002.
4. Ductile detailing as per IS 13920.
5. All structural steelwork to be hot rolled medium tensile steel.
6. Supply and installation of internal electrical wiring and distribution boards.`;

const EXAMPLES = [{ label: "Sample building tender", value: SAMPLE }];

/**
 * Tender / specification checker.
 *
 * The problem statement names two causes of procurement disputes — incomplete
 * specifications and outdated standard references — so those two findings lead
 * the results, above the per-line matches.
 */
export default function SpecPanel({ onModel, onOpen, t }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);

  const run = async (task) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await task();
      setResult(response);
      onModel?.(response.used_model);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  };

  const submit = async (event) => {
    event?.preventDefault();
    const trimmed = text.trim();
    if (trimmed.length < 20 || loading) return;
    await run(() => analyzeSpec({ text: trimmed }));
  };

  const submitFile = async (file) => {
    if (!file || loading) return;
    await run(() => analyzeSpecFile(file));
  };

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    submitFile(event.dataTransfer?.files?.[0]);
  };

  return (
    <section className="panel">
      <div className="panel__intro">
        <h2>{t("spec.title")}</h2>
        <p>{t("spec.lead")}</p>
      </div>

      <form className="form" onSubmit={submit}>
        <label className="sr-only" htmlFor="spec-input">
          {t("spec.title")}
        </label>
        <textarea
          id="spec-input"
          className="input input--area input--tall"
          rows={8}
          placeholder={t("spec.placeholder")}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) submit(event);
          }}
        />
        <div className="form__row">
          <ExampleChips
            examples={EXAMPLES}
            onPick={setText}
            disabled={loading}
            label={t("common.try")}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={loading || text.trim().length < 20}
          >
            {loading ? t("spec.submitting") : t("spec.submit")}
          </button>
        </div>
        <p className="form__hint">{t("common.submitHint")}</p>
      </form>

      {/* Real tenders are PDFs. Requiring copy-paste was the gap between this
          feature and how procurement actually works. */}
      <div
        className={`dropzone ${dragging ? "dropzone--over" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          onChange={(event) => {
            submitFile(event.target.files?.[0]);
            // Let the same file be re-selected after an error.
            event.target.value = "";
          }}
        />
        <button
          type="button"
          className="dropzone__button"
          onClick={() => fileInput.current?.click()}
          disabled={loading}
        >
          {t("spec.uploadCta")}
        </button>
        <p className="dropzone__hint">{t("spec.uploadHint")}</p>
        <p className="dropzone__privacy">{t("spec.uploadPrivacy")}</p>
      </div>

      {loading && <Skeleton rows={3} label={t("spec.submitting")} />}
      <ErrorNote error={error} onRetry={submit} t={t} />

      {result && !loading && (
        <div className="result">
          {result.source?.kind === "pdf" && (
            <p className="note note--source">
              <strong>{result.source.filename}</strong>
              {" · "}
              {t("spec.sourcePages").replace("{n}", result.source.pages)}
              {result.source.truncated && ` · ${t("spec.sourceTruncated")}`}
            </p>
          )}

          <CompletenessGauge value={result.completeness} t={t} />

          {result.outdated_citations.length > 0 && (
            <section className="finding finding--warn">
              <h3>
                {t("spec.outdated")}{" "}
                <span className="finding__count">({result.outdated_citations.length})</span>
              </h3>
              <p className="finding__note">{t("spec.outdatedNote")}</p>
              <ul className="finding__list">
                {result.outdated_citations.map((entry) => (
                  <li key={entry.cited_as}>
                    <code className="is-number is-number--stale">{entry.cited_as}</code>
                    <span className="finding__arrow">→ {t("spec.supersededBy")}</span>
                    <StandardNumber onOpen={onOpen}>{entry.superseded_by}</StandardNumber>
                    {entry.amendment_count > 0 && (
                      <span className="finding__meta">
                        {entry.amendment_count} amendment(s)
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {result.missing_normative_refs.length > 0 && (
            <section className="finding finding--info">
              <h3>
                {t("spec.missing")}{" "}
                <span className="finding__count">({result.missing_normative_refs.length})</span>
              </h3>
              <p className="finding__note">{t("spec.missingNote")}</p>
              <div className="finding__chips">
                {result.missing_normative_refs.map((ref) => (
                  <StandardNumber key={ref} onOpen={onOpen}>
                    {ref}
                  </StandardNumber>
                ))}
              </div>
            </section>
          )}

          {result.mandatory_standards.length > 0 && (
            <section className="finding finding--mandatory">
              <h3>
                {t("spec.mandatory")}{" "}
                <span className="finding__count">({result.mandatory_standards.length})</span>
              </h3>
              <div className="finding__chips">
                {result.mandatory_standards.map((ref) => (
                  <StandardNumber key={ref} onOpen={onOpen}>
                    {ref}
                  </StandardNumber>
                ))}
              </div>
            </section>
          )}

          {result.cited_standards.length > 0 && (
            <section className="block">
              <div className="block__head">
                <h3>
                  {t("spec.cited")}{" "}
                  <span className="finding__count">({result.cited_standards.length})</span>
                </h3>
              </div>
              <ul className="finding__list">
                {result.cited_standards.map((entry) => (
                  <li key={entry.cited_as}>
                    {entry.in_corpus ? (
                      <StandardNumber onOpen={onOpen}>{entry.resolved}</StandardNumber>
                    ) : (
                      <span className="is-number is-number--absent">{entry.cited_as}</span>
                    )}
                    <span className="finding__meta">
                      cited as <code>{entry.cited_as}</code>
                      {!entry.in_corpus && ` · ${t("spec.notIndexed")}`}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="block">
            <div className="block__head">
              <h3>
                {t("spec.lineItems")}{" "}
                <span className="finding__count">({result.line_count})</span>
              </h3>
              <DownloadCsvButton
                rows={result.lines.flatMap((line) =>
                  line.matches.map((match) => ({
                    line_no: line.line_no,
                    line: line.text,
                    is_number: match.is_number,
                    title: match.title,
                    confidence: match.confidence,
                    mandatory: match.qco_mandatory ? "yes" : "no",
                  })),
                )}
                filename="manakmitra-spec-analysis.csv"
                t={t}
              />
            </div>

            <ol className="lines">
              {result.lines.map((line) => (
                <li className="lines__item" key={line.line_no}>
                  <div className="lines__text">
                    <span className="lines__no">
                      {line.page ? `p${line.page}` : line.line_no}
                    </span>
                    {line.text}
                  </div>
                  {line.matches.length === 0 ? (
                    <p className="lines__none">No standard matched this line.</p>
                  ) : (
                    <ul className="lines__matches">
                      {line.matches.map((match) => (
                        <li key={match.is_number}>
                          <StandardNumber onOpen={onOpen}>{match.is_number}</StandardNumber>
                          <QcoBadge mandatory={match.qco_mandatory} qcoName={match.qco_name} t={t} />
                          <span className="lines__match-title">{match.title}</span>
                          <span className="lines__score">
                            {Math.round(match.confidence * 100)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </section>
  );
}

function CompletenessGauge({ value, t }) {
  const percent = Math.round(value * 100);
  const level = value >= 0.75 ? "high" : value >= 0.45 ? "medium" : "low";
  return (
    <div className={`gauge gauge--${level}`}>
      <div className="gauge__value">{percent}%</div>
      <div className="gauge__body">
        <div className="gauge__label">{t("spec.completeness")}</div>
        <div className="gauge__track">
          <div
            className={`gauge__fill gauge__fill--${level}`}
            style={{ width: `${Math.max(percent, 2)}%` }}
            role="meter"
            aria-valuenow={percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t("spec.completeness")}
          />
        </div>
      </div>
    </div>
  );
}
