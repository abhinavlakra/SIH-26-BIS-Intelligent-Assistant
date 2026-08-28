import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getStats } from "./api.js";
import { translator } from "./i18n.js";
import AskPanel from "./components/AskPanel.jsx";
import BrowsePanel from "./components/BrowsePanel.jsx";
import Header from "./components/Header.jsx";
import Overview from "./components/Overview.jsx";
import RecommendPanel from "./components/RecommendPanel.jsx";
import SpecPanel from "./components/SpecPanel.jsx";
import StandardDrawer from "./components/StandardDrawer.jsx";
import StatusBar from "./components/StatusBar.jsx";

const VIEWS = [
  { id: "overview", labelKey: "nav.overview", hintKey: "nav.hint.overview", icon: "▦" },
  { id: "recommend", labelKey: "nav.recommend", hintKey: "nav.hint.recommend", icon: "◎" },
  { id: "ask", labelKey: "nav.ask", hintKey: "nav.hint.ask", icon: "?" },
  { id: "spec", labelKey: "nav.spec", hintKey: "nav.hint.spec", icon: "☰" },
  { id: "browse", labelKey: "nav.browse", hintKey: "nav.hint.browse", icon: "⌸" },
];

const LANG_KEY = "manakmitra.lang";
const RECENT_KEY = "manakmitra.recent";
const RECENT_LIMIT = 6;

function loadRecent() {
  try {
    const stored = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(stored) ? stored.slice(0, RECENT_LIMIT) : [];
  } catch {
    return [];
  }
}

export default function App() {
  // Recommendation is the differentiator, but the overview answers "what is in
  // here?" — the question every visitor has first — so it leads.
  const [view, setView] = useState("overview");
  const [browseFilters, setBrowseFilters] = useState(null);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState(null);
  // Which engine actually answered most recently (may be a fallback).
  const [effectiveModel, setEffectiveModel] = useState(null);
  const [lang, setLang] = useState(() => localStorage.getItem(LANG_KEY) ?? "en");
  const [recent, setRecent] = useState(loadRecent);

  // A stack, so following a reference out of the drawer can be walked back.
  const [drawerStack, setDrawerStack] = useState([]);
  const navRef = useRef(null);

  const t = useMemo(() => translator(lang), [lang]);

  const refreshStats = useCallback(() => {
    getStats()
      .then((payload) => {
        setStats(payload);
        setStatsError(null);
      })
      .catch((error) => {
        setStats(null);
        setStatsError(error);
      });
  }, []);

  useEffect(refreshStats, [refreshStats]);

  useEffect(() => {
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const openStandard = useCallback((isNumber) => {
    if (!isNumber) return;
    setDrawerStack((stack) =>
      stack[stack.length - 1] === isNumber ? stack : [...stack, isNumber],
    );
    setRecent((current) => {
      const next = [isNumber, ...current.filter((item) => item !== isNumber)].slice(
        0,
        RECENT_LIMIT,
      );
      localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const closeDrawer = useCallback(() => setDrawerStack([]), []);

  const navigate = useCallback((target, filters = null) => {
    setView(target);
    if (target === "browse") setBrowseFilters(filters);
    closeDrawer();
  }, [closeDrawer]);

  // Roving arrow-key navigation across the rail, as a tablist should behave.
  const onNavKeyDown = (event) => {
    const index = VIEWS.findIndex((entry) => entry.id === view);
    if (index === -1) return;
    let next = null;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") next = index + 1;
    if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = index - 1;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = VIEWS.length - 1;
    if (next === null) return;

    event.preventDefault();
    const target = VIEWS[(next + VIEWS.length) % VIEWS.length];
    setView(target.id);
    navRef.current?.querySelector(`#nav-${target.id}`)?.focus();
  };

  const panelProps = { onModel: setEffectiveModel, onOpen: openStandard, lang, t };

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <Header lang={lang} onLang={setLang} t={t} />
      <StatusBar
        stats={stats}
        error={statsError}
        onRetry={refreshStats}
        effectiveModel={effectiveModel}
        t={t}
      />

      <div className="shell">
        <nav
          className="rail"
          aria-label="Sections"
          ref={navRef}
          onKeyDown={onNavKeyDown}
          role="tablist"
          aria-orientation="vertical"
        >
          {VIEWS.map((entry) => (
            <button
              key={entry.id}
              id={`nav-${entry.id}`}
              type="button"
              role="tab"
              className={`rail__item ${view === entry.id ? "rail__item--active" : ""}`}
              onClick={() => navigate(entry.id)}
              aria-selected={view === entry.id}
              tabIndex={view === entry.id ? 0 : -1}
              // Without this the accessible name is the label *and* the hint
              // concatenated, which is a mouthful to hear read out.
              aria-label={t(entry.labelKey)}
            >
              <span className="rail__icon" aria-hidden="true">
                {entry.icon}
              </span>
              <span className="rail__text">
                <span className="rail__label">{t(entry.labelKey)}</span>
                <span className="rail__hint">{t(entry.hintKey)}</span>
              </span>
            </button>
          ))}

          {recent.length > 0 && (
            <div className="rail__recent">
              <div className="rail__recent-head">
                <span>{t("nav.recent")}</span>
                <button
                  type="button"
                  className="rail__clear"
                  onClick={() => {
                    setRecent([]);
                    localStorage.removeItem(RECENT_KEY);
                  }}
                >
                  {t("nav.clearRecent")}
                </button>
              </div>
              {recent.map((isNumber) => (
                <button
                  key={isNumber}
                  type="button"
                  className="rail__recent-item"
                  onClick={() => openStandard(isNumber)}
                  title={isNumber}
                >
                  {isNumber}
                </button>
              ))}
            </div>
          )}
        </nav>

        <main className="main" id="main" role="tabpanel">
          {view === "overview" && (
            <Overview onOpen={openStandard} onNavigate={navigate} t={t} />
          )}
          {view === "recommend" && <RecommendPanel {...panelProps} />}
          {view === "ask" && <AskPanel {...panelProps} />}
          {view === "spec" && <SpecPanel {...panelProps} />}
          {view === "browse" && (
            <BrowsePanel initialFilters={browseFilters} onOpen={openStandard} t={t} />
          )}
        </main>
      </div>

      <StandardDrawer
        isNumber={drawerStack[drawerStack.length - 1] ?? null}
        onOpen={openStandard}
        onClose={closeDrawer}
        t={t}
      />

      <footer className="footer">
        <p>
          <strong>ManakMitra</strong> · Smart India Hackathon 2026 · SIH26107
        </p>
        <p className="footer__note">{t("footer.note")}</p>
      </footer>
    </div>
  );
}
