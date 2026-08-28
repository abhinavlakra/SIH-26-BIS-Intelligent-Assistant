/**
 * Backend client.
 *
 * All paths are relative: the Vite dev server proxies /api to FastAPI, and in
 * production FastAPI serves this bundle itself. Override with VITE_API_BASE
 * only if you run the frontend against a remote backend.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  constructor(message, { status = null, reachable = true } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.reachable = reachable;
  }
}

async function request(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Start it with: uvicorn app.main:app --reload",
      { reachable: false },
    );
  }

  if (!response.ok) {
    let detail = `Request failed (HTTP ${response.status})`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
        // FastAPI validation errors arrive as a list.
        detail = payload.detail[0].msg;
      }
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(detail, { status: response.status });
  }

  return response.json();
}

/** IS numbers contain '/' and ':' — encode them so path routing survives. */
const segment = (value) => encodeURIComponent(value).replace(/%2F/gi, "/");

const querystring = (params) => {
  const search = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
};

export const getStats = () => request("/api/stats");
export const getHealth = () => request("/api/health");

export const askQuestion = ({ query, topK, sector, lang }) =>
  request("/api/chat", {
    method: "POST",
    body: { query, top_k: topK ?? null, sector: sector ?? null, lang: lang ?? "en" },
  });

export const recommendStandards = ({ description, topN, lang, includeRelated }) =>
  request("/api/recommend", {
    method: "POST",
    body: {
      description,
      top_n: topN ?? null,
      lang: lang ?? "en",
      include_related: includeRelated ?? true,
    },
  });

export const analyzeSpec = ({ text, maxLines }) =>
  request("/api/analyze-spec", {
    method: "POST",
    body: { text, max_lines: maxLines ?? null },
  });

/**
 * Upload a tender PDF for the same analysis.
 *
 * Sent as multipart rather than JSON, so it bypasses `request()` — that helper
 * always sets a JSON content type, and the browser has to set the multipart
 * boundary itself.
 */
export const analyzeSpecFile = async (file) => {
  const form = new FormData();
  form.append("file", file);

  let response;
  try {
    response = await fetch(`${BASE}/api/analyze-spec/upload`, {
      method: "POST",
      body: form,
    });
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Start it with: uvicorn app.main:app --reload",
      { reachable: false },
    );
  }

  if (!response.ok) {
    let detail = `Upload failed (HTTP ${response.status})`;
    try {
      const payload = await response.json();
      // The server writes 422 messages to be shown verbatim ("no text layer",
      // "password-protected", "not a PDF").
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      /* keep the status-code fallback */
    }
    throw new ApiError(detail, { status: response.status });
  }

  return response.json();
};

// --- catalogue -----------------------------------------------------------

export const browseStandards = (filters) =>
  request(`/api/standards${querystring(filters)}`);

export const getStandard = (isNumber) => request(`/api/standards/${segment(isNumber)}`);

export const getGraph = (isNumber, depth = 1) =>
  request(`/api/graph/${segment(isNumber)}${querystring({ depth })}`);

export const getCertification = (isNumber) =>
  request(`/api/certification/${segment(isNumber)}`);

export const getFacets = () => request("/api/facets");
export const getCoverage = () => request("/api/coverage");
export const getAnalytics = (limit = 8) =>
  request(`/api/analytics/queries${querystring({ limit })}`);
