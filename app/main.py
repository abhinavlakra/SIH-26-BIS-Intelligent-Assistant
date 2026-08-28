"""ManakMitra API entrypoint.

Development (two processes, hot reload):
    uvicorn app.main:app --reload          # this API on :8000
    cd ../frontend && npm run dev          # UI on :5173, proxies /api here

Demo (one process, one port):
    cd ../frontend && npm run build        # emits frontend/dist
    uvicorn app.main:app                   # serves the UI *and* the API on :8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import catalogue, chat, health, recommend

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

app = FastAPI(
    title="ManakMitra — BIS Standards Assistant",
    description=(
        "AI assistant and recommendation engine for Indian Standards (BIS).\n\n"
        "**SIH 2026 — problem statement SIH26107/108.**\n\n"
        "- `POST /api/chat` — ask a question, get an answer grounded in the "
        "catalogue with IS-number citations.\n"
        "- `POST /api/recommend` — describe a product, get the IS codes that "
        "apply, why, and whether certification is mandatory.\n"
        "- `POST /api/analyze-spec` — check a tender for outdated citations and "
        "missing normative references.\n"
        "- `GET /api/standards` — browse and filter the indexed catalogue.\n"
        "- `GET /api/coverage` — indexed counts against the real BIS totals.\n"
        "- `GET /api/graph/{is_number}` — the reference neighbourhood of a standard.\n"
        "- `GET /api/certification/{is_number}` — which BIS scheme applies.\n\n"
        "Indexes public BIS catalogue *metadata* only (IS number, title, scope "
        "summary, sector). Full standard texts are copyrighted and excluded."
    ),
    version="0.1.0",
)

# The React frontend is a later milestone; permissive during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")
app.include_router(catalogue.router, prefix="/api")


# Serve the built frontend when it exists, so a demo needs a single process.
# Mounted last so it never shadows /api/* or /docs. Falls back to the Swagger
# UI when the frontend has not been built yet.
if (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")
