import { session } from "./state.js";
import { api } from "./api.js";
import { $$ } from "./ui.js";

// What the user has done so far: drives the "next step" guidance and the nav check marks
export async function loadStatus() {
  const id = session.userId;
  const [injuries, history, state, claims] = await Promise.all([
    api.injuries(id).catch(() => []),
    api.history(id).catch(() => []),
    api.engineState(id).catch(() => ({})),
    api.claims(id).catch(() => ({})),
  ]);
  const status = {
    injuries, history, state,
    claims: claims.analytics || [],
    hasInjury: injuries.length > 0,
    checkins: history.length,
    hasPlan: Boolean(state.last_decision),
  };
  const done = { injury: status.hasInjury, checkin: status.checkins >= 4, exercises: status.hasPlan,
                 progress: status.checkins >= 4, insurance: status.claims.length > 0 };
  for (const a of $$(".sidenav a")) {
    const isDone = done[a.dataset.route];
    a.classList.toggle("is-done", Boolean(isDone));
    const num = a.querySelector(".nav-num");
    if (a.dataset.route !== "home") num.textContent = isDone ? "✓" : num.dataset.n || (num.dataset.n = num.textContent);
  }
  return status;
}
