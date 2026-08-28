import { useCallback, useEffect, useRef, useState } from "react";

import { getCertification, getGraph, getStandard } from "../api.js";
import { ErrorNote, QcoBadge, Skeleton, StatusTag, VerificationTag } from "./Shared.jsx";

/**
 * Slide-over detail for one standard.
 *
 * A drawer rather than a route: results stay on screen behind it, so following
 * a reference never costs the user their place. It stacks — opening a neighbour
 * from inside the graph pushes onto a back stack.
 */
export default function StandardDrawer({ isNumber, onOpen, onClose, t }) {
  const [detail, setDetail] = useState(null);
  const [graph, setGraph] = useState(null);
  const [certification, setCertification] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef(null);
  const previouslyFocused = useRef(null);

  const load = useCallback(() => {
    if (!isNumber) return;
    setLoading(true);
    setError(null);
    Promise.all([
      getStandard(isNumber),
      getGraph(isNumber).catch(() => null),
      getCertification(isNumber).catch(() => null),
    ])
      .then(([detailPayload, graphPayload, certPayload]) => {
        setDetail(detailPayload);
        setGraph(graphPayload);
        setCertification(certPayload);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, [isNumber]);

  useEffect(() => {
    setDetail(null);
    setGraph(null);
    setCertification(null);
    load();
  }, [load]);

  // Return focus where it came from on close, and let Escape dismiss.
  useEffect(() => {
    if (!isNumber) return undefined;
    previouslyFocused.current = document.activeElement;
    panelRef.current?.focus();

    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused.current?.focus?.();
    };
  }, [isNumber, onClose]);

  if (!isNumber) return null;

  const standard = detail?.standard;

  return (
    <div className="drawer" role="presentation" onMouseDown={onClose}>
      <aside
        className="drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-label={`${isNumber} details`}
        tabIndex={-1}
        ref={panelRef}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer__head">
          <div>
            <code className="is-number is-number--lg">{isNumber}</code>
            {standard && (
              <>
                <StatusTag status={standard.status} />
                <QcoBadge
                  mandatory={standard.qco_mandatory}
                  qcoName={standard.qco_name}
                  t={t}
                />
                <VerificationTag verification={standard.verification} t={t} />
              </>
            )}
          </div>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={onClose}
            aria-label={t("detail.close")}
          >
            ✕
          </button>
        </header>

        <div className="drawer__body">
          {loading && <Skeleton rows={2} label="Loading standard" />}
          <ErrorNote error={error} onRetry={load} t={t} />

          {standard && !loading && (
            <>
              <h2 className="drawer__title">{standard.title}</h2>

              {standard.scope && (
                <section className="drawer__section">
                  <h3>{t("detail.scope")}</h3>
                  <p className="drawer__scope">{standard.scope}</p>
                </section>
              )}

              <section className="drawer__section">
                <h3>{t("detail.classification")}</h3>
                <dl className="deflist">
                  <dt>{t("detail.department")}</dt>
                  <dd>{detail.department_name || "—"}</dd>
                  <dt>{t("detail.committee")}</dt>
                  <dd>{standard.technical_committee || "—"}</dd>
                  {standard.bis_sector && (
                    <>
                      <dt>{t("detail.subject")}</dt>
                      <dd>
                        {standard.bis_subsector
                          ? `${standard.bis_sector} → ${standard.bis_subsector}`
                          : standard.bis_sector}
                      </dd>
                    </>
                  )}
                  <dt>{t("detail.ics")}</dt>
                  <dd>{standard.ics_codes.join(", ") || "—"}</dd>
                  <dt>{t("detail.year")}</dt>
                  <dd>{standard.year ?? "—"}</dd>
                  {standard.amendment_count > 0 && (
                    <>
                      <dt>{t("detail.amendments")}</dt>
                      <dd>{standard.amendment_count}</dd>
                    </>
                  )}
                </dl>
              </section>

              <VersionTimeline standard={standard} onOpen={onOpen} t={t} />

              {certification && (
                <section className="drawer__section">
                  <h3>{t("detail.certification")}</h3>
                  <div
                    className={`callout ${
                      certification.mandatory ? "callout--warn" : "callout--info"
                    }`}
                  >
                    <strong>
                      {certification.mandatory
                        ? t("detail.mandatory")
                        : t("detail.voluntary")}
                    </strong>
                    <p>{certification.note}</p>
                  </div>
                  {certification.scheme_name && (
                    <>
                      <p className="drawer__scheme">{certification.scheme_name}</p>
                      <p className="drawer__meta">
                        <strong>{t("detail.appliesTo")}:</strong> {certification.applies_to}
                      </p>
                      <h4 className="drawer__subhead">{t("detail.steps")}</h4>
                      <ol className="steps">
                        {certification.steps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ol>
                    </>
                  )}
                </section>
              )}

              {graph?.nodes?.length > 1 && (
                <section className="drawer__section">
                  <h3>{t("detail.graph")}</h3>
                  <ReferenceGraph graph={graph} onOpen={onOpen} />
                  <p className="drawer__note">{t("detail.graphNote")}</p>
                </section>
              )}

              {detail.related.length > 0 && (
                <section className="drawer__section">
                  <h3>{t("detail.related")}</h3>
                  <ul className="reflist">
                    {detail.related.map((item) => (
                      <li key={`${item.relation}-${item.is_number}`}>
                        <span className={`reflist__rel reflist__rel--${item.relation}`}>
                          {RELATION_LABEL[item.relation]}
                        </span>
                        {item.in_corpus ? (
                          <button
                            type="button"
                            className="is-number is-number--link"
                            onClick={() => onOpen(item.is_number)}
                          >
                            {item.is_number}
                          </button>
                        ) : (
                          <span className="is-number is-number--absent" title={t("spec.notIndexed")}>
                            {item.is_number}
                          </span>
                        )}
                        <span className="reflist__title">{item.title}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {detail.cited_by.length > 0 && (
                <section className="drawer__section">
                  <h3>{t("detail.citedBy")}</h3>
                  <div className="reflist__chips">
                    {detail.cited_by.map((ref) => (
                      <button
                        key={ref}
                        type="button"
                        className="is-number is-number--link"
                        onClick={() => onOpen(ref)}
                      >
                        {ref}
                      </button>
                    ))}
                  </div>
                </section>
              )}

              <p className="drawer__footnote">{t("detail.obtain")}</p>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

const RELATION_LABEL = {
  normative_ref: "requires",
  test_method: "tested by",
  supersedes: "replaces",
  superseded_by: "replaced by",
};

/** Supersedes → this → superseded_by, as a single readable line. */
function VersionTimeline({ standard, onOpen, t }) {
  const previous = standard.supersedes ?? [];
  if (!previous.length && !standard.superseded_by) return null;

  return (
    <section className="drawer__section">
      <h3>{t("detail.year")}</h3>
      <ol className="timeline">
        {previous.map((ref) => (
          <li className="timeline__item timeline__item--past" key={ref}>
            <code className="is-number">{ref}</code>
            <span>replaced</span>
          </li>
        ))}
        <li className="timeline__item timeline__item--current">
          <code className="is-number">{standard.is_number}</code>
          <span>
            {standard.superseded_by ? "previous edition" : "current edition"}
            {standard.amendment_count > 0 && ` · ${standard.amendment_count} amendment(s)`}
          </span>
        </li>
        {standard.superseded_by && (
          <li className="timeline__item timeline__item--next">
            <button
              type="button"
              className="is-number is-number--link"
              onClick={() => onOpen(standard.superseded_by)}
            >
              {standard.superseded_by}
            </button>
            <span>current edition</span>
          </li>
        )}
      </ol>
    </section>
  );
}

/**
 * The reference graph as a radial SVG.
 *
 * Hand-rolled rather than pulled from a chart library: the bundle has no UI
 * dependencies beyond React and must render with no network, and a single
 * radial layout does not justify 100 kB. One root, neighbours on a circle.
 * Nodes we do not index are drawn dashed — a coverage gap shown, not hidden.
 */
function ReferenceGraph({ graph, onOpen }) {
  const root = graph.nodes.find((node) => node.level === 0);
  const others = graph.nodes.filter((node) => node.level > 0);
  if (!root || !others.length) return null;

  const width = 460;
  const height = 320;
  const cx = width / 2;
  const cy = height / 2;
  // Labels are wide ("IS 12269:2013"), so past about six neighbours adjacent
  // pills start to touch. Alternating two radii doubles the effective angular
  // spacing without growing the diagram.
  const dense = others.length > 6;
  const radii = dense ? [96, 134] : [112];

  const positions = new Map([[root.is_number, { x: cx, y: cy }]]);
  others.forEach((node, index) => {
    // Start at -90° so the first neighbour sits at the top, not the right.
    const angle = (index / others.length) * Math.PI * 2 - Math.PI / 2;
    const radius = radii[index % radii.length];
    positions.set(node.is_number, {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    });
  });

  // Keep the "IS" prefix — a bare "4031" is ambiguous — but collapse the
  // verbose part notation so the node stays a readable pill.
  const shorten = (isNumber) => isNumber.replace(/\s*\(Part\s*([\w/\s]+?)\s*\)/, " P$1");

  return (
    <svg
      className="graph"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Reference graph for ${root.is_number}: ${others.length} related standards`}
    >
      {graph.edges.map((edge) => {
        const from = positions.get(edge.source);
        const to = positions.get(edge.target);
        if (!from || !to) return null;
        return (
          <line
            key={`${edge.source}-${edge.target}-${edge.relation}`}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            className={`graph__edge graph__edge--${edge.relation}`}
          />
        );
      })}

      {graph.nodes.map((node) => {
        const point = positions.get(node.is_number);
        if (!point) return null;
        const isRoot = node.level === 0;
        const label = shorten(node.is_number);
        return (
          <g
            key={node.is_number}
            className={`graph__node ${isRoot ? "graph__node--root" : ""} ${
              node.in_corpus ? "" : "graph__node--absent"
            }`}
            transform={`translate(${point.x} ${point.y})`}
            onClick={() => node.in_corpus && !isRoot && onOpen(node.is_number)}
            role={node.in_corpus && !isRoot ? "button" : undefined}
            tabIndex={node.in_corpus && !isRoot ? 0 : undefined}
            onKeyDown={(event) => {
              if ((event.key === "Enter" || event.key === " ") && node.in_corpus && !isRoot) {
                event.preventDefault();
                onOpen(node.is_number);
              }
            }}
          >
            <title>{node.title || node.is_number}</title>
            <rect
              x={-Math.max(28, label.length * 3.6)}
              y={-12}
              width={Math.max(56, label.length * 7.2)}
              height={24}
              rx={12}
            />
            <text textAnchor="middle" dy="4">
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
