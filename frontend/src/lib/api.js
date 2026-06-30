const baseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const userKey = import.meta.env.VITE_USER_API_KEY || "";
export const adminKey = import.meta.env.VITE_ADMIN_API_KEY || "";
export const defaultProjectId = import.meta.env.VITE_DEFAULT_PROJECT_ID || "";

const friendly = {
  auth_required: "Authentication is required.",
  auth_forbidden: "You do not have permission for this project.",
  insufficient_credits: "This project does not have enough credits. Please top up or use demo mode.",
  quota_exceeded: "This project has reached its quota limit.",
  job_not_found: "This item was not found.",
  project_not_found: "This item was not found.",
};

export async function api(path, { method = "GET", body, projectId, admin = false, idempotencyKey } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (userKey) headers["X-User-API-Key"] = userKey;
  if (admin && adminKey) headers["X-Admin-API-Key"] = adminKey;
  if (projectId) headers["X-Project-ID"] = projectId;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  const response = await fetch(`${baseUrl}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const error = data?.error;
    throw new Error(friendly[error?.code] || error?.message || "Request failed. Please try again.");
  }
  return data;
}

export const backend = {
  me: () => api("/api/me"),
  projects: () => api("/api/projects"),
  createProject: (body) => api("/api/projects", { method: "POST", body }),
  jobs: (id) => api(`/api/projects/${id}/jobs`),
  job: (id) => api(`/api/jobs/${id}`),
  jobAssets: (id) => api(`/api/jobs/${id}/assets`),
  assets: (id) => api(`/api/projects/${id}/assets`),
  billing: (id) => api(`/api/projects/${id}/billing`),
  transactions: (id) => api(`/api/projects/${id}/billing/transactions`),
  usage: (id) => api(`/api/projects/${id}/billing/usage`),
  quotas: (id) => api(`/api/projects/${id}/quotas`),
  topUp: (id, body) => api(`/api/projects/${id}/billing/top-up`, { method: "POST", body, admin: true }),
  createJob: (kind, body, projectId) => api(`/api/jobs/${kind}/generate`, { method: "POST", body, projectId, idempotencyKey: crypto.randomUUID() }),
};
