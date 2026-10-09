// Who is signed in, plus their age and exercise answer (the models need these; the users table doesn't store them).
// Kept in the browser's localStorage, so the user never has to type their user_id.
// React components read the session through AppContext; this file only handles storage.

const SESSION_KEY = "rehab.session";
const profileKey = userId => `rehab.profile.${userId}`;

function read(key) {
  try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
}
function write(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode: works for this visit only */ }
}

let memorySession = read(SESSION_KEY);

export const session = {
  get: () => memorySession,
  set(user) { memorySession = user; write(SESSION_KEY, user); },
  clear() { memorySession = null; try { localStorage.removeItem(SESSION_KEY); } catch { /* ignore */ } },
  get userId() { return memorySession?.user_id; },
};

export const profile = {
  get: () => read(profileKey(session.userId)) || {},
  set: data => write(profileKey(session.userId), { ...profile.get(), ...data }),
  isComplete() { const p = profile.get(); return Boolean(p.age && p.exercise_frequency); },
};

// Same answers as the Pain Data survey (and the backend's Literal types)
export const EXERCISE_OPTIONS = [
  "I never exercise regularly.",
  "I do not exercise at all.",
  "I exercise sometimes.",
  "I exercise most of the time.",
  "I always exercise.",
];

// Same cut-offs as pain_to_severity() in engine/rules.py
export function painToSeverity(score) {
  if (score <= 1) return "Not severe at all";
  if (score <= 3) return "Mild";
  if (score <= 5) return "Moderate";
  if (score <= 7) return "Severe";
  return "Very severe";
}
