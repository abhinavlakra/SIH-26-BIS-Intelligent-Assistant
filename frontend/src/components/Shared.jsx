/** Small presentational pieces shared across the panels. */

import { useEffect, useState } from "react";

export function Spinner({ label = "Working…" }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="spinner__dot" />
      <span className="spinner__dot" />
      <span className="spinner__dot" />
      <span className="spinner__label">{label}</span>
    </div>
  );
}

/**
 * Placeholder rows shaped like the results that are coming.
 *
 * The LLM path has been measured at 7-35s through a router, and a bare spinner
 * for that long reads as "broken" rather than "working". A skeleton at least
 * tells the user what shape the answer will take.
 */
export function Skeleton({ rows = 3, label }) {
  return (
    <div className="skeleton" role="status" aria-live="polite">
      {label && <span className="sr-only">{label}</span>}
      {Array.from({ length: rows }, (_, index) => (
        <div className="skeleton__card" key={index} aria-hidden="true">
          <div className="skeleton__line skeleton__line--sm" />
          <div className="skeleton__line" />
          <div className="skeleton__line skeleton__line--md" />
        </div>
      ))}
    </div>
  );
}

export function ErrorNote({ error, onRetry, t }) {
  if (!error) return null;
  const label = t ? t("common.error") : "Something went wrong";
  return (
    <div className="note note--error" role="alert">
      <strong>{error.reachable === false ? "Backend offline" : label}</strong>
      <p>{error.message}</p>
      {onRetry && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>
          {t ? t("common.tryAgain") : "Try again"}
        </button>
      )}
    </div>
  );
}

export function ExampleChips({ examples, onPick, disabled, label = "Try:" }) {
  return (
    <div className="examples">
      <span className="examples__label">{label}</span>
      {examples.map((example) => (
        <button
          key={example.label}
          type="button"
          className="chip"
          disabled={disabled}
          onClick={() => onPick(example.value)}
          title={example.value}
        >
          {example.label}
        </button>
      ))}
    </div>
  );
}

/** Confidence/relevance bands. A bare "0.62" tells a user nothing. */
export function band(value) {
  if (value >= 0.6) return "high";
  if (value >= 0.35) return "medium";
  return "low";
}

const BAND_KEY = { high: "common.high", medium: "common.medium", low: "common.review" };

const BAND_EXPLAINER = {
  high: "Strong match — the standard's scope clearly covers this.",
  medium: "Plausible match — read the scope before relying on it.",
  low: "Weak match — shown for completeness; verify it applies at all.",
};

/**
 * Relevance/confidence in 0-1 as a labelled meter.
 *
 * `role="meter"` plus the aria-value* attributes so a screen reader announces
 * the number rather than reading an unlabelled div, and a band word so a
 * sighted user does not have to interpret a raw score.
 */
export function Meter({ value, caption, t }) {
  const level = band(value);
  const percent = Math.round(value * 100);
  const word = t ? t(BAND_KEY[level]) : level;
  return (
    <div
      className="meter"
      role="meter"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`${caption}: ${percent}% — ${word}`}
      title={`${caption}: ${percent}%\n${BAND_EXPLAINER[level]}`}
    >
      <div className="meter__track">
        <div
          className={`meter__fill meter__fill--${level}`}
          style={{ width: `${Math.max(percent, 3)}%` }}
        />
      </div>
      <span className={`meter__value meter__value--${level}`}>
        {percent}%<span className="meter__band"> {word}</span>
      </span>
    </div>
  );
}

/** Legend explaining the bands, so the meter is self-documenting. */
export function ConfidenceLegend({ t }) {
  return (
    <p className="legend">
      {["high", "medium", "low"].map((level) => (
        <span className="legend__item" key={level}>
          <span className={`legend__swatch legend__swatch--${level}`} aria-hidden="true" />
          {t(BAND_KEY[level])}
          <span className="legend__range">
            {level === "high" ? "60–100%" : level === "medium" ? "35–59%" : "<35%"}
          </span>
        </span>
      ))}
    </p>
  );
}

/**
 * An IS number. Clickable when `onOpen` is given — every IS number anywhere in
 * the app should lead to its detail drawer, which is what turns a result list
 * from a dead end into something you can explore.
 */
export function StandardNumber({ children, onOpen }) {
  if (!onOpen) return <code className="is-number">{children}</code>;
  return (
    <button
      type="button"
      className="is-number is-number--link"
      onClick={() => onOpen(children)}
      title={`Open ${children}`}
    >
      {children}
    </button>
  );
}

export function StatusTag({ status }) {
  if (!status || status === "active") return null;
  return <span className={`tag tag--${status}`}>{status}</span>;
}

/**
 * The compliance signal. This is the difference between "this standard is
 * relevant to you" and "you may not legally sell without it", so it is styled
 * to be the loudest thing on the card.
 */
export function QcoBadge({ mandatory, qcoName, t }) {
  if (!mandatory) return null;
  return (
    <span
      className="tag tag--mandatory"
      title={qcoName ? `Mandatory under: ${qcoName}` : "Mandatory under a Quality Control Order"}
    >
      {t ? t("common.mandatory") : "Mandatory"}
    </span>
  );
}

export function VerificationTag({ verification, t }) {
  const verified = verification === "verified";
  return (
    <span
      className={`tag tag--${verified ? "verified" : "unverified"}`}
      title={t(verified ? "detail.verified" : "detail.unverified")}
    >
      {verified ? "✓" : "?"}
    </span>
  );
}

/** Copy-to-clipboard with feedback, degrading quietly where it is unavailable. */
export function CopyButton({ text, t }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), 1600);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      /* clipboard blocked (no HTTPS, or denied) — leave the label unchanged */
    }
  };

  return (
    <button type="button" className="btn btn--ghost btn--sm" onClick={copy}>
      {copied ? t("common.copied") : t("common.copy")}
    </button>
  );
}

/** Builds a CSV and triggers a download entirely client-side. */
export function DownloadCsvButton({ rows, filename, t }) {
  if (!rows?.length) return null;

  const download = () => {
    const headers = Object.keys(rows[0]);
    const escape = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const csv = [
      headers.join(","),
      ...rows.map((row) => headers.map((header) => escape(row[header])).join(",")),
    ].join("\n");

    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button type="button" className="btn btn--ghost btn--sm" onClick={download}>
      {t("common.export")}
    </button>
  );
}
