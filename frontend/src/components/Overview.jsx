import { useCallback, useEffect, useState } from "react";

import { getAnalytics, getCoverage, getFacets } from "../api.js";
import { ErrorNote, Skeleton } from "./Shared.jsx";

/**
 * The landing surface: what is indexed, and how much of the real BIS catalogue
 * that represents.
 *
 * Opening on honest coverage is deliberate. The obvious question about any
 * catalogue prototype is "how much of it do you actually have?", and answering
 * it before it is asked is worth more than a flattering number.
 */
export default function Overview({ onOpen, onNavigate, t }) {
  const [coverage, setCoverage] = useState(null);
  const [facets, setFacets] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([getCoverage(), getFacets(), getAnalytics().catch(() => null)])
      .then(([coveragePayload, facetsPayload, analyticsPayload]) => {
        setCoverage(coveragePayload);
        setFacets(facetsPayload);
        setAnalytics(analyticsPayload);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  if (loading) {
    return (
      <section className="panel">
        <Skeleton rows={3} label="Loading catalogue overview" />
      </section>
    );
  }

  // Records carrying at least one ICS code. `ics_groups` counts (record, code)
  // pairs, so this is an upper bound — close enough to caption the panel with.
  const classified = (facets?.ics_groups ?? []).reduce((sum, g) => sum + g.count, 0);

  return (
    <section className="panel">
      <div className="panel__intro">
        <h2>{t("overview.title")}</h2>
        <p>{t("overview.lead")}</p>
      </div>

      <ErrorNote error={error} onRetry={load} t={t} />

      {coverage && (
        <>
          <div className="kpis">
            <Kpi
              value={coverage.total_indexed.toLocaleString()}
              label={t("overview.kpi.indexed")}
              note={`BIS published ${coverage.total_published.toLocaleString()} as of ${coverage.as_of}`}
            />
            <Kpi
              value={`${coverage.departments_covered}/${coverage.departments_total}`}
              label={t("overview.kpi.departments")}
              note={`${coverage.sectional_committees}+ sectional committees`}
            />
            <Kpi
              value={facets?.qco_mandatory ?? 0}
              label={t("overview.kpi.mandatory")}
              note="Certification compulsory"
              tone="warn"
            />
            <Kpi
              value={facets?.ics_groups?.length ?? 0}
              label={t("overview.ics")}
              note="ICS subject groups"
            />
          </div>

          <section className="block">
            <div className="block__head">
              <h3>{t("overview.coverage")}</h3>
              <p className="block__note">{t("overview.coverageNote")}</p>
            </div>
            <CoverageChart departments={coverage.departments} onNavigate={onNavigate} t={t} />
          </section>
        </>
      )}

      {facets?.ics_groups?.length > 0 && (
        <section className="block">
          <div className="block__head">
            <h3>{t("overview.ics")}</h3>
            {/* The BIS portal API publishes no ICS codes, so this only covers
                the hand-curated records. Saying how many keeps the panel from
                reading as though it described the whole catalogue. */}
            <p className="block__note">
              {t("overview.icsNote")
                .replace("{n}", classified.toLocaleString())
                .replace("{total}", (facets.total ?? 0).toLocaleString())}
            </p>
          </div>
          <IcsTreemap groups={facets.ics_groups} onNavigate={onNavigate} />
        </section>
      )}

      <section className="block">
        <div className="block__head">
          <h3>{t("overview.analytics")}</h3>
        </div>
        <QueryAnalytics analytics={analytics} onOpen={onOpen} t={t} />
      </section>
    </section>
  );
}

function Kpi({ value, label, note, tone }) {
  return (
    <div className={`kpi ${tone ? `kpi--${tone}` : ""}`}>
      <div className="kpi__value">{value}</div>
      <div className="kpi__label">{label}</div>
      {note && <div className="kpi__note">{note}</div>}
    </div>
  );
}

/**
 * Indexed count against the real BIS published count, per department.
 *
 * Two bars per row: a faint one scaled to the department's share of the whole
 * catalogue, and a solid one for what we hold. The solid bar being tiny is the
 * honest picture and is exactly what should be shown.
 */
function CoverageChart({ departments, onNavigate, t }) {
  const maxPublished = Math.max(
    ...departments.map((d) => Math.max(d.published, d.indexed)),
  );

  return (
    <ul className="coverage">
      {departments.map((department) => {
        const publishedWidth = (department.published / maxPublished) * 100;
        // Both bars share one axis, so the comparison stays honest whichever
        // way round they are. Since the full catalogue was collected the
        // indexed count now *exceeds* the published figure for most
        // departments — the BIS total is a June 2025 snapshot and the portal
        // is current — so the bar has to be able to run past it.
        const indexedWidth = (department.indexed / maxPublished) * 100;
        const empty = department.indexed === 0;
        const complete = department.indexed >= department.published;

        return (
          <li className={`coverage__row ${empty ? "coverage__row--empty" : ""}`} key={department.code}>
            <button
              type="button"
              className="coverage__label"
              onClick={() => !empty && onNavigate("browse", { department: department.code })}
              disabled={empty}
              title={
                empty
                  ? `${department.name} — no standards indexed yet`
                  : `Browse ${department.indexed} indexed ${department.name} standards`
              }
            >
              <span className="coverage__code">{department.code}</span>
              <span className="coverage__name">{department.name}</span>
            </button>
            <div className="coverage__bars">
              <div
                className="coverage__published"
                style={{ width: `${publishedWidth}%` }}
                aria-hidden="true"
              />
              <div
                className="coverage__indexed"
                style={{ width: `${Math.max(indexedWidth, department.indexed ? 0.6 : 0)}%` }}
                aria-hidden="true"
              />
            </div>
            <span className="coverage__count">
              <strong>{department.indexed.toLocaleString()}</strong>
              <span className="coverage__total">
                {complete ? "✓" : `/ ${department.published.toLocaleString()}`}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

// The top-level ICS field names. Enough to make the codes legible without
// shipping the full classification.
const ICS_NAMES = {
  "01": "Generalities & terminology",
  "03": "Services & company organization",
  11: "Health care technology",
  13: "Environment & safety",
  17: "Metrology & measurement",
  21: "Mechanical systems & components",
  23: "Fluid systems & components",
  29: "Electrical engineering",
  35: "Information technology",
  43: "Road vehicles engineering",
  53: "Materials handling equipment",
  59: "Textile & leather technology",
  67: "Food technology",
  71: "Chemical technology",
  75: "Petroleum & related technologies",
  77: "Metallurgy",
  83: "Rubber & plastics industries",
  87: "Paint & colour industries",
  91: "Construction materials & building",
  93: "Civil engineering",
  97: "Domestic & commercial equipment",
};

/**
 * Squarified-ish treemap. Rows are packed greedily by area, which is plenty
 * for twenty-odd blocks and avoids a layout dependency.
 */
function IcsTreemap({ groups, onNavigate }) {
  const total = groups.reduce((sum, group) => sum + group.count, 0);
  if (!total) return null;

  // Pack into rows of roughly equal area so no block becomes a sliver.
  const rows = [];
  let current = [];
  let currentShare = 0;
  const targetShare = 1 / Math.max(2, Math.round(Math.sqrt(groups.length)));

  groups.forEach((group) => {
    current.push(group);
    currentShare += group.count / total;
    if (currentShare >= targetShare) {
      rows.push({ items: current, share: currentShare });
      current = [];
      currentShare = 0;
    }
  });
  if (current.length) rows.push({ items: current, share: currentShare });

  return (
    <div className="treemap">
      {rows.map((row, rowIndex) => (
        <div
          className="treemap__row"
          key={rowIndex}
          style={{ flexGrow: Math.max(row.share, 0.06) }}
        >
          {row.items.map((group) => {
            const share = group.count / total;
            const name = ICS_NAMES[group.value] ?? `ICS ${group.value}`;
            return (
              <button
                type="button"
                className="treemap__cell"
                key={group.value}
                style={{ flexGrow: Math.max(group.count, 0.5) }}
                onClick={() => onNavigate("browse", { ics: group.value })}
                title={`ICS ${group.value} — ${name} (${group.count} standards, ${Math.round(share * 100)}%)`}
              >
                <span className="treemap__code">{group.value}</span>
                <span className="treemap__name">{name}</span>
                <span className="treemap__count">{group.count}</span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/**
 * Query telemetry — including the queries that found nothing.
 *
 * The unanswered list is the one panel in this app built for BIS rather than
 * for the end user: it is a standards-development gap signal drawn from real
 * demand rather than from a survey.
 */
function QueryAnalytics({ analytics, onOpen, t }) {
  if (!analytics || analytics.total_queries === 0) {
    return <p className="empty-note">{t("overview.noQueries")}</p>;
  }

  return (
    <div className="analytics">
      <div className="analytics__stats">
        <span>
          <strong>{analytics.total_queries}</strong> queries
        </span>
        <span>
          <strong>{Math.round(analytics.grounded_rate * 100)}%</strong> answered
        </span>
        <span>
          <strong>{analytics.median_latency_ms} ms</strong> median
        </span>
      </div>

      <div className="analytics__cols">
        <div>
          <h4 className="analytics__head">{t("overview.analytics")}</h4>
          <ul className="ranklist">
            {analytics.top_queries.map((entry) => (
              <li key={entry.value}>
                <span className="ranklist__text">{entry.value}</span>
                <span className="ranklist__count">{entry.count}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="analytics__head analytics__head--gap">
            {t("overview.unanswered")}
          </h4>
          {analytics.unanswered.length === 0 ? (
            <p className="empty-note">—</p>
          ) : (
            <ul className="ranklist ranklist--gap">
              {analytics.unanswered.map((entry) => (
                <li key={entry.value}>
                  <span className="ranklist__text">{entry.value}</span>
                  <span className="ranklist__count">{entry.count}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="block__note">{t("overview.unansweredNote")}</p>
        </div>
      </div>
    </div>
  );
}
