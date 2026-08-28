import { LANGUAGES } from "../i18n.js";

export default function Header({ lang, onLang, t }) {
  return (
    <header className="header">
      <div className="header__inner">
        <div className="brand">
          <div className="brand__mark" aria-hidden="true">
            मा
          </div>
          <div className="brand__text">
            <h1 className="brand__name">
              Manak<span>Mitra</span>
            </h1>
            <p className="brand__tagline">{t("app.tagline")}</p>
          </div>
        </div>

        <div className="header__meta">
          <div className="langswitch" role="group" aria-label={t("common.language")}>
            {LANGUAGES.map((entry) => (
              <button
                key={entry.code}
                type="button"
                className={`langswitch__btn ${
                  lang === entry.code ? "langswitch__btn--active" : ""
                }`}
                onClick={() => onLang(entry.code)}
                aria-pressed={lang === entry.code}
                lang={entry.code}
                title={entry.label}
              >
                {entry.short}
              </button>
            ))}
          </div>
          <span className="badge badge--ps">SIH26107</span>
          <span className="header__ministry">{t("app.ministry")}</span>
        </div>
      </div>
    </header>
  );
}
