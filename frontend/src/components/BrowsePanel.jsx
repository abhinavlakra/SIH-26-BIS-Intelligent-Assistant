import { useCallback, useEffect, useState } from "react";

import { browseStandards, getFacets } from "../api.js";
import {
  DownloadCsvButton,
  ErrorNote,
  QcoBadge,
  Skeleton,
  StatusTag,
  VerificationTag,
} from "./Shared.jsx";

const PAGE_SIZE = 20;

const EMPTY_FILTERS = {
  q: "",
  department: "",
  bis_sector: "",
  status: "",
  ics: "",
  qco: false,
};

/**
 * Plain filtered listing of everything indexed.
 *
 * Deliberately *not* semantic: this is the "I know roughly what I want" path,
 * and mixing it with embedding search makes both harder to reason about. Facet
 * counts come from the server so the filters show what is worth clicking.
 */
export default function BrowsePanel({ initialFilters, onOpen, t }) {
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS, ...initialFilters });
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [facets, setFacets] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFacets().then(setFacets).catch(() => setFacets(null));
  }, []);

  // A filter arriving from another panel (e.g. clicking a department on the
  // Overview) replaces the current one and resets paging.
  useEffect(() => {
    if (!initialFilters) return;
    setFilters({ ...EMPTY_FILTERS, ...initialFilters });
    setPage(1);
  }, [initialFilters]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    browseStandards({
      q: filters.q,
      department: filters.department,
      bis_sector: filters.bis_sector,
      status: filters.status,
      ics: filters.ics,
      qco: filters.qco ? "true" : "",
      page,
      page_size: PAGE_SIZE,
    })
      .then(setResult)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [filters, page]);

  // Debounced so typing in the filter box does not fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(load, filters.q ? 220 : 0);
    return () => clearTimeout(timer);
  }, [load, filters.q]);

  const update = (patch) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };

  const dirty = Object.entries(EMPTY_FILTERS).some(
    ([key, value]) => filters[key] !== value,
  );
  const totalPages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1;

  return (
    <section className="panel">
      <div className="panel__intro">
        <h2>{t("browse.title")}</h2>
        <p>{t("browse.lead")}</p>
      </div>

      <div className="filters">
        <label className="filters__field filters__field--grow">
          <span className="sr-only">{t("browse.search")}</span>
          <input
            type="search"
            className="input"
            placeholder={t("browse.search")}
            value={filters.q}
            onChange={(event) => update({ q: event.target.value })}
          />
        </label>

        <label className="filters__field">
          <span className="filters__label">{t("browse.department")}</span>
          <select
            className="input input--select"
            value={filters.department}
            onChange={(event) => update({ department: event.target.value })}
          >
            <option value="">{t("browse.all")}</option>
            {(facets?.departments ?? []).map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.value} ({entry.count})
              </option>
            ))}
          </select>
        </label>

        {/* BIS subject sector — what a user actually browses by on the portal.
            Orthogonal to the department above, which is who owns the standard. */}
        <label className="filters__field">
          <span className="filters__label">{t("browse.subject")}</span>
          <select
            className="input input--select"
            value={filters.bis_sector}
            onChange={(event) => update({ bis_sector: event.target.value })}
          >
            <option value="">{t("browse.all")}</option>
            {(facets?.bis_sectors ?? []).map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.value} ({entry.count})
              </option>
            ))}
          </select>
        </label>

        <label className="filters__field">
          <span className="filters__label">{t("browse.status")}</span>
          <select
            className="input input--select"
            value={filters.status}
            onChange={(event) => update({ status: event.target.value })}
          >
            <option value="">{t("browse.all")}</option>
            {(facets?.statuses ?? []).map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.value} ({entry.count})
              </option>
            ))}
          </select>
        </label>

        <label className="filters__check">
          <input
            type="checkbox"
            checked={filters.qco}
            onChange={(event) => update({ qco: event.target.checked })}
          />
          {t("browse.mandatoryOnly")}
          {facets && <span className="filters__count">{facets.qco_mandatory}</span>}
        </label>

        {dirty && (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              setFilters(EMPTY_FILTERS);
              setPage(1);
            }}
          >
            {t("browse.clear")}
          </button>
        )}
      </div>

      <ErrorNote error={error} onRetry={load} t={t} />

      {loading && !result && <Skeleton rows={4} label="Loading standards" />}

      {result && (
        <>
          <div className="result__head">
            <p className="result__count" aria-live="polite">
              <strong>{result.total}</strong> {t("browse.results")}
            </p>
            <DownloadCsvButton
              rows={result.items.map((item) => ({
                is_number: item.is_number,
                title: item.title,
                department: item.department_code,
                committee: item.technical_committee,
                status: item.status,
                year: item.year ?? "",
                ics: item.ics_codes.join(" "),
                mandatory: item.qco_mandatory ? "yes" : "no",
              }))}
              filename="manakmitra-standards.csv"
              t={t}
            />
          </div>

          {result.items.length === 0 ? (
            <p className="empty-note">{t("browse.none")}</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">IS number</th>
                  <th scope="col">Title</th>
                  <th scope="col">Dept</th>
                  <th scope="col">Year</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.is_number}>
                    <td>
                      <button
                        type="button"
                        className="is-number is-number--link"
                        onClick={() => onOpen(item.is_number)}
                      >
                        {item.is_number}
                      </button>
                    </td>
                    <td>
                      <span className="table__title">{item.title}</span>
                      <span className="table__tags">
                        <StatusTag status={item.status} />
                        <QcoBadge
                          mandatory={item.qco_mandatory}
                          t={t}
                        />
                        <VerificationTag verification={item.verification} t={t} />
                      </span>
                    </td>
                    <td>
                      <span className="table__dept" title={item.sector}>
                        {item.department_code}
                      </span>
                    </td>
                    <td className="table__num">{item.year ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {totalPages > 1 && (
            <nav className="pager" aria-label="Pagination">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
              >
                ← {t("browse.prev")}
              </button>
              <span className="pager__state">
                {t("browse.page")} {page} {t("common.of")} {totalPages}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={page >= totalPages}
                onClick={() => setPage((current) => current + 1)}
              >
                {t("browse.next")} →
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
