# ManakMitra — Improvement Walkthrough

**Prepared:** 22 August 2026 · **Implemented:** 22 August 2026
**Scope:** BIS catalogue research, gap analysis against the official SIH problem
statements, dashboard design, and a prioritised build order.

This document was written against the system described in
`ManakMitra-Project-Context.pdf` — 51 seed standards, `/api/chat`,
`/api/recommend`, `/api/health`, `/api/stats`, a two-tab React SPA, 28 passing
tests.

> ## Implementation status
>
> **Tiers 1–4 are built**, except where noted. The corpus is now **95 records
> across 16 of 17 BIS departments**, the test suite is **79 passing**, and the
> UI is a five-surface dashboard. What changed, against §7:
>
> | Tier 1 | |
> |---|---|
> | Rebalance the corpus | ✅ 51 → 95 records, 8 → 16 departments, Civil 51% → 27% |
> | QCO + certification fields, mandatory/voluntary split | ✅ 24 standards flagged, split in the UI |
> | Normative-reference graph + one-hop expansion | ✅ `expand_related()`, `GET /api/graph/{is}` |
> | Clickable IS numbers → detail drawer | ✅ everywhere, with a stacking drawer |
>
> | Tier 2 | |
> |---|---|
> | Overview: KPIs, coverage-vs-real, ICS treemap | ✅ hand-rolled SVG/flexbox, no chart library |
> | Browse + facets | ✅ `GET /api/standards`, `/facets` |
> | Version currency + outdated-reference banner | ✅ in the tender analyser and the drawer timeline |
> | Certification pathway stepper | ✅ `GET /api/certification/{is}` |
> | Hybrid ranking + floor recalibration | ✅ **and it moved both floors** — see below |
>
> | Tier 3 | |
> |---|---|
> | Tender analyser + completeness score | ✅ `POST /api/analyze-spec` |
> | BIS services knowledge base | ❌ **not built** — the one substantial gap left |
> | Hindi + English | ✅ plus an *offline* retrieval fallback the plan did not anticipate |
> | Export CSV | ✅ on every result set |
>
> | Tier 4 | |
> |---|---|
> | Accessibility pass | ✅ skip link, roving tabindex, `role="meter"`, live regions, reduced-motion |
> | Query analytics + BIS gap tile | ✅ `GET /api/analytics/queries` |
> | Skeletons, recent queries, better empty states | ✅ (⌘K palette skipped as low-value) |
> | Compare view | ❌ skipped — the detail drawer covers most of the need |
> | Hosted deployment | ❌ not attempted |
>
> ### Three things the plan got wrong
>
> 1. **§4.1's additive blend was a bug.** `0.60·cosine + 0.25·lexical +
>    0.15·ICS` raises *every* score by a constant floor, which pushed off-topic
>    queries back over the relevance floor — a test caught it immediately. The
>    blend is now multiplicative and centred on neutral, so the floors stay valid:
>    `cosine · (1 + 0.25·lexical + 0.15·ICS)`. Normalising lexical scores against
>    the best candidate was the same mistake in miniature; it is now absolute
>    query-coverage.
> 2. **§4.2 was more urgent than "after any corpus change".** Growing to 95
>    records raised the noise ceiling from ~0.21 to **0.31**, which put the old
>    `RECOMMEND_FLOOR = 0.15` *below* it — the endpoint would have returned pure
>    noise. Both floors moved: **0.35 → 0.45** (chat) and **0.15 → 0.35**
>    (recommend). `python -m app.ingestion.calibrate` now measures this and fails
>    loudly.
> 3. **§6.3 assumed a translation model would be available.** It is not:
>    agentrouter.org returns `content-blocked` for translation-shaped prompts. So
>    Hindi retrieval falls back to an offline BIS domain glossary, which lands
>    the right standard at 0.83–0.95 confidence with the network off. Better than
>    the original plan, and consistent with the project's offline guarantee.
>
> The rest of this document is the original analysis, unchanged. §1 (BIS
> research) is now encoded in `backend/app/bis_reference.py`; §7's remaining
> unticked rows are the live roadmap.

---

## 0. Read this first — the one finding that reframes the project

I pulled the **actual text of both problem statements** from the scraped SIH 2026
set. They ask for considerably more than a chatbot plus a recommender, and the
extra asks are the marks nobody else will chase.

> **SIH26107** — *"AI-powered Intelligent Assistant for Indian Standards and BIS
> Services for Industries and Consumers"*
> Expected solution: answer queries on Indian Standards · **suggest standards
> from product details** · **guide on certification pathways** · **explain
> conformity assessment procedures** · **answer consumer-protection questions** ·
> **hallmarking guidance** · **identify testing facilities** · **multilingual**.

> **SIH26108** — *"AI-Powered Recommendation Engine for Identifying Applicable
> Indian Standards for Procurement Specifications"*
> Expected solution: accept **product descriptions *and tender documents*** ·
> recommend by *"semantic understanding rather than keyword matching"* ·
> **identify allied standards, normative references and test methods** ·
> **highlight current versions and amendments** · **suggest mandatory
> certifications** · multilingual · **integrate with procurement portals**.

Source: `github.com/vedantchalke36/sih-2026-problem-statements/ps_2026/SIH26107.md`
and `SIH26108.md` (scraped from sih.gov.in, last update 2026-08-21).

### Scorecard against the literal asks

| Requirement | PS | Status today | Where it lands below |
|---|---|---|---|
| Q&A on Indian Standards | 107 | ✅ Done, well | — |
| Suggest standards from product details | 107, 108 | ✅ Done, well | — |
| Semantic, not keyword | 108 | ✅ Done (local embeddings) | §4 hybrid ranking |
| Certification pathway guidance | 107 | ❌ **Absent** | §3.2, §5 Card C |
| Conformity assessment procedure | 107 | ❌ **Absent** | §3.2 |
| Consumer-protection Q&A | 107 | ❌ **Absent** | §6.4 |
| Hallmarking guidance | 107 | ❌ **Absent** | §6.4 |
| Testing-facility lookup | 107 | ❌ **Absent** | §6.4 |
| Multilingual | 107, 108 | ❌ **Absent** | §6.3 |
| Tender document as input | 108 | ❌ **Absent** | §5 Card E |
| Allied / normative references | 108 | ❌ **Absent — biggest single gap** | §3.3, §5 Card D |
| Test methods | 108 | ❌ Absent | §3.3 |
| Current version & amendments | 108 | ❌ **Absent** | §3.4 |
| Mandatory certification (QCO) flag | 108 | ❌ **Absent** | §3.2 |
| Procurement-portal integration | 108 | ❌ Absent | §5 Card E (export) |

**Read the scorecard honestly: the two things you have are excellent and the
other thirteen are unbuilt.** The good news is that most of them are *data*
problems, not architecture problems — your retriever, degradation strategy and
UI shell already support them. §7 sequences them.

---

## 1. BIS catalogue research — verified facts you can quote

Pulled from the BIS *Standard catalogue — July '25* deck published by SESEI
(the Seconded European Standardization Expert in India), cross-checked against a
PIB press release.

### 1.1 The real numbers

| Metric | Value | As of |
|---|---|---|
| Published Indian Standards | **23,461** | June 2025 |
| Technical departments | **17** | June 2025 |
| Sectional committees | **405+** | June 2025 |
| Division councils | 16 | Feb 2024 (PIB) |
| Domain experts involved | ~19,000 | Feb 2024 (PIB) |
| New standards added in 2025 | 600+ (total → 23,293) | Dec 2025 |

Harmonisation split of all 23,461: **13,415 indigenous**, 2,597 identical
(single numbering), 5,921 identical (dual numbering), 860 modified/technically
equivalent, 668 not equivalent.

> **Use this in your pitch.** "23,461 standards across 17 departments" is a far
> stronger framing than "thousands", and it is a citable number.

### 1.2 The 17 technical departments, with real counts

This is the authoritative taxonomy. Your `sector` field should map onto it
exactly, and your dashboard should show coverage against these denominators.

| # | Department | Code | Published |
|---:|---|---|---:|
| 1 | Production and General Engineering | **PGD** | 2,589 |
| 2 | Food and Agriculture | **FAD** | 2,338 |
| 3 | Chemical | **CHD** | 2,101 |
| 4 | Civil Engineering | **CED** | 2,005 |
| 5 | Electrotechnical | **ETD** | 1,954 |
| 6 | Metallurgical Engineering | **MTD** | 1,774 |
| 7 | Medical Equipment and Hospital Planning | **MHD** | 1,743 |
| 8 | Electronics and Information Technology | **LITD** | 1,604 |
| 9 | Textiles | **TXD** | 1,547 |
| 10 | Petroleum, Coal and Related Products | **PCD** | 1,525 |
| 11 | Mechanical Engineering | **MED** | 1,453 |
| 12 | Transport Engineering | **TED** | 1,363 |
| 13 | Management and Systems | **MSD** | 544 |
| 14 | Water Resources | **WRD** | 462 |
| 15 | Ayush | **AYD** | 178 |
| 16 | Service Sector | **SSD** | 163 |
| 17 | Environment and Ecology | **EED** | 118 |
| | **Total** | | **23,461** |

Two naming traps worth knowing: Electronics & IT is **LITD** (not "EITD"), and
Management & Systems is **MSD** (not "MND").

### 1.3 What your seed corpus actually looks like against that

I audited `data/seed/standards.jsonl` directly:

```
51 records · 8 of 17 departments represented
CED 26  ETD 8  MTD 7  CHD 4  FAD 3  LITD 1  MSD 1  PCD 1
5 records have no `year` field: IS 3025, IS 2386, IS 4031, IS 2720, IS 1200
```

Good news: **every committee prefix in the corpus is a genuine BIS department
code.** No invented taxonomy.

Bad news: **the corpus is 51% Civil Engineering**, where the real catalogue is
8.5% Civil. And the single largest department — **PGD, 2,589 standards — has
zero representation**, as do TXD, MED, MHD, TED, WRD, SSD, EED and AYD.

The practical consequence is a demo failure mode: any question about textiles,
medical devices, machine tools, fasteners, or transport returns
*"not in the catalogue"* — which looks like the honesty feature working, but is
really a coverage hole. A BIS jury member will probe exactly there, because
those are their departments.

**Action:** rebalance to ~15 records per department across all 17, even if that
means dropping to 8 civil records. 17 × 15 = 255 records is still hand-verifiable
in a weekend and *looks* like a catalogue rather than a civil-engineering demo.
Breadth beats depth for a five-minute jury slot.

### 1.4 Data sources — what is actually reachable

| Source | URL | Usable? |
|---|---|---|
| BIS catalogue browse | `standards.bis.gov.in/website/catalogue-list` | JS-rendered SPA; **blocks headless browsers** (I confirmed this — renders blank under automation). Needs a real browser session or manual export. |
| Department-wise browse | `standards.bis.gov.in/website/published-standards/department-wise` | Same SPA; the canonical browse-by-department view. |
| Compendium of Indian Standards | `bis.gov.in/compendium-of-indian-standards/` | Server-rendered table (Title / Department / Sector). **Scrapable today.** |
| Products under compulsory certification | `bis.gov.in/product-certification/products-under-compulsory-certification/` | Landing page; the QCO product lists are on linked sub-pages and in a "Guidance Document on QCOs" PDF. |
| CRS public dashboard | `crsbis.in/BIS/publicdashAction.do?hmode=getProductCategory` | **Live public dashboard** — licences per product category, filterable by country. Real, queryable data for the CRS side. |
| SESEI catalogue deck | `sesei.eu/.../BIS-catalogue-July-2026.pdf` | PDF, updates ~monthly. Reliable for department totals. |
| data.gov.in | `data.gov.in` | Your `collector.py` already targets this. Coverage of the full catalogue is partial — verify before depending on it. |

> **Reality check on the collector.** Do not promise the jury "we can ingest all
> 23,461 automatically" unless you have actually run it end-to-end. The BIS SPA
> defeats naive scraping. A defensible line is: *"the pipeline is source-agnostic
> — normalize.py maps any catalogue export onto our schema; we seeded 255
> verified records and BIS can drop in the full export."* That is true, humble,
> and it lands better than an over-claim a BIS officer can puncture.

### 1.5 The five BIS conformity assessment schemes

You need these names right; they are the backbone of the "certification pathway"
requirement in SIH26107. All are built on IS/ISO/IEC 17067 principles and
operated through 5 regional and 41 branch offices.

| Scheme | Common name | Applies to |
|---|---|---|
| **Scheme I** | Product Certification / **ISI Mark** | Domestic manufacturers, licence to use the Standard Mark |
| **Scheme I (FMCS)** | Foreign Manufacturers Certification | Overseas manufacturers exporting to India |
| **Scheme II** | **CRS** — Compulsory Registration Scheme | Mostly electronics & IT goods; self-declaration + BIS-recognised lab test |
| — | **Hallmarking** | Gold and silver articles; HUID-based |
| **Scheme X** | Machinery & electrical equipment | Introduced under the Omnibus Technical Regulation |
| — | **Eco Mark** | Environment-friendly products |

Certification is **voluntary by default**; it becomes mandatory only when the
Central Government issues a **Quality Control Order (QCO)** for that product.
That distinction — *voluntary standard vs. QCO-mandated certification* — is the
single most valuable thing you can teach a user, and no other team will show it.

---

## 2. Where the current product falls short (UX audit)

Honest read of `frontend/src/`, having gone through every component:

1. **There is no way to see what is in the catalogue.** The user gets a text box
   and nothing else. The very first jury question — *"what's actually in
   there?"* — has no on-screen answer. `/api/stats` knows, but only the status
   bar's four sector chips surface it.
2. **Results are a dead end.** `RecommendPanel` renders a ranked list and stops.
   No click-through, no detail, no export, no save, no "what next". A
   procurement officer cannot *do* anything with the output.
3. **Confidence is unexplained.** `<Meter value={0.62} caption="Confidence" />`
   shows a bar. Nobody knows whether 0.62 is good. There is no legend, no
   banding, no tooltip.
4. **Citations don't link anywhere.** `StandardNumber` renders text. Every IS
   number should be a link to the BIS portal, or at minimum open a local detail
   panel.
5. **No history.** Refresh the page and the query is gone. Nothing to compare
   against, nothing to return to.
6. **Empty state blames the user.** *"Try describing the physical product… or
   index more of the catalogue with the collector"* leaks implementation detail
   at the user. It should instead suggest neighbouring departments or show the
   nearest near-misses below the floor.
7. **Two tabs is a thin information architecture** for a problem statement that
   lists eight capabilities.
8. **Monolingual**, against an explicit multilingual requirement in both PSs.
9. **Spinner, not skeleton.** With an LLM path measured at 7–35 s through the
   router, a bare spinner feels broken. Stream or stage the feedback.
10. **Accessibility is partial.** There is a `sr-only` label and `aria-current`
    on tabs — a good start — but the tab strip isn't a roving-tabindex widget,
    the meter has no `role="meter"`/`aria-valuenow`, and results don't announce
    via a live region.

None of these are hard. All of them are visible in a five-minute demo.

---

## 3. Data model v2 — the foundation for everything else

Most of the missing PS requirements are unlocked by four new field groups.
Extend `Standard` in `backend/app/models.py`.

### 3.1 Proposed record

```jsonc
{
  "is_number": "IS 10500:2012",
  "title": "Drinking Water — Specification",
  "scope": "...",
  "ics_codes": ["13.060.20"],
  "sector": "Chemical",
  "department_code": "CHD",              // NEW — join key to §1.2
  "technical_committee": "CHD 13",
  "status": "active",
  "year": 2012,

  // --- §3.2 certification & compulsion ---
  "qco_mandatory": false,                 // NEW
  "qco_name": null,                       // NEW e.g. "Toys (QCO), 2020"
  "qco_notified_on": null,                // NEW ISO date
  "certification_scheme": null,           // NEW "Scheme I" | "Scheme II (CRS)" | "Scheme X" | "Hallmarking"
  "conformity_route": null,               // NEW short prose: how to actually get certified

  // --- §3.3 the reference graph (SIH26108's core ask) ---
  "normative_refs": ["IS 3025 (Part 1)"], // NEW standards this one *requires*
  "test_methods": ["IS 3025"],            // NEW how conformity is measured
  "allied_standards": ["IS 14543:2016"],  // NEW commonly cited alongside

  // --- §3.4 version currency ---
  "revision": "Second Revision",          // NEW
  "reaffirmed_on": "2021-03",             // NEW
  "amendment_count": 1,                   // NEW
  "supersedes": ["IS 10500:1991"],        // NEW
  "superseded_by": null,                  // NEW

  "keywords": ["drinking water", "..."],
  "bis_url": "https://standards.bis.gov.in/..."  // NEW — makes citations clickable
}
```

### 3.2 Certification & compulsion

Powers *"suggest mandatory certifications where applicable"* (108) and
*"guidance on certification pathways"* (107). This is the highest
impact-to-effort item in the whole document: a single boolean turns a list of
standards into a **compliance obligation**, which is what the user actually
came for.

The demo line becomes: *"IS 16046 applies to your power bank — and it is under a
QCO, so CRS registration is **mandatory** before you can sell. Here is the
route."* That is a different product from a search box.

### 3.3 The reference graph — your strongest differentiator

SIH26108 explicitly asks for *"allied standards, normative references, and test
methods"*. Nobody builds this, because it needs relationships rather than
embeddings.

You don't need to parse copyrighted clause text. Every IS lists its normative
references in a public, non-copyrightable *"References"* front-matter section,
and the relationships between well-known standards are common domain knowledge —
e.g. IS 456 (concrete) normatively pulls in IS 383 (aggregates), IS 269 (cement),
IS 1786 (reinforcement bars), IS 516 (test methods for concrete strength).

Hand-authoring ~4 references per standard across 255 records is a few hours and
gives you:

- **Recall expansion.** Retrieve top-5 semantically, then walk the graph one hop
  to surface standards no embedding would ever match. A concrete query surfaces
  the *cement* standard — that is the moment a civil engineer on the jury nods.
- **A visual.** A reference graph renders beautifully (§5 Card D) and is
  instantly legible as "we modelled the domain", not "we called an API".
- **Completeness scoring.** Given a tender spec citing IS 456, you can report:
  *"your spec omits IS 383 and IS 1786, both normatively referenced"* — which is
  literally the *"incomplete specifications"* problem named in the PS background.

### 3.4 Version currency

*"Highlights current versions and amendments"* (108). The PS background names
*"outdated standard references"* as a cause of procurement disputes. With
`supersedes` / `superseded_by` / `amendment_count`, you can render a red banner:
**"Your tender cites IS 1893:2002 — superseded by IS 1893 (Part 1):2016, with 2
amendments."** That is a dispute prevented, on screen, in one line.

### 3.5 Implementation notes (things that will bite)

- **Chroma metadata must be scalars** — per `CLAUDE.md`. Every new list field
  (`normative_refs`, `test_methods`, `allied_standards`, `supersedes`) needs
  comma-join/split handling in **both** `to_metadata` and `from_metadata` in
  `rag/vectorstore.py`. Forgetting the second half fails silently.
- Keep the graph **out of the embedding text**. `embedding_text()` should stay
  title + scope + keywords + sector. Reference numbers are noise in vector space;
  they belong in a traversal step after retrieval.
- All new fields must be **optional with sane defaults**, so the existing 51
  records keep loading and the 28 tests keep passing while you backfill.
- Backfill the 5 missing `year` values while you are in there.

---

## 4. Retrieval quality

### 4.1 Hybrid ranking (already on your roadmap — do it)

Your README documents the failure honestly: for *"stainless steel water bottle"*,
heuristic mode ranks IS 14543 (packaged drinking *water*) above IS 5522 (steel
for utensils). Lexical proximity beats product identity. Fix:

```
final = 0.60 · cosine  +  0.25 · BM25(title+keywords)  +  0.15 · ICS-prefix overlap
```

ICS overlap is the cheap secret weapon: ICS is a hierarchical code, so
`77.140.*` (steel products) vs `13.060.*` (water quality) is a two-digit compare
that encodes real domain distance. Use `rank_bm25` (pure Python, no service) and
keep it fully offline — your "works with Wi-Fi off" claim survives intact.

Guard it with a test that asserts IS 5522 outranks IS 14543 for the bottle query.

### 4.2 Recalibrate the floors after any corpus change

`CLAUDE.md` warns about this and it is correct. `RELEVANCE_FLOOR = 0.35` and
`RECOMMEND_FLOOR = 0.15` were calibrated on 51 records. At 255 records the noise
ceiling rises — more documents means more chances for a spurious 0.4. **Re-measure
both distributions and re-derive the gap**; do not carry the constants over
blindly. Add a `scripts/calibrate.py` that prints the signal/noise histogram so
this is a command, not a memory.

### 4.3 Long-document input

For tender documents (108), a whole PDF embedded as one vector is mush. Chunk by
paragraph or line item, retrieve per chunk, then union and re-rank. This also
gives you per-line-item attribution in the UI — *"clause 4.2 → IS 2062"* — which
is far more useful than one flat list for the document.

---

## 5. Dashboard design

Replace the two-tab strip with a left rail and a workspace. Five surfaces.

```
┌──────────────────────────────────────────────────────────────────────┐
│  ManakMitra          [ Search all standards…  ⌘K ]      EN | हिं  ▾  │
├────────────┬─────────────────────────────────────────────────────────┤
│ ◉ Overview │                                                         │
│ ◉ Find     │                  W O R K S P A C E                      │
│ ◉ Ask      │                                                         │
│ ◉ Browse   │                                                         │
│ ◉ Compare  │                                                         │
│            │                                                         │
│ ─────────  │                                                         │
│ Recent     │                                                         │
│  · LED …   │                                                         │
│  · flats…  │                                                         │
├────────────┴─────────────────────────────────────────────────────────┤
│ ● Live · 255 standards · 17/17 departments · Engine: claude-opus-4-8 │
└──────────────────────────────────────────────────────────────────────┘
```

### Card A — Overview (the new landing surface)

The screen that answers *"what is in there?"* before anyone asks.

- **Four KPI tiles:** standards indexed · departments covered (17/17) · under
  QCO (mandatory) · normative links mapped.
- **Coverage bar chart** — indexed count per department *against the real BIS
  denominator from §1.2*. Showing "CED 15 / 2,005" is not a weakness; it is a
  claim of honesty and scale-awareness that a ministry jury will respect far more
  than a fake 100%.
- **ICS treemap** — instantly communicates "this is a real classification
  system", and doubles as a filter: click a block → Browse, pre-filtered.
- **Query analytics strip** (see §6.5) — top queries, and **unanswered queries**.

> **Pitch the analytics strip deliberately.** Every other team builds a tool for
> the *user*. This one tile is a tool for **BIS itself**: "these 40 queries found
> nothing — that is your standards-development gap list, generated from real
> demand." A ministry jury is evaluating what the ministry gets. Nothing else in
> your build speaks to them that directly.

### Card B — Find my standards (upgraded)

Keep the existing flow, then make the result actionable:

- **Split the results**: a **"Mandatory — certification required"** block above
  a **"Recommended — voluntary"** block. This is the single highest-value UI
  change available to you.
- **Confidence as a band, not a bare number**: High / Medium / Review needed,
  colour-coded, with a tooltip explaining what drives it.
- **Per item:** IS number (clickable) · title · why · confidence · QCO badge ·
  chips for normative refs.
- **Actions:** Copy as tender clause · Export CSV/PDF · Save to workspace.
- **"Also consider"** — the one-hop graph expansion from §3.3, visibly labelled
  as *"pulled in as a normative reference of IS 456"* so the mechanism is
  legible.

### Card C — Certification pathway

A stepper rendered from `certification_scheme` + `qco_*`:

```
Product → Applicable IS → Scheme (ISI / CRS / Scheme X / Hallmarking)
        → Test at a BIS-recognised lab → Apply → Licence → Mark
```

Each step in one plain sentence, with the fee/timeline caveat *"verify current
figures on the BIS portal"* — never hard-code a fee you cannot defend.
This closes four SIH26107 bullets on one screen.

### Card D — Standard detail (slide-over drawer)

Any IS number anywhere opens this. No navigation, no lost context.

Header (number, title, status, QCO badge) · scope · ICS · committee ·
**version timeline** (supersedes → current → amendments) · **reference graph**
(a small force-directed or radial SVG — this is the screenshot that goes on your
slide) · "Where to obtain" linking to the BIS portal.

### Card E — Tender / spec analyser

Paste or upload a tender document. Output: a per-line-item table —
*line item → matched IS → mandatory? → cited version current? → missing
normative refs*. Plus a **spec completeness score**.

This is SIH26108's literal ask and the most defensible "procurement portal
integration" story: export the annotated spec as CSV/JSON, and note that the same
payload is a REST call GeM could make.

### Card F — Compare

Two or three standards side by side: scope, ICS, committee, status, year. Solves
the real user question *"IS 456 or IS 800 — which one governs me?"*

---

## 6. User-friendliness

### 6.1 Immediate wins (each under an hour)

- Make **every IS number clickable** → opens Card D.
- **Confidence legend** with banding and a plain-language tooltip.
- **Copy** and **Export CSV** buttons on every result set.
- **Recent queries** in `localStorage`, in the left rail.
- **Skeleton loaders** matching the result card shape, not a spinner.
- **Better empty state**: show the near-misses that fell below the floor, greyed,
  labelled *"below our confidence threshold"* — it proves the floor is working
  rather than looking like a dead end.
- **⌘K command palette** for search-anything. Cheap, and it reads as polish.

### 6.2 Accessibility (do it — it is explicitly scored in government software)

- Roving `tabindex` on the nav rail; arrow-key navigation.
- `role="meter"` + `aria-valuenow`/`aria-valuemin`/`aria-valuemax` on `Meter`.
- `aria-live="polite"` region announcing *"5 standards found"*.
- Verify 4.5:1 contrast on every token in `styles.css`.
- Visible focus rings — never `outline: none` without a replacement.
- Respect `prefers-reduced-motion`.
- Target **GIGW 3.0** (the Government of India website guidelines) explicitly and
  say so in the pitch. It is a differentiator that costs a day.

### 6.3 Multilingual (required by both PSs)

Cheapest credible path, in order:

1. **UI strings** in Hindi + English via a small `i18n.js` dictionary. No
   library, no CDN — consistent with your no-dependency rule.
2. **Query-side**: pass non-English queries through the LLM for translation
   before embedding. `all-MiniLM-L6-v2` is English-only, so this is required, not
   optional.
3. **Answer-side**: add *"respond in {language}"* to the system prompt. Free.
4. If you want retrieval itself to be multilingual, swap to
   `paraphrase-multilingual-MiniLM-L12-v2` — same architecture, ~470 MB, still
   fully local. Costs index rebuild time and a floor recalibration (§4.2).

Demo just Hindi + English properly. Eight half-working languages is worse than
two solid ones.

### 6.4 The BIS-services knowledge base (SIH26107's other half)

Consumer protection, hallmarking, testing labs and grievances are **not**
standards — they are service content. Don't force them into the standards
corpus; add a **second Chroma collection**, `bis_services`, with the same
record shape and a `topic` field:

- Hallmarking: HUID, purity grades (14K/18K/22K), how to verify a hallmark,
  what a jeweller must display.
- Consumer: how to file a complaint, the BIS Care app, what the ISI mark
  guarantees, spotting a counterfeit mark.
- Labs: BIS-recognised laboratory scheme, how to find a lab for your product.
- Licensing: how to apply, what documents, the broad process shape.

Route in `services/chat.py` by querying both collections and preferring the
higher-scoring one. Roughly 40 hand-written entries covers the bullets, and it
converts four ❌ rows in §0 into ✅ for maybe a day of writing.

Keep every entry sourced and dated, and keep the "verify on the BIS portal"
footnote. Do not state fees or timelines you cannot cite.

### 6.5 Query analytics

`GET /api/analytics/queries` over a small SQLite log: query text, timestamp, top
score, grounded true/false, latency, engine used. Feeds Card A, and gives you
real latency numbers to quote instead of estimates.

Log queries only — **no IP, no user identifier**. Say that on screen. Privacy
hygiene in a government-facing tool is a mark, not an overhead.

---

## 7. Prioritised build order

Ranked by jury impact per hour. Do them in order; stop wherever you run out of
time and you will still have shipped the highest-value items.

### Tier 1 — before anything else (≈2 days)

| # | Item | § | Why first |
|---|---|---|---|
| 1 | **Verify the 51 records; rebalance to ~255 across 17 departments** | 1.3 | Your own README calls this the top risk. Every other feature sits on it, and the current civil-engineering skew is a live demo failure mode. |
| 2 | **Add QCO + certification-scheme fields; split mandatory vs voluntary in the UI** | 3.2, 5B | Highest impact-to-effort in the document. Turns a search result into a compliance obligation. |
| 3 | **Normative-reference graph + one-hop expansion** | 3.3 | The literal ask of SIH26108 that nobody else will build. |
| 4 | **Clickable IS numbers → detail drawer** | 5D | Fixes the biggest UX dead end for a few hours' work. |

### Tier 2 — the dashboard (≈2 days)

| # | Item | § |
|---|---|---|
| 5 | Overview surface: KPIs, coverage-vs-real chart, ICS treemap | 5A |
| 6 | Browse/filter with facet counts, backed by `GET /api/standards` | 5, 8 |
| 7 | Version currency: supersedes / amendments, with the "outdated reference" banner | 3.4 |
| 8 | Certification pathway stepper | 5C |
| 9 | Hybrid ranking + floor recalibration | 4.1, 4.2 |

### Tier 3 — completes the problem statements (≈2 days)

| # | Item | § |
|---|---|---|
| 10 | Tender/spec analyser with completeness score | 5E |
| 11 | BIS services knowledge base (hallmarking, consumer, labs) | 6.4 |
| 12 | Hindi + English multilingual | 6.3 |
| 13 | Export: CSV / PDF / JSON | 6.1 |

### Tier 4 — polish (≈1 day)

| # | Item | § |
|---|---|---|
| 14 | Accessibility pass to GIGW 3.0 | 6.2 |
| 15 | Query analytics + the BIS-facing gap tile | 6.5 |
| 16 | Skeletons, ⌘K palette, recent queries, better empty state | 6.1 |
| 17 | Compare view | 5F |
| 18 | Hosted deployment (Render/Railway) with the local fallback retained | — |

---

## 8. New API surface

```
GET   /api/standards?q=&department=&ics=&status=&year_from=&qco=&page=
        → paginated browse + facet counts               (Card A, B, Browse)
GET   /api/standards/{is_number}
        → full record + resolved graph neighbours       (Card D)
GET   /api/facets
        → department / ICS / status / year counts       (Card A)
GET   /api/coverage
        → indexed vs official BIS totals per department (Card A)
GET   /api/graph/{is_number}?depth=1
        → nodes + edges for the reference graph         (Card D)
POST  /api/recommend          [+ lang, include_graph, include_qco]
POST  /api/analyze-spec       → per-line-item results + completeness score (Card E)
GET   /api/certification/{is_number}
        → scheme, QCO status, conformity route          (Card C)
POST  /api/chat               [+ lang, scope: standards | services | both]
GET   /api/analytics/queries  → top queries, unanswered, latency  (Card A)
```

Two constraints from `CLAUDE.md` that apply to all of them:

- **The `StaticFiles` mount must stay last in `main.py`.** It is mounted at `/`,
  so any router registered after it is shadowed. Every new router goes *above* it.
- Preserve **graceful degradation** in each new service. Anything touching the
  LLM needs a defined non-LLM path, and `used_model` must keep telling the truth.
  It is a genuine differentiator — do not let new features quietly break it.

---

## 9. Revised demo script

Five minutes, ordered so the strongest moment lands first.

1. **Overview (15 s).** "255 standards, all 17 BIS departments, 23,461 in the
   real catalogue — here is exactly what we cover and what we don't."
   *Opening on honest coverage inoculates you against the obvious attack.*
2. **Find → LED bulb factory (90 s).** Ranked standards, then the payoff:
   **"IS 16046 is under a QCO — CRS registration is mandatory."** Click the IS
   number → detail drawer → reference graph. *This is the demo.*
3. **Tender analyser (60 s).** Paste a spec citing IS 1893:2002 → red banner,
   superseded by IS 1893 (Part 1):2016, plus two missing normative references.
   *"This is the procurement dispute the problem statement describes, caught."*
4. **Ask, in Hindi (30 s).** A hallmarking question, answered with citations.
   *Covers multilingual and the BIS-services half of SIH26107 in one move.*
5. **Off-topic refusal (20 s).** Still your best trust moment — keep it.
6. **The BIS-facing tile (30 s).** "Unanswered queries = BIS's
   standards-development gap list, from real demand."
7. **Pull the Wi-Fi (20 s).** Extractive mode, sub-100 ms, pill flips honestly.
   *Close on the engineering.*

---

## 10. Answers to the questions you will be asked

| Question | Answer |
|---|---|
| *"Only 255 of 23,461 — why so few?"* | Every record is verified against the official catalogue. The pipeline is source-agnostic; BIS drops in the full export and it indexes unchanged. We chose verified breadth over unverified volume. |
| *"How do you know it isn't hallucinating?"* | Two calibrated relevance floors, a system prompt that forbids outside knowledge, and citations on every claim. Here is it refusing an off-topic question. |
| *"Copyright on standard texts?"* | We index public catalogue metadata only — number, title, scope summary, classification. No clause text. We point users to BIS to obtain the standard. |
| *"What if the API is down?"* | Pulls the Wi-Fi. Extractive mode, sub-100 ms, and the status pill says so. Embeddings and retrieval never leave the machine. |
| *"How would BIS deploy this?"* | Single FastAPI process, embedded vector store, no external services in the retrieval path. Runs on one VM or on-premise behind the BIS firewall. |
| *"What is different from ChatGPT?"* | ChatGPT will invent an IS number. We refuse, we cite, we flag QCO obligations, and we traverse normative references. Show the refusal. |

---

## 11. Traps to avoid

- **Do not fabricate QCO data.** A wrong "mandatory certification" claim is worse
  than omitting the feature — it is the one error a BIS officer will spot
  instantly and it undermines everything else on screen. Source every QCO flag,
  and show the notification reference in the UI.
- **Do not unify the two relevance floors** without re-measuring both
  distributions (`CLAUDE.md` is explicit, and there is a regression test).
- **Do not add a chart library for one treemap.** Hand-rolled SVG keeps the
  offline-render guarantee and the 64 kB gzipped bundle.
- **Do not let the dashboard outgrow the two features that work.** Search and
  recommend are your proven strengths; every new surface should feed them.
- **Do not demo through the agent router if you can avoid it.** 7–35 s of dead
  air is the worst thing that can happen in a five-minute slot. Use a direct
  Anthropic key with Haiku 4.5, or pre-warm the cache. Keep the env-var shadowing
  gotcha in mind — check `/api/stats` before you present.

---

## Appendix — verification checklist for the corpus

For each record, confirm against the official catalogue:

- [ ] IS number formatting matches BIS style — `IS 1893 (Part 1) : 2016`
- [ ] Year is the current edition, not a superseded one
- [ ] Committee code is a real sectional committee under the right department (§1.2)
- [ ] Status (active / withdrawn / superseded) is current
- [ ] ICS code is valid and matches the subject
- [ ] `supersedes` / `superseded_by` point at real IS numbers
- [ ] QCO flag has a citable notification behind it
- [ ] Scope summary is paraphrased, never copied from the standard text

Track it in a sheet with a `verified_by` / `verified_on` column, and expose
"last verified" in the UI. A jury that sees provenance metadata stops asking
whether you made the data up.
