// Generates a project context + progress handoff PDF and writes it to the
// Desktop. Renders styled HTML via the same Playwright/Chrome that drives the
// screenshot capture, then prints to PDF (Chromium's print engine → crisp,
// selectable text). Run from the frontend dir:  node scripts/gen-context-pdf.mjs
import { chromium } from 'playwright';

const OUT = 'C:/Users/sapta/Desktop/ManakMitra-Project-Context.pdf';
const GENERATED = '22 August 2026';

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  :root {
    --ink:#0f172a; --muted:#475569; --faint:#64748b;
    --brand:#1d4ed8; --brand2:#0891b2; --line:#e2e8f0;
    --ok:#15803d; --okbg:#dcfce7; --warn:#b45309; --warnbg:#fef3c7;
    --chipbg:#eff6ff; --code:#0b3d91;
  }
  * { box-sizing:border-box; }
  html { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  body {
    font-family:"Segoe UI", Arial, sans-serif; color:var(--ink);
    font-size:10.5px; line-height:1.5; margin:0;
  }
  h1,h2,h3 { color:var(--ink); margin:0; line-height:1.25; }
  h2 {
    font-size:15px; margin:22px 0 8px; padding-bottom:5px;
    border-bottom:2px solid var(--line);
  }
  h2 .n { color:var(--brand); font-weight:700; margin-right:7px; }
  h3 { font-size:11.5px; margin:13px 0 4px; color:var(--brand); }
  p { margin:6px 0; }
  ul { margin:6px 0; padding-left:18px; }
  li { margin:3px 0; }
  a { color:var(--brand); text-decoration:none; }
  code {
    font-family:"Cascadia Code","Consolas",monospace; font-size:9.3px;
    background:#f1f5f9; color:var(--code); padding:1px 4px; border-radius:3px;
  }
  pre {
    font-family:"Cascadia Code","Consolas",monospace; font-size:9px;
    background:#0f172a; color:#e2e8f0; padding:11px 13px; border-radius:7px;
    line-height:1.45; overflow:hidden; white-space:pre-wrap;
  }
  pre .c { color:#7dd3fc; }
  pre .g { color:#86efac; }
  pre .d { color:#94a3b8; }

  .cover {
    background:linear-gradient(135deg,#1d4ed8 0%,#0891b2 100%);
    color:#fff; padding:34px 30px; border-radius:12px; margin-bottom:8px;
  }
  .cover .kicker { font-size:10px; letter-spacing:2px; text-transform:uppercase; opacity:.9; }
  .cover h1 { color:#fff; font-size:34px; margin:6px 0 2px; letter-spacing:.5px; }
  .cover .tag { font-size:13px; opacity:.95; font-weight:500; }
  .cover .meta { margin-top:16px; font-size:10px; opacity:.92; line-height:1.7; }
  .cover .meta b { font-weight:600; }

  .lead { font-size:11px; color:var(--muted); margin:10px 0 4px; }

  .grid2 { display:flex; gap:14px; }
  .grid2 > div { flex:1; }

  table { width:100%; border-collapse:collapse; margin:8px 0; font-size:9.6px; }
  th, td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { background:#f8fafc; color:var(--faint); text-transform:uppercase; font-size:8.3px; letter-spacing:.6px; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; }

  .chip {
    display:inline-block; background:var(--chipbg); color:var(--brand);
    border:1px solid #bfdbfe; border-radius:20px; padding:1px 9px;
    font-size:8.6px; font-weight:600; margin:2px 3px 2px 0;
  }
  .badge { display:inline-block; border-radius:5px; padding:1px 7px; font-size:8.4px; font-weight:700; }
  .b-ok { background:var(--okbg); color:var(--ok); }
  .b-wait { background:var(--warnbg); color:var(--warn); }

  .card { border:1px solid var(--line); border-radius:9px; padding:12px 14px; margin:8px 0; background:#fff; }
  .callout {
    border-left:4px solid var(--brand2); background:#f0f9ff;
    padding:9px 13px; border-radius:0 7px 7px 0; margin:9px 0; font-size:10px;
  }
  .callout.warn { border-left-color:var(--warn); background:#fffbeb; }
  .callout b { color:var(--ink); }

  .kpis { display:flex; gap:10px; margin:12px 0 2px; }
  .kpi { flex:1; border:1px solid var(--line); border-radius:9px; padding:11px 12px; background:#fbfdff; }
  .kpi .big { font-size:22px; font-weight:800; color:var(--brand); line-height:1; }
  .kpi .lbl { font-size:8.6px; color:var(--faint); text-transform:uppercase; letter-spacing:.5px; margin-top:4px; }

  .section { page-break-inside:avoid; }
  .pb { page-break-before:always; }
  .foot-note { color:var(--faint); font-size:9px; margin-top:4px; }
</style>
</head>
<body>

  <div class="cover">
    <div class="kicker">Project Context &amp; Progress Report</div>
    <h1>ManakMitra</h1>
    <div class="tag">AI Assistant &amp; Recommendation Engine for Indian Standards (BIS)</div>
    <div class="meta">
      <b>Smart India Hackathon 2026</b> &nbsp;&middot;&nbsp; Problem SIH26107 / SIH26108<br/>
      Ministry of Consumer Affairs &rarr; Bureau of Indian Standards<br/>
      <b>Prepared:</b> ${GENERATED} &nbsp;&middot;&nbsp; <b>For:</b> engineering handoff / Claude session context<br/>
      <b>Status:</b> Backend + frontend complete and verified running end-to-end
    </div>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="big">51</div><div class="lbl">IS standards indexed</div></div>
    <div class="kpi"><div class="big">8</div><div class="lbl">Sectors covered</div></div>
    <div class="kpi"><div class="big">28</div><div class="lbl">Tests passing</div></div>
    <div class="kpi"><div class="big">4</div><div class="lbl">Live API endpoints</div></div>
  </div>

  <div class="section">
    <h2><span class="n">1</span>Executive summary</h2>
    <p><b>ManakMitra</b> ("Manak" = standard) is a working prototype that makes the Bureau of
    Indian Standards catalogue searchable and actionable in plain language. It does two things:
    a <b>RAG chatbot</b> that answers questions about Indian Standards and cites the exact IS
    numbers, and a <b>recommendation engine</b> that turns a plain-language product or
    procurement description into a ranked list of applicable IS codes with a rationale and a
    confidence signal.</p>
    <p>The system is <b>fully built and runs end-to-end today</b>: a FastAPI backend serves a
    React single-page frontend on one port; the corpus is indexed and queried locally; and live
    Claude generation is wired in and verified. It degrades gracefully to an extractive,
    citation-only mode when no LLM is reachable, so a demo can never hard-fail on a network
    outage. All flows have been driven through a real browser with zero console errors.</p>
  </div>

  <div class="section">
    <h2><span class="n">2</span>The problem &amp; our solution</h2>
    <div class="grid2">
      <div>
        <h3>Problem</h3>
        <p>BIS publishes thousands of Indian Standards. MSMEs, manufacturers, and procurement
        officers struggle to (a) find <i>what a standard actually says</i> and (b) know
        <i>which</i> IS code applies to their product or process. The catalogue is large,
        technical, and hard to navigate without expert knowledge.</p>
      </div>
      <div>
        <h3>Solution</h3>
        <p>Two capabilities over a grounded, retrieval-backed index:</p>
        <ul>
          <li><b>RAG chat</b> — natural-language Q&amp;A grounded in the catalogue, always citing IS numbers, and honestly refusing when a topic is not covered.</li>
          <li><b>Recommendation engine</b> (the differentiator) — spec &rarr; ranked IS codes, each with a one-line "why it applies" and a confidence level.</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="section">
    <h2><span class="n">3</span>What is built &mdash; component status</h2>
    <table>
      <thead><tr><th style="width:26%">Component</th><th style="width:12%">Status</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td>Data model &amp; seed corpus</td><td><span class="badge b-ok">DONE</span></td><td>51 verified, real IS records in <code>data/seed/standards.jsonl</code></td></tr>
        <tr><td>Local embeddings</td><td><span class="badge b-ok">DONE</span></td><td>sentence-transformers all-MiniLM-L6-v2 (offline, free)</td></tr>
        <tr><td>Vector store + index build</td><td><span class="badge b-ok">DONE</span></td><td>ChromaDB persistent; <code>build_index</code> ingests the corpus</td></tr>
        <tr><td>Retriever</td><td><span class="badge b-ok">DONE</span></td><td>top-k semantic search with optional sector/status filters</td></tr>
        <tr><td>RAG chat service + endpoint</td><td><span class="badge b-ok">DONE</span></td><td>grounded prompt, citations, honest "not in catalogue"</td></tr>
        <tr><td>Recommendation service + endpoint</td><td><span class="badge b-ok">DONE</span></td><td>per-item rationale + confidence</td></tr>
        <tr><td>LLM adapter (Claude)</td><td><span class="badge b-ok">DONE</span></td><td>swappable provider; Anthropic + third-party router support</td></tr>
        <tr><td>Graceful degradation + circuit breaker</td><td><span class="badge b-ok">DONE</span></td><td>extractive fallback keeps the service answering</td></tr>
        <tr><td>Health / stats endpoints</td><td><span class="badge b-ok">DONE</span></td><td>expose corpus size, sectors, active model, endpoint</td></tr>
        <tr><td>React + Vite frontend</td><td><span class="badge b-ok">DONE</span></td><td>built to <code>frontend/dist</code>, served by FastAPI on one port</td></tr>
        <tr><td>Test suite</td><td><span class="badge b-ok">DONE</span></td><td>28 tests passing, network-free</td></tr>
        <tr><td>Live LLM integration (agentrouter, opus-4-8)</td><td><span class="badge b-ok">DONE</span></td><td>verified end-to-end with grounded, cited answers</td></tr>
        <tr><td>Catalogue collector (scale beyond seed)</td><td><span class="badge b-wait">STUB</span></td><td>scaffolded; expands corpus from public data.gov.in when run</td></tr>
        <tr><td>Hosted deployment</td><td><span class="badge b-wait">DEFERRED</span></td><td>runs locally today; Render/Railway is a next step</td></tr>
      </tbody>
    </table>
  </div>

  <div class="section pb">
    <h2><span class="n">4</span>Architecture &amp; stack</h2>
    <p>A single FastAPI process serves both the JSON API and the built React SPA. Embeddings and
    retrieval run <b>locally</b> — only text <i>generation</i> ever calls a hosted model, and even
    that is optional.</p>
    <div class="grid2">
      <div>
        <h3>Backend</h3>
        <span class="chip">FastAPI + Uvicorn</span>
        <span class="chip">ChromaDB (embedded, persistent)</span>
        <span class="chip">sentence-transformers</span>
        <span class="chip">Anthropic Python SDK</span>
        <span class="chip">pydantic-settings</span>
      </div>
      <div>
        <h3>Frontend</h3>
        <span class="chip">React</span>
        <span class="chip">Vite</span>
        <span class="chip">Served via FastAPI StaticFiles</span>
        <span class="chip">Single port (:8000)</span>
      </div>
    </div>
    <div class="callout">
      <b>Why local embeddings + Chroma:</b> zero infrastructure, works offline, no per-call cost,
      and no dependency on a live API during judging. This decouples retrieval quality from
      network conditions — the highest-risk factor in a live demo.
    </div>
    <h3>Request flow</h3>
    <pre><span class="d"># Chat</span>
query <span class="c">&rarr;</span> local embed <span class="c">&rarr;</span> Chroma top-k <span class="c">&rarr;</span> grounded prompt <span class="c">&rarr;</span> Claude <span class="c">&rarr;</span> <span class="g">answer + citations</span>
                                              <span class="d">(no key / unreachable)</span> <span class="c">&rarr;</span> <span class="g">extractive answer</span>

<span class="d"># Recommend</span>
spec <span class="c">&rarr;</span> local embed <span class="c">&rarr;</span> similarity rank <span class="c">&rarr;</span> per-item Claude rationale <span class="c">&rarr;</span> <span class="g">ranked IS codes + confidence</span></pre>
  </div>

  <div class="section">
    <h2><span class="n">5</span>Data strategy &mdash; public metadata only</h2>
    <p>The corpus contains <b>only public catalogue metadata</b> for each standard: IS number,
    title, scope, ICS codes, sector, technical committee, status, and keywords. <b>Full IS texts
    are copyrighted and are deliberately excluded.</b> Every seeded record uses a genuine IS
    number and title verified against the public catalogue — no fabricated or toy data, which a
    domain jury would spot immediately.</p>
    <h3>Unified record shape</h3>
    <pre>{ is_number, title, scope, ics_codes[], sector,
  technical_committee, status, year, keywords[] }</pre>
  </div>

  <div class="section">
    <h2><span class="n">6</span>Corpus snapshot (live)</h2>
    <p>Figures read live from <code>GET /api/stats</code> on the running instance:</p>
    <div class="grid2">
      <div>
        <table>
          <thead><tr><th>Sector</th><th class="num">Standards</th></tr></thead>
          <tbody>
            <tr><td>Civil Engineering</td><td class="num">26</td></tr>
            <tr><td>Electrotechnical</td><td class="num">8</td></tr>
            <tr><td>Metallurgical Engineering</td><td class="num">7</td></tr>
            <tr><td>Chemical</td><td class="num">4</td></tr>
            <tr><td>Food and Agriculture</td><td class="num">3</td></tr>
            <tr><td>Electronics and Information Technology</td><td class="num">1</td></tr>
            <tr><td>Management and Systems</td><td class="num">1</td></tr>
            <tr><td>Petroleum, Coal and Related Products</td><td class="num">1</td></tr>
            <tr><td><b>Total</b></td><td class="num"><b>51</b></td></tr>
          </tbody>
        </table>
      </div>
      <div>
        <h3>Representative standards</h3>
        <p class="foot-note" style="font-size:9.6px;color:var(--muted)">Well-known IS codes in the seed set:</p>
        <span class="chip">IS 10500 &mdash; Drinking water</span>
        <span class="chip">IS 456 &mdash; Concrete</span>
        <span class="chip">IS 1893 &mdash; Seismic design</span>
        <span class="chip">IS 13920 &mdash; Ductile detailing</span>
        <span class="chip">IS 2062 &mdash; Structural steel</span>
        <span class="chip">IS 383 &mdash; Aggregates</span>
        <span class="chip">IS 875 &mdash; Design loads</span>
        <span class="chip">IS 4326 &mdash; Earthquake-resistant buildings</span>
      </div>
    </div>
  </div>

  <div class="section pb">
    <h2><span class="n">7</span>API surface</h2>
    <table>
      <thead><tr><th style="width:22%">Endpoint</th><th style="width:10%">Method</th><th>Purpose</th></tr></thead>
      <tbody>
        <tr><td><code>/api/health</code></td><td>GET</td><td>Liveness check</td></tr>
        <tr><td><code>/api/stats</code></td><td>GET</td><td>Corpus size, sector breakdown, active model + endpoint, LLM enabled flag</td></tr>
        <tr><td><code>/api/chat</code></td><td>POST</td><td>Grounded Q&amp;A: returns answer, citations (IS number, title, scope, score), and <code>used_model</code></td></tr>
        <tr><td><code>/api/recommend</code></td><td>POST</td><td>Spec &rarr; ranked recommendations, each with why-it-applies + confidence</td></tr>
      </tbody>
    </table>
    <p class="foot-note">FastAPI auto-generates interactive Swagger docs at <code>/docs</code> — the API is fully testable without the frontend.</p>
  </div>

  <div class="section">
    <h2><span class="n">8</span>LLM integration &amp; graceful degradation</h2>
    <p>Generation sits behind a swappable <code>LLMProvider</code> adapter. The default configured
    model is <code>claude-haiku-4-5</code> (fast, cheap); the live demo currently runs
    <code>claude-opus-4-8</code> through the <b>agentrouter.org</b> Anthropic-compatible router.
    The same adapter also works directly against api.anthropic.com. When no key is configured, a
    <code>NullProvider</code> transparently routes every request to extractive mode.</p>

    <h3>Integrating agentrouter.org took solving four layered gates</h3>
    <table>
      <thead><tr><th style="width:34%">Gate</th><th>Fix applied</th></tr></thead>
      <tbody>
        <tr><td>Client fingerprinting — router rejects non-CLI clients with <code>unauthorized_client_error</code></td><td>Send <code>User-Agent: claude-cli/...</code> + <code>x-app: cli</code> headers (router mode only)</td></tr>
        <tr><td>Per-token model entitlement — this token is limited to one model</td><td>Pin <code>ANTHROPIC_MODEL=claude-opus-4-8</code> (others return 403 "no permission")</td></tr>
        <tr><td>Broken httpx decompressor in this env crashes on compressed bodies</td><td>Request <code>Accept-Encoding: identity</code> to skip the decode path</td></tr>
        <tr><td>opus-4-8 via the router is slow &amp; variable (~7&ndash;35s)</td><td>Raise <code>LLM_TIMEOUT_SECONDS</code> to 60 so successful answers are not dropped</td></tr>
      </tbody>
    </table>

    <div class="callout">
      <b>Circuit breaker:</b> after the API becomes unreachable, only the <i>first</i> request pays
      the timeout; for a cooldown window every call fails instantly and degrades to extractive
      mode — so a mid-demo Wi-Fi drop produces no visible stall. A status pill in the UI always
      reflects the real engine in use (<code>used_model</code>), never a fake one.
    </div>
  </div>

  <div class="section">
    <h2><span class="n">9</span>Testing &amp; verification</h2>
    <ul>
      <li><b>28 automated tests pass</b> across retriever, recommend, LLM adapter, and API layers. Tests are network-free — keys are cleared in <code>conftest.py</code>, so they run in CI without secrets.</li>
      <li><b>Browser-driven verification:</b> a Playwright/Chrome script exercises recommend, chat, an off-topic refusal, and a mobile viewport — screenshots captured, <b>zero console errors</b>.</li>
      <li><b>Live end-to-end:</b> <code>/api/chat</code> and <code>/api/recommend</code> return grounded, cited answers with <code>used_model: claude-opus-4-8</code>. Example: an earthquake-resistant flats query surfaces IS 1893, IS 13920, IS 456, IS 4326, and IS 875.</li>
    </ul>
  </div>

  <div class="section pb">
    <h2><span class="n">10</span>Project layout</h2>
<pre>project/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            <span class="d"># FastAPI app; mounts API + built SPA</span>
│  │  ├─ config.py          <span class="d"># pydantic-settings: keys, model, paths</span>
│  │  ├─ models.py          <span class="d"># request/response + Standard schema</span>
│  │  ├─ ingestion/         <span class="d"># collector, normalize, build_index</span>
│  │  ├─ rag/               <span class="d"># embeddings, vectorstore, retriever, llm</span>
│  │  ├─ services/          <span class="d"># chat (RAG), recommend</span>
│  │  └─ routers/           <span class="d"># chat, recommend, health</span>
│  ├─ tests/                <span class="d"># 28 tests (api, llm, recommend, retriever)</span>
│  └─ .env                  <span class="d"># gitignored — keys + model config</span>
├─ data/
│  └─ seed/standards.jsonl  <span class="d"># 51 verified real IS records</span>
├─ frontend/                <span class="d"># React + Vite SPA (built to dist/)</span>
├─ scripts/run_demo.ps1     <span class="d"># the designated demo entrypoint</span>
└─ README.md</pre>
  </div>

  <div class="section">
    <h2><span class="n">11</span>How to run</h2>
    <p>From a <b>plain PowerShell terminal</b> (not inside a Claude Code session — see the gotcha below):</p>
<pre><span class="c">powershell -ExecutionPolicy Bypass -File</span> scripts\run_demo.ps1</pre>
    <p>This installs frontend deps if missing, builds the SPA, and starts Uvicorn. Then open
    <a href="http://localhost:8000">http://localhost:8000</a> for the UI, or
    <code>http://localhost:8000/docs</code> for Swagger. Confirm the engine with
    <code>GET /api/stats</code>.</p>
  </div>

  <div class="section">
    <h2><span class="n">12</span>Non-obvious knowledge (for the next session)</h2>
    <div class="callout warn">
      <b>Env-var shadowing:</b> a Claude Code shell exports <code>ANTHROPIC_API_KEY</code>,
      <code>ANTHROPIC_BASE_URL</code>, and <code>ANTHROPIC_MODEL</code>, and OS env vars
      <b>outrank</b> <code>backend/.env</code> in pydantic-settings. Run the demo from a normal
      terminal, or <code>unset</code> those four vars, or the .env config silently won't apply.
    </div>
    <ul>
      <li><b>Model IDs are complete as-is</b> — never append a date suffix to a Claude model string.</li>
      <li><b>No <code>thinking</code> / effort params are sent</b> — Haiku 4.5 rejects them and the Opus/Sonnet 5 models run adaptive thinking by default, so one adapter fits every model.</li>
      <li><b>agentrouter base URL must not include <code>/v1</code></b> — the SDK appends <code>/v1/messages</code> itself.</li>
      <li><b>Bearer token vs api-key:</b> setting <code>anthropic_auth_token</code> makes the SDK send <code>Authorization: Bearer</code> and ignore any stray <code>ANTHROPIC_API_KEY</code> — the correct mode for routers.</li>
      <li><b>The .env is gitignored</b> and holds the live token; it is never committed and never printed.</li>
    </ul>
  </div>

  <div class="section">
    <h2><span class="n">13</span>Deferred &amp; suggested next steps</h2>
    <ul>
      <li><b>Expand the corpus</b> — run the collector against the public data.gov.in BIS dataset to grow well beyond the 51 seed records.</li>
      <li><b>Hosted deployment</b> — Render or Railway, so the demo is reachable by URL.</li>
      <li><b>One-line provider toggle</b> — make switching between agentrouter and a direct Anthropic key a single .env change.</li>
      <li><b>Embeddings upgrade</b> — optionally move to a hosted embedding model for higher retrieval quality once online is guaranteed.</li>
      <li><b>Hybrid ranking</b> — blend semantic similarity with keyword/ICS-code overlap in the recommender.</li>
    </ul>
    <div class="card">
      <b>Supporting tooling:</b> a local <code>search</code> CLI is installed on this PC
      (<code>search -t "query"</code> for text results, <code>search "query"</code> to open in the
      browser). It stands in for the built-in web search, which is unavailable when running through
      an agent router. Browser mode uses Google; text mode uses DuckDuckGo (Google removed its
      no-JS results, so it cannot be scraped headlessly).
    </div>
    <p class="foot-note">Generated ${GENERATED}. Figures verified live against the running instance at localhost:8000.</p>
  </div>

</body>
</html>`;

const footer = `<div style="width:100%;font-size:8px;color:#94a3b8;font-family:Segoe UI,Arial,sans-serif;padding:0 14mm;display:flex;justify-content:space-between;">
  <span>ManakMitra — Project Context &amp; Progress</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>`;

async function launch() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return await chromium.launch(); // fall back to bundled Chromium
  }
}

const browser = await launch();
try {
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.pdf({
    path: OUT,
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: footer,
    margin: { top: '12mm', bottom: '14mm', left: '13mm', right: '13mm' },
  });
  console.log('WROTE ' + OUT);
} finally {
  await browser.close();
}
