// Every call to the FastAPI backend goes through here.
// The frontend is served by the same server (http://127.0.0.1:8000/app), so paths start at the server root.

async function request(method, path, { query, body } = {}) {
  let url = path;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null) params.append(k, v);
    url += "?" + params.toString();
  }
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error("Can't reach the server. Is uvicorn running?");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    let msg = data && data.detail;
    if (Array.isArray(msg)) msg = msg.map(d => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ");   // 422 validation errors
    throw new Error(msg || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  // Auth
  register: (email, full_name, password) => request("POST", "/auth/register", { body: { email, full_name, password } }),
  login: (email, password) => request("POST", "/auth/login", { body: { email, password } }),

  // Injury and daily check-ins
  submitInjury: (userId, injury_type, symptoms, pain_level) =>
    request("POST", "/injury/submit", { query: { injury_type, symptoms, pain_level, user_id: userId } }),
  injuries: userId => request("GET", `/injury/user/${userId}`),
  submitCheckin: (userId, score, mobility, notes) =>
    request("POST", "/pain/submit", { query: { score, mobility, notes: notes || "", user_id: userId } }),
  history: userId => request("GET", `/pain/history/${userId}`),

  // Models
  predictRecovery: (age, pain_severity, exercise_frequency) =>
    request("POST", "/recovery-model/predict", { body: { age, pain_severity, exercise_frequency } }),
  anomalyCheck: (age, pain_severity, exercise_frequency) =>
    request("POST", "/autoencoder/check", { body: { age, pain_severity, exercise_frequency } }),

  // Recommendation engine
  recommend: (userId, age, exercise_frequency, include_guidance) =>
    request("POST", "/engine/recommend", { body: { user_id: userId, age, exercise_frequency, include_guidance } }),
  engineState: userId => request("GET", `/engine/state/${userId}`),
  notifications: userId => request("GET", `/engine/notifications/${userId}`),

  // Insurance analytics
  submitClaim: (userId, injury_type, expected_recovery_weeks) =>
    request("POST", "/insurance/submit-claim", { query: { user_id: userId, injury_type, expected_recovery_weeks } }),
  claims: userId => request("GET", `/insurance/analytics/${userId}`),
  claimReport: (claimId, age, exercise_frequency) =>
    request("GET", `/insurance/claims/${claimId}/report`, { query: { age, exercise_frequency } }),
};
