# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**ManakMitra** — AI assistant and recommendation engine for Indian Standards (BIS).
Built for Smart India Hackathon 2026, problem statement **SIH26107** — *AI-powered
Intelligent Assistant for Indian Standards and BIS Services* (Ministry
of Consumer Affairs → Bureau of Indian Standards).

Served from one FastAPI app:

- `POST /api/chat` — RAG Q&A grounded in the BIS catalogue, answers cite IS numbers.
- `POST /api/recommend` — plain-language product/procurement spec → ranked
  applicable IS codes with a rationale, confidence and **certification
  obligation**. This is the differentiator over a plain chatbot; treat it as the
  primary feature.
- `POST /api/analyze-spec` — tender text → per-line-item standards, outdated
  citations, and normative references the document is missing.
- `POST /api/analyze-spec/upload` — the same, from a tender **PDF**.
- `GET /api/standards`, `/facets`, `/coverage`, `/graph/{is}`,
  `/certification/{is}`, `/analytics/queries` — catalogue browse, honest
  coverage against real BIS totals, the reference graph, and query telemetry.
- `GET /api/services` — BIS **service** guidance: hallmarking, testing
  laboratories, consumer protection, certification schemes.

Only public catalogue **metadata** is indexed (IS number, title, scope summary,
sector, committee). Full standard texts are copyrighted and deliberately excluded.

`IMPROVEMENT-WALKTHROUGH.md` at the project root holds the gap analysis against
the literal SIH26107 expected-solution bullets, the BIS catalogue research
behind `app/bis_reference.py`, and the remaining roadmap.

## Commands

Backend commands must run from `backend/` (`pytest.ini` sets `pythonpath = .`).

```bash
# Backend setup + run
cd backend
pip install -r requirements.txt
python -m app.ingestion.build_index --rebuild   # required before first run
uvicorn app.main:app --reload                   # :8000

# Tests (112 currently; no network, deterministic)
python -m pytest -q
python -m pytest tests/test_retriever.py -q                    # one file
python -m pytest tests/test_api.py::test_chat_declines_when_nothing_is_relevant -q   # one test

# Corpus maintenance
python -m app.ingestion.enrich            # dry-run the curated enrichment pass
python -m app.ingestion.enrich --write    # apply it to data/seed/standards.jsonl
python -m app.ingestion.calibrate         # re-measure the two relevance floors

# Sample tender PDFs for the tender checker (samples/tenders/, committed)
python scripts/make_sample_tenders.py     # run from the project root

# Collect the full published catalogue from the official BIS portal (~2 min)
python -m app.ingestion.collector         # 24,324 records -> data/processed/
python -m app.ingestion.taxonomy          # sector/sub-sector classification (~7 min)
python -m app.ingestion.collector --from-cache   # re-merge, no network
python -m app.ingestion.build_index --rebuild    # ~2.5 min at this scale
python -m app.ingestion.calibrate                # floors WILL have moved

# Frontend
cd frontend
npm install
npm run dev        # :5173, proxies /api to :8000
npm run build      # emits dist/, which the backend then serves
npm run capture    # drives the running site in Chrome, writes frontend/shots/*.png

# Expand the corpus from the public data.gov.in BIS catalogue (needs keys in .env)
cd backend
python -m app.ingestion.collector
python -m app.ingestion.build_index --rebuild
```

PowerShell wrappers in `scripts/`: `setup.ps1` (one-time), `run_demo.ps1`
(build UI + serve everything on :8000 — use for demos), `run_dev_full.ps1`
(backend + Vite dev server with hot reload).

## Architecture

Request flow: `routers/ → services/ → rag/ → Chroma`. Embeddings and retrieval
are **always local**; only answer generation calls a hosted model.

```
corpus (JSONL) → ingestion/build_index → sentence-transformers → ChromaDB
                                                                     ↓
                            rag/retriever.search(query, floor)  ──────┘
                                     ↓
              services/chat.py          services/recommend.py
                     ↓                          ↓
              rag/llm.py provider (Claude) or fallback
                     ↓
                 routers/ → FastAPI
```

### Graceful degradation is a core design property, not an add-on

Every layer is built so a live demo cannot hard-fail on an API outage. Preserve
this when editing `rag/llm.py`, `services/chat.py`, or `services/recommend.py`:

1. No `ANTHROPIC_API_KEY` → `NullProvider`, `available = False`.
2. Any SDK error → `LLMUnavailable` → chat returns an **extractive** answer
   (retrieved entries verbatim), recommend falls back to **keyword-overlap**
   rationales. Both still return citations/rankings.
3. A **circuit breaker** in `AnthropicProvider` trips on failure, so only the
   first affected request pays the timeout; the rest degrade instantly for
   `llm_circuit_cooldown_seconds`.
4. `used_model` in every response names the engine that actually answered. The
   frontend status pill reads this, not the config — it must never claim "LLM"
   when a fallback produced the answer.

### Hybrid ranking (`rag/retriever.py`)

Semantic similarity alone confuses *subject* with *product*: for "stainless
steel water bottle" it ranked IS 14543 (packaged drinking **water**) above
IS 5522 (steel for utensils). Two local re-rankers correct that:

    final = cosine · (1 + 0.25·lexical + 0.15·ICS-affinity)

The blend is **multiplicative and centred**, not additive. Neutral evidence
leaves a score exactly where it was — an additive blend lifts every score by a
constant and silently invalidates the floors below, which is a bug this codebase
has already had once. `lexical` is the IDF-weighted fraction of the query a
candidate covers (absolute, never normalised against the best candidate, for the
same reason). Light plural stemming matters more than it looks: "bottles" not
matching the keyword "bottle" was enough to lose the signal entirely.

### Two relevance floors, deliberately different (`rag/retriever.py`)

Calibrated for the full 24,324-record catalogue
(`python -m app.ingestion.calibrate` prints the distributions and fails loudly
if a floor drifts out of its window):

    relevant queries      0.677 - 1.000
    product descriptions  0.488 - 0.797
    domain-adjacent       0.383 - 0.490
    clearly off-topic     0.142 - 0.333

- `RELEVANCE_FLOOR = 0.58` (chat) — must clear the **domain-adjacent** band, not
  just the obviously off-topic one. "Customs duty rates for importing textiles
  into Brazil" is unanswerable from a standards catalogue but says *textiles*,
  and there are 1,634 textile standards for it to land on (it scores 0.490).
- `RECOMMEND_FLOOR = 0.42` (recommend) — deliberately sits *below* that band. Its
  input is a product description, not a question; returning a weak candidate
  whose meter visibly reads "Review needed" beats refusing a real product. Chat
  is the surface that refuses, recommend is the surface that must not stonewall.

**Both floors have moved twice, and will move again.** 51 records → 0.35/0.15;
95 → 0.45/0.35; 24,324 → the values above. Two forces drive it: more documents
raise the noise ceiling, and the portal publishes no scope text, so most records
are embedded from their title alone and every score compresses downward. The
LED-bulb description retrieves exactly the right standards (IS 16103, IS 16101,
IS 16102) and still only scores 0.488. **Never carry these constants across a
corpus change** — re-run `calibrate`.

### The reference graph

`normative_refs` / `test_methods` / `supersedes` model how standards cite each
other. `retriever.expand_related()` walks one hop out from the semantic hits,
which surfaces standards no embedding would find — a query about an apartment
block retrieves IS 456, and IS 456 pulls in the cement, aggregate and rebar
standards. Neighbours inherit a decayed score so they rank below direct hits.

Keep reference numbers **out of** `Standard.embedding_text()`: they are noise in
vector space and belong in the traversal step.

### BIS services are a second knowledge base (`bis_services.py`)

SIH26107 asks for consumer protection, hallmarking and testing-laboratory
guidance. The catalogue holds IS numbers and titles, so it correctly finds
nothing for "how do I complain about a fake ISI mark" — a refusal that reads as
a failure. `app/bis_services.py` holds ~17 curated entries, each with a
**source URL on bis.gov.in**, retrieved by `services/knowledge.py` (in-memory
cosine — too few entries to justify a Chroma collection).

`chat.answer()` routes to it in two ways:

1. **Intent first.** `knowledge.looks_like_service_question()` is a keyword
   router, and it exists because similarity alone gets the important case
   wrong: *"which laboratory can test my drinking water sample"* is dominated
   by "drinking water" and retrieves IS 3025 and IS 17614 — water *test-method*
   standards — so someone asking where to get something tested is handed a
   reading list. The product noun is the loudest token but the question is not
   about the product. It fails safe: no match means the catalogue answers.
2. **Fallback.** When the catalogue clears no hit, services are tried before
   declining.

Off-topic questions must still decline — adding a second knowledge base is
exactly how a system that used to refuse starts answering everything.
`tests/test_services.py` guards that.

Never put a fee, a processing time or a helpline number in these entries: they
change, we cannot cite them, and a test asserts their absence.

### QCO / certification

`qco_mandatory` + `qco_name` is the difference between "this standard is
relevant" and "you may not legally sell without it". Never set the flag without
a nameable Quality Control Order behind it — `test_catalogue.py` asserts this
across the whole corpus, because a wrong mandatory claim is the one error a BIS
jury spots instantly.

### Corpus and index

`config.active_corpus()` prefers `data/processed/standards.jsonl` (collector
output) and falls back to the committed `data/seed/standards.jsonl` (95 curated
records). Delete the processed file to drop back to the seed.

**The processed corpus is the full published BIS catalogue — 24,324 records.**
`ingestion/collector.py` pages it out of the portal's own JSON API:

    POST https://standardsadmin.bis.gov.in/proposal-service/getWebsiteIndianStandardsList
    {"page": 1, "pageSize": 100}      # pageSize is capped at 100 server-side

Things that matter about that API:

- It returns IS number, title, department, sectional committee, type of standard
  and publication date. It returns **no scope text, no ICS codes, no QCO status
  and no normative references**.
- Subject classification comes from a *second* pair of endpoints, crawled by
  `ingestion/taxonomy.py`: `getSectorsWithSubSectorsAndCounts` (210 sectors /
  1,009 sub-sectors) and `getStandardsBySectorId`. These are the buckets behind
  the "No. of Standards" hyperlinks on `catalogue-list`. **Sector mode and
  sub-sector mode are disjoint views** — 2,889 and ~17,431 standards
  respectively — so both are crawled. Result: **19,057 of 24,324 records
  classified** into 384 sectors and 956 sub-sectors, joined on `standardId`
  (IS numbers are written too inconsistently across the portal to join on).
  It lands in `data/processed/taxonomy.json` and feeds
  `Standard.embedding_text()`, which for most records is otherwise just a title.
- QCO status and the reference graph still come only from `ingestion/enrich.py`.
- It mixes back issues of the BIS house magazine *Standards India* in with the
  standards (`SI B2410:2011`). They are filtered out: their broad article titles
  were topping the results for real product queries.
- The collector **merges** rather than replaces. Curated records match by
  *edition key* — the IS number without its year — so the portal corrects stale
  hand-authored years instead of leaving two records for one standard. 22
  curated years were wrong and were fixed this way.
- 18 curated numbers are published in no edition on the portal. Some are
  genuinely superseded (IS 8112 and IS 12269 were absorbed into IS 269:2015);
  some are umbrella numbers for multi-part series (IS 3025, IS 2386). The
  collector prints them as verification leads rather than silently dropping them.

`ingestion/normalize.py` maps varying column names via aliases so other
catalogue exports feed the same pipeline. The Chroma index in `data/chroma/` is
gitignored and always rebuildable — a full rebuild takes about 2.5 minutes.

### Frontend

React + Vite, plain CSS with custom properties — **no Tailwind, no external
fonts or CDNs** (the UI must render offline). The app only ever calls relative
`/api/...`: Vite proxies that in dev, FastAPI serves the built bundle in prod, so
no environment switching or CORS handling is needed.

## Gotchas

- **Chroma metadata must be scalars.** List fields are joined on write and split
  on read in `rag/vectorstore.py`. Both directions are driven off the single
  `_LIST_FIELDS` tuple — add a new list field there and nowhere else. Optional
  scalars need `_NULLABLE_SCALARS` too, since Chroma rejects `None`.
- **`vectorstore.all_standards()` is cached per process** and invalidated by
  `add_standards()` / `reset()`. Anything that mutates the collection by another
  route must clear `_ALL_CACHE`.
- **Never guard the Chroma client with `lru_cache`.** FastAPI runs sync
  endpoints in a threadpool and the dashboard fires four API calls in parallel
  on mount. `lru_cache` does not serialise the call it wraps — on a miss *every*
  waiting thread runs the body — so multiple `PersistentClient`s get built at
  once and race Chroma's process-global `SharedSystemClient` registry. The
  symptom is *intermittent* 500s on page load (`KeyError: '<chroma dir>'`,
  `AttributeError: 'RustBindingsAPI' object has no attribute 'bindings'`) that
  vanish on the next refresh. `_client()` uses an explicit lock with a
  double-check, and exposes `.cache_clear()` for the test fixtures.
  `tests/test_catalogue.py` guards it.
- **IS numbers are written inconsistently** — `IS 1893 (Part 1):2016`,
  `IS 1893 (Part 1) : 2016`, bare `IS 1893`. Compare with
  `vectorstore._normalise_ref()`, and resolve citation families with
  `services/spec._family_key()`. Never compare raw strings.
- **Hindi retrieval does not depend on the LLM.** `services/language.py` tries
  model translation first and falls back to an offline BIS domain glossary,
  because agentrouter.org returns `content-blocked` for translation-shaped
  prompts. Test the offline path — that is the one that runs in a demo.
- **The static mount must stay last in `main.py`.** `StaticFiles` is mounted at
  `/`, so registering it before the routers would shadow `/api/*` and `/docs`.
  `/` serves the app when `frontend/dist` exists, else redirects to `/docs` —
  tests cover both branches.
- **OS environment variables outrank `backend/.env`** (pydantic-settings
  precedence). A shell exporting `ANTHROPIC_MODEL`/`ANTHROPIC_API_KEY` silently
  overrides the file. Check `GET /api/stats` to see what is actually in use.
- **Never append a date suffix to a Claude model ID.** Use `claude-haiku-4-5`,
  not `claude-haiku-4-5-20251001`. Also do not send `thinking` or
  `output_config.effort` from `rag/llm.py`: Haiku 4.5 rejects them, and omitting
  them keeps the adapter valid across the Opus/Sonnet 5 models too.
- **Tests mutate settings via env vars** in `tests/conftest.py` and must clear
  the `lru_cache` on `get_settings`, `vectorstore._client`, and `llm.get_provider`.
  They force `ANTHROPIC_API_KEY=""` so no test hits the network. Follow that
  pattern for new fixtures.
- **PDF text has *visual* lines, not logical ones.** `services/pdfdoc.py` must
  reflow before segmenting: a clause wraps over three lines, running headers
  repeat per page, and BOQ tables extract as prose-looking rows. Feeding raw
  extraction into `spec.analyze` produced line items like
  `"1 Service Sector Department (SSD) 163"` and matched standards to table
  cells. Four filters earn their place — furniture (lines repeating on >50% of
  pages), table rows (ends in a bare number, ≥2 numbers, no terminal
  punctuation), ALL-CAPS headings, and "a clause ending in a full stop is
  finished" (without the last one the next page's header glues onto it).
  `_CLAUSE_START` and `_CLAUSE_PREFIX` must stay in sync or numbering leaks
  into the embedding.
- **Uploads are parsed in memory and never written to disk** — tender documents
  are frequently confidential and often pre-award.
- **Paths in this repo contain a space** (`SIH 2026`). In Node, use
  `fileURLToPath`, not `URL.pathname` — the latter leaves `%20` encoded and
  silently creates a literal `SIH%202026` directory.

## Known project constraint

The corpus is the **full published BIS catalogue, 24,324 records across all 17
technical departments**, collected from the official portal — so IS numbers,
titles, departments, committees and years are authoritative for those fields.

What is *not* authoritative, and remains the highest-risk open item:

- **Scope text, ICS codes, QCO status and the reference graph exist for only 95
  records** — the hand-curated seed. The portal API publishes none of it. Every
  record carries `verification: "unverified"` and the UI shows the tag; only
  records taken from an official BIS publication are marked `verified`.
- **QCO flags are set conservatively.** A wrong "certification is mandatory"
  claim is the one error a BIS jury spots instantly, so anything uncertain is
  left voluntary. `tests/test_catalogue.py` asserts no record claims mandatory
  without naming an order.
- The collector's `unmatched` list (18 numbers) is a ready-made verification
  worklist.

Note that `standards.bis.gov.in` itself is an Angular SPA and renders nothing
without JavaScript — do not try to scrape its HTML. The JSON API above is the
supported path. Server-rendered alternatives for cross-checking:
`bis.gov.in/compendium-of-indian-standards/` and
`crsbis.in/BIS/publicdashAction.do?hmode=getProductCategory`.
