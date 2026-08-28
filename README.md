# ManakMitra — AI Assistant & Recommendation Engine for Indian Standards

**SIH 2026 · Problem Statement SIH26107**
*AI-powered Intelligent Assistant for Indian Standards and BIS Services*
Ministry of Consumer Affairs, Food & Public Distribution → Bureau of Indian Standards (BIS)
Theme: Smart Automation · Software

> *Manak* (मानक) = standard. ManakMitra = "a friend for standards."

---

## The problem

BIS publishes thousands of Indian Standards. An MSME owner, a manufacturer, or a
government procurement officer typically has two questions — and today both are
answered by manually digging through a catalogue portal:

1. **"What does the standard on X say?"** — hard to search in plain language.
2. **"Which IS codes apply to *my* product?"** — no tool does this at all.

ManakMitra answers both:

| Endpoint | What it does |
|---|---|
| `POST /api/chat` | Natural-language Q&A, answered **only** from the indexed catalogue, with IS-number citations |
| `POST /api/recommend` | Describe a product in plain words → ranked applicable IS codes, each with a rationale, confidence and **certification obligation** |
| `POST /api/analyze-spec` | Paste a tender → outdated citations, missing normative references, per-line-item matches |
| `POST /api/analyze-spec/upload` | Upload a tender **PDF** → the same analysis, with page-level provenance |
| `GET /api/coverage` | Indexed counts against the **real** BIS published totals, per department |
| `GET /api/graph/{is}` | The reference neighbourhood of a standard |
| `GET /api/certification/{is}` | Which BIS scheme applies, and whether a QCO makes it mandatory |
| `GET /api/services` | BIS service guidance — hallmarking, testing labs, consumer protection — each answer carrying its source on bis.gov.in |

The recommendation engine is the differentiator: it turns a passive lookup portal
into an **actionable compliance assistant**.

---

## Architecture

```
                    ┌──────────────────────────────────────────┐
   BIS standards    │  Ingestion                               │
   portal JSON API  │  collector.py → enrich.py → JSONL        │
   (24,324 records) │            (data/processed)              │
                    └──────────────────┬───────────────────────┘
                                       │  build_index.py
                                       ▼
                         ┌──────────────────────────┐
                         │  sentence-transformers   │  local, offline, free
                         │  all-MiniLM-L6-v2        │
                         └────────────┬─────────────┘
                                      ▼
                         ┌──────────────────────────┐
                         │  ChromaDB (persistent)   │  data/chroma
                         │  cosine similarity       │
                         └────────────┬─────────────┘
                                      │ retriever.py (top-k + relevance floor)
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
              ┌──────────────────┐        ┌──────────────────┐
              │ services/chat.py │        │ services/        │
              │ grounded Q&A     │        │ recommend.py     │
              └────────┬─────────┘        └────────┬─────────┘
                       └────────────┬──────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │  rag/llm.py adapter  │ ─► Claude (Messages API)
                         │  NullProvider ◄──────┼──  no key / API down
                         └──────────┬───────────┘
                                    ▼
                            FastAPI  →  /docs
```

**Design decisions that matter for judging:**

- **Embeddings run locally.** No embedding API, no per-query cost, works with the
  Wi-Fi off. Retrieval end-to-end measures **~20-40 ms**. Only *generation*
  touches a hosted model.
- **Graceful degradation, and it's fast.** If `ANTHROPIC_API_KEY` is missing *or
  the API call fails*, chat returns an extractive answer and recommend still
  ranks with keyword-overlap rationales. A **circuit breaker** (`rag/llm.py`)
  means only the first affected request pays the timeout — measured 41.5s →
  0.04s → 0.04s on repeat calls with the API unreachable. **The demo cannot
  hard-fail, or visibly stall, on an API outage.**
- **Grounded, not generative.** The system prompt forbids outside knowledge and
  invented IS numbers, and a calibrated relevance floor makes the service say
  "not in the catalogue" rather than answer with irrelevant citations.
- **The whole catalogue, indexed locally.** 24,324 published standards across
  all 17 BIS technical departments, collected from the official portal's own
  JSON API and embedded on this machine. Retrieval never leaves the box.
- **Two relevance floors, on purpose.** Chat uses a strict floor (0.58) so it
  refuses; recommend uses a lower one (0.42) because its input is a product
  description, not a question, and a weak candidate flagged *"Review needed"*
  beats stonewalling a real product. Both were **re-derived** at this scale —
  `python -m app.ingestion.calibrate` prints the distributions and fails loudly
  if a floor drifts out of its window. They have moved twice already.
- **Retrieval is hybrid, and entirely local.** Cosine similarity is modulated by
  lexical query-coverage and ICS-hierarchy affinity. That fixes the case pure
  embeddings get wrong — *"stainless steel water bottle"* now ranks IS 5522
  (steel for utensils) above IS 14543 (packaged drinking *water*), with no LLM
  involved.
- **The reference graph does what embeddings cannot.** Standards cite each
  other, so retrieval walks one hop out: an *"earthquake resistant apartment
  block"* query reaches IS 1893 semantically, then pulls in the cement,
  aggregate and reinforcement standards IS 456 normatively requires.
- **Compliance, not just relevance.** Every recommendation says whether a
  Quality Control Order makes certification *mandatory*, and names the order.
  Knowing IS 4151 applies to your helmet matters far less than knowing the ISI
  mark is compulsory before you can sell it.
- **Metadata only.** We index IS number, title, scope summary, sector, and
  committee. Full standard texts are copyrighted and deliberately excluded — the
  assistant points users to the IS number to consult or purchase via BIS.

---

## Quick start

**Demo mode — one process, one port. Use this for judging.**

```powershell
.\scripts\setup.ps1      # once: installs deps, creates .env, builds the index
.\scripts\run_demo.ps1   # builds the UI and serves everything on :8000
```

Open **http://localhost:8000** — the web app. Swagger stays available at
**/docs** for showing the API directly.

**Development mode — hot reload, two processes.**

```powershell
.\scripts\run_dev_full.ps1   # backend :8000 + Vite dev server :5173
```

Open **http://localhost:5173**. Vite proxies `/api` to the backend, so the
frontend uses the same relative URLs in development and production.

<details>
<summary>Manual equivalents</summary>

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m app.ingestion.build_index --rebuild
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev          # dev server on :5173
npm run build        # or: emit dist/ for the backend to serve
npm run capture      # drive the running site in Chrome, save screenshots
```

</details>

### Optional: enable LLM answers

Copy `backend/.env.example` to `backend/.env` and set:

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5     # or claude-sonnet-5 / claude-opus-5
```

Without a key the API still works — `GET /api/stats` reports
`"llm_enabled": false` so you always know which mode you're in.

> **Gotcha:** OS environment variables take precedence over `backend/.env`. If
> your shell already exports `ANTHROPIC_MODEL` or `ANTHROPIC_API_KEY` (some IDEs
> and AI CLIs do), `/api/stats` will report *that* model rather than the one in
> your `.env`. Check `/api/stats` before demoing — it always shows what is
> actually in use.

---

## Demo script (for the jury)

Open **http://localhost:8000**.

1. **Overview** (the landing surface, ~15 s) — "24,324 standards, all 17 BIS
   technical departments — the entire published catalogue, collected from the
   official portal and indexed on this laptop." Point at the coverage chart:
   bars are drawn against the *official* BIS published count per department, so
   the scale is checkable rather than asserted.
2. **"Find my standards"** → **Two-wheeler helmets** → **Find standards**.
   One plain sentence becomes a compliance decision: **IS 4151:2015** under
   *"Certification required"*, naming the Helmet (Quality Control) Order, 2020 —
   with IS 2925 (industrial helmets) correctly demoted to *"Also applicable"*.
   Then click the IS number → the detail drawer opens with the certification
   pathway. *This is the strongest moment — lead with it.*
3. **"Check a tender"** → **Sample building tender** → **Analyse**. It flags
   **IS 1893:2002 → superseded by IS 1893 (Part 1):2016**, a bare **IS 13920**
   citation with no year, seven missing normative references, and four line
   items needing mandatory certification. *"This is the procurement dispute the
   problem statement describes, caught before the tender goes out."*
4. **Open IS 456:2000** from anywhere → the **reference graph**: ten standards,
   typed edges for *requires* and *tested by*. *"A vector index cannot do this."*
5. **"Ask a question"** → switch to **हिं** → the helmet question in Hindi.
   Answered with citations, and the retrieval works with the network off.
6. **Still on "Ask"** → **Off-topic (declines)** → *"Not covered by the indexed
   catalogue"* with **zero citations** instead of an invented IS number.
   **Show this** — most RAG demos fail exactly here.
7. **Back to Overview** → the *"Queries the catalogue could not answer"* tile.
   *"That is a standards-development gap list for BIS, from real demand."*
8. **Pull the Wi-Fi** → answers keep coming, sub-100 ms, and the status pill
   flips to "Extractive mode" rather than pretending.
9. *(Optional)* **/docs** — the same features as a documented REST API, which is
   how BIS would actually integrate it.

Screenshots for your slide deck: run `npm run capture` in `frontend/` while the
app is running; PNGs land in `frontend/shots/`.

## Sample tenders

Seven fixtures in `samples/tenders/`, each built to make one thing happen.
Regenerate with `python scripts/make_sample_tenders.py`.

| File | Completeness | What it demonstrates |
|---|---|---|
| `01-building-rcc.pdf` | 50% | Outdated citations (`IS 1893:2002`, `IS 13920` with no year) plus 5 missing normative references |
| `02-electrical-substation.pdf` | 75% | Four standards under a QCO — ISI and CRS side by side |
| `03-water-supply.pdf` | 67% | Mandatory packaged-drinking-water certification |
| `04-well-specified.pdf` | 83% | A *good* tender — current editions, normative chain spelled out |
| `05-no-citations.pdf` | **0%** | Cites no standard at all, yet still surfaces 3 mandatory ones |
| `06-messy-boq.pdf` | 57% | The reflow stress test — contents page, running headers, a schedule-of-rates table and three numbering conventions. 3 pages become 8 clean line items; the entire BOQ is discarded |
| `07-scanned.pdf` | — | No text layer: refused with an explanation rather than an empty result |

Run 04 then 05 back to back — 83% against 0% is the clearest way to show the
completeness score means something.

## Tests

```bash
cd backend && python -m pytest -q      # 112 passed
```

Tests use a temporary corpus and index, and force extractive mode, so they are
deterministic and make **no network calls**. That also means the offline paths
— heuristic ranking, the Hindi glossary, extractive answers — are the ones under
test, which is correct: those are what run when a venue's Wi-Fi fails.

---

## Project layout

```
project/
├── backend/
│   ├── app/
│   │   ├── config.py              # env-driven settings
│   │   ├── models.py              # Standard record + API schemas
│   │   ├── bis_reference.py       # the 17 BIS departments + the 6 schemes
│   │   ├── main.py                # FastAPI app; also serves frontend/dist
│   │   ├── ingestion/             # collector, normalize, enrich, calibrate
│   │   ├── rag/                   # embeddings, vectorstore, retriever, llm
│   │   ├── services/              # chat, recommend, catalogue, spec,
│   │   │                         # certification, language, analytics
│   │   └── routers/               # chat, recommend, catalogue, health/stats
│   ├── tests/                     # 112 tests, no network required
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # rail navigation + shared state
│   │   ├── api.js                 # backend client (relative /api paths)
│   │   ├── i18n.js                # English + Hindi UI strings
│   │   ├── styles.css             # design system, no CSS framework
│   │   └── components/            # Overview, RecommendPanel, AskPanel,
│   │                              # SpecPanel, BrowsePanel, StandardDrawer,
│   │                              # Header, StatusBar, Shared
│   ├── scripts/capture.mjs        # drive the site in Chrome, save screenshots
│   └── vite.config.js             # dev proxy /api → :8000
├── data/
│   ├── seed/standards.jsonl       # 95 curated records with scope/QCO (committed)
│   ├── raw/                       # collector cache (gitignored)
│   ├── processed/                 # normalized corpus (gitignored)
│   └── chroma/                    # vector index (gitignored, rebuildable)
└── scripts/                       # setup, run_demo, run_dev, run_dev_full
```

## Frontend notes

- **React + Vite**, plain CSS with custom properties — no Tailwind, no CSS-in-JS,
  no external fonts or CDNs. The UI renders fully offline.
- **Same URLs in dev and prod.** The app only ever calls relative `/api/...`.
  Vite proxies that in development; FastAPI serves the built bundle in
  production. No environment switching, no CORS surprises during a demo.
- **The status bar tells the truth.** It reports the engine that actually
  answered the last request, not just what is configured — if the API was
  unreachable and the answer came from the fallback, the pill says
  "Extractive mode".
- **Accessible by default.** Skip link, roving arrow-key navigation on the rail,
  `role="meter"` with `aria-value*` on every score, live regions on results,
  a focus-visible treatment on every control, and `prefers-reduced-motion`
  honoured. Targeting GIGW 3.0, which government software is scored against.
- **Bilingual.** English and Hindi, from a plain dictionary in `i18n.js` — no
  i18n library, no webfont. Hindi *retrieval* falls back to an offline BIS
  glossary when no translation model is reachable, so it works with the Wi-Fi off.
- The reference graph and ICS treemap are hand-rolled SVG/flexbox. No chart
  library — one radial layout does not justify 100 kB and a CDN.
- Bundle is ~255 kB (77 kB gzipped) with no UI dependencies beyond React.

## Scaling the corpus

`standards.bis.gov.in` is an Angular SPA — its HTML contains nothing. The data
comes from the JSON API its bundle calls, which the collector pages through:

```bash
cd backend
python -m app.ingestion.collector          # 24,324 records, ~2 min, caches to data/raw/
python -m app.ingestion.taxonomy           # sector/sub-sector classification, ~7 min
python -m app.ingestion.collector --from-cache  # re-merge with the taxonomy
python -m app.ingestion.build_index --rebuild   # ~2.5 min
python -m app.ingestion.calibrate          # the floors WILL have moved
```

**What that API gives, and what it does not.** It publishes IS number, title,
department, sectional committee, type of standard and publication date. It
publishes **no scope text, no ICS codes, no QCO status and no normative
references** — so the collector *merges* rather than replaces, overlaying the 95
hand-curated records that carry that depth.

**Subject classification comes from a second crawl.** On `catalogue-list` each
sector's "No. of Standards" is a hyperlink; the page's Excel exports keep the
counts and drop the link. `taxonomy.py` rebuilds what the link leads to, via
`getSectorsWithSubSectorsAndCounts` and `getStandardsBySectorId`. Sector mode
and sub-sector mode are **disjoint** views (2,889 and ~17,431 standards), so
both are crawled — together they classify **19,057 of 24,324 records** into 384
sectors and 956 sub-sectors. That matters for retrieval: without it most records
are embedded from their title alone.

Curated records are matched by *edition key* (the IS number without its year),
which means the portal corrects stale hand-authored data instead of duplicating
it: **22 curated years were wrong and were fixed automatically** (IS 1077:1992 →
IS 1077:2025, IS 1904:1986 → IS 1904:2021, and so on). A further 18 curated
numbers are published in no edition at all — some genuinely superseded (IS 8112
and IS 12269 were absorbed into IS 269:2015), some umbrella numbers for
multi-part series — and the collector prints them as verification leads.

`normalize.py` maps varying column names via aliases, so other catalogue exports
(CSV→JSON, portal scrapes) can feed the same pipeline.

> **Heads up:** `standards.bis.gov.in` is a JS-rendered SPA and **renders blank
> under headless automation** — it cannot be scraped naively. Server-rendered
> alternatives are `bis.gov.in/compendium-of-indian-standards/` and the public
> CRS dashboard at `crsbis.in`.

**After any material corpus change, re-run `python -m app.ingestion.calibrate`.**
A bigger corpus raises the noise ceiling, and the relevance floors have to move
with it — the script fails loudly if they no longer sit in the gap.

---

## Known limitations (be upfront in Q&A)

- **Depth covers 95 records, breadth covers 24,324.** IS numbers, titles,
  departments, committees and years now come from the official portal and are
  authoritative. Scope text, ICS codes, QCO flags and the reference graph exist
  only for the hand-curated seed, because the portal API publishes none of them.
  Records are tagged `unverified` in the UI until checked. **Still the
  highest-risk open item** — the collector's 18-number `unmatched` list is a
  ready-made worklist.
- **Titles are the main retrieval signal at scale**, and that compresses scores.
  The LED-bulb query retrieves exactly the right standards (IS 16103, IS 16101,
  IS 16102) and still only scores 0.488, where a curated record with scope text
  scores 0.95. It is why the floors moved, and why adding scope text would do
  more for quality than any further model change.
- **QCO flags are set conservatively.** Only well-established Quality Control
  Orders are flagged; anything uncertain is left as voluntary. A missing
  mandatory flag is recoverable, a wrong one is not.
- **Scope summaries, not clause text.** The assistant cannot quote a specific
  limit or test value — by design, and it says so.
- **One slow request when the network blackholes.** If DNS/TCP hangs rather than
  refusing outright (a captive-portal or firewalled venue), the first LLM attempt
  can take ~40s before the circuit breaker trips; every request for the next 60s
  is then instant. If you expect a hostile network, just leave
  `ANTHROPIC_API_KEY` unset and demo in extractive mode — every response is then
  sub-100 ms.

- **Multilingual answers need a model; multilingual *retrieval* does not.** The
  embedding model is English-only, so a Hindi query is translated before
  retrieval. When no translation model is reachable — agentrouter.org returns
  `content-blocked` for translation-shaped prompts — it falls back to an offline
  BIS domain glossary and says so. Precision is lower than English.

## Roadmap

- [x] React web app (chat + recommendation, mobile responsive)
- [x] Hybrid retrieval (semantic × lexical × ICS overlap) for better ranking
- [x] Normative-reference graph, with one-hop expansion in the recommender
- [x] QCO / mandatory-certification flags and per-scheme conformity pathways
- [x] Tender analyser: outdated citations + missing normative references
- [x] Catalogue browse, facets, and honest coverage against real BIS totals
- [x] Hindi + English, with an offline fallback for retrieval
- [x] Query analytics, including the unanswered-query gap list for BIS
- [ ] Verify the corpus against the official catalogue (highest-risk item)
- [ ] BIS services knowledge base: hallmarking, consumer grievances, testing labs
- [ ] Deploy to Render/Railway with a local fallback for judging

See `IMPROVEMENT-WALKTHROUGH.md` for the full gap analysis against the SIH26107 /
SIH26107 expected-solution bullets and the reasoning behind each of these.
