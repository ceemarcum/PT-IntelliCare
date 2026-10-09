// Step 3: exercise recommendations from the engine (POST /engine/recommend), which combines
// check-in trends, the autoencoder, the recovery model (Linear Regression) and the RAG.
import { api } from "../api.js";
import { session, profile, EXERCISE_OPTIONS } from "../state.js";
import { loadStatus } from "../status.js";
import { $, esc, busy, notice, pageHead, guide, loading, fmtDate, renderGuidance } from "../ui.js";

const LEVELS = ["beginner", "intermediate", "advanced"];
const LEVEL_NOTES = { beginner: "Gentle range of motion", intermediate: "Building strength", advanced: "Full activity" };

export async function render(main) {
  main.innerHTML = loading();
  const status = await loadStatus();

  if (!status.hasInjury) {
    main.innerHTML = `${pageHead("Step 3 of 5", "Your exercises")}
      <div class="card empty"><p>Report your injury first so we know which exercises fit.</p>
      <a class="btn btn-primary" href="#/injury">Go to step 1: Report injury</a></div>`;
    return;
  }

  const level = status.state.level || "beginner";
  const p = profile.get();
  const notes = await api.notifications(session.userId).catch(() => []);

  main.innerHTML = `
    ${pageHead("Step 3 of 5", "Your exercises", "Your plan moves up when pain goes down, and eases off when pain goes up.")}
    ${guide(["Log your check-in first (step 2).", "Press <strong>Update my plan</strong>.",
             "We check your pain trend and models, set your level, and show exercises for it."])}

    <section class="card" aria-labelledby="level-title">
      <div class="card-head"><h2 id="level-title">Your level</h2>
        ${status.state.updated_at ? `<span class="small muted">Updated ${fmtDate(status.state.updated_at)}</span>` : ""}</div>
      <div class="ladder" role="list">
        ${LEVELS.map((l, i) => `<div role="listitem" class="rung ${l === level ? "is-current" : i < LEVELS.indexOf(level) ? "is-past" : ""}"
            ${l === level ? 'aria-current="step"' : ""}>${cap(l)}<small>${LEVEL_NOTES[l]}</small></div>`).join("")}
      </div>
      ${status.checkins < 4 ? `<p class="small muted" style="margin-top:12px">You have ${status.checkins} check-in(s). Your level can change after 4.</p>` : ""}
    </section>

    <form class="card" id="plan-form" novalidate>
      <h2>Update my plan</h2>
      ${profile.isComplete() ? `<p class="small muted">Using age ${esc(p.age)} and "${esc(p.exercise_frequency)}" <a href="#" id="edit-profile">Change</a></p>` : ""}
      <div id="profile-fields" ${profile.isComplete() ? "hidden" : ""}>
        <div class="field"><label for="age">Your age</label>
          <input type="number" id="age" class="input-narrow" min="1" max="120" value="${esc(p.age || "")}"></div>
        <div class="field"><label for="exercise">How often do you exercise?</label>
          <select id="exercise">${EXERCISE_OPTIONS.map(o => `<option ${o === p.exercise_frequency ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></div>
      </div>
      <label class="chip" style="display:inline-block;margin-bottom:14px">
        <input type="checkbox" id="include-guidance" checked><span>Include exercise instructions</span></label>
      <p class="hint">Instructions come from physical therapy guides and take about 10 seconds.</p>
      <div id="plan-error" aria-live="assertive"></div>
      <div class="actions"><button class="btn btn-primary" type="submit" id="plan-submit">Update my plan</button></div>
    </form>

    <div id="plan-result" aria-live="polite"></div>

    <section class="card" aria-labelledby="notes-title">
      <h2 id="notes-title">Plan updates</h2><div id="notes">${notesHtml(notes)}</div>
    </section>`;

  $("#edit-profile")?.addEventListener("click", e => { e.preventDefault(); $("#profile-fields").hidden = false; e.target.parentElement.hidden = true; });

  $("#plan-form").addEventListener("submit", async e => {
    e.preventDefault();
    const age = Number($("#age").value), exercise = $("#exercise").value;
    if (!(age >= 1 && age <= 120)) { $("#plan-error").innerHTML = notice("bad", "", "<p>Enter your age.</p>"); return; }
    profile.set({ age, exercise_frequency: exercise });
    $("#plan-error").innerHTML = "";
    const withGuidance = $("#include-guidance").checked;

    await busy($("#plan-submit"), withGuidance ? "Building your plan…" : "Updating…", async () => {
      try {
        const r = await api.recommend(session.userId, age, exercise, withGuidance);
        $("#plan-result").innerHTML = resultHtml(r);
        $("#plan-result").scrollIntoView({ behavior: "smooth", block: "start" });
        await loadStatus();
        $("#notes").innerHTML = notesHtml(await api.notifications(session.userId).catch(() => []));
        // refresh the ladder without losing the result
        document.querySelectorAll(".rung").forEach((el, i) => {
          el.classList.toggle("is-current", LEVELS[i] === r.level_after);
          el.classList.toggle("is-past", i < LEVELS.indexOf(r.level_after));
          if (LEVELS[i] === r.level_after) el.setAttribute("aria-current", "step"); else el.removeAttribute("aria-current");
        });
      } catch (err) {
        $("#plan-error").innerHTML = notice("bad", "Couldn't update your plan", `<p>${esc(err.message)}</p>`);
      }
    });
  });
}

function resultHtml(r) {
  const head = {
    progress: ["good", `You moved up to ${r.level_after}`],
    regress: ["warn", `Back to ${r.level_after} for now`],
    pause: ["bad", "Progress paused"],
    hold: ["info", `Staying at ${r.level_after}`],
  }[r.decision] || ["info", "Plan updated"];

  const g = r.exercise_guidance;
  return `
    <section class="card" aria-labelledby="result-title">
      <h2 id="result-title" class="visually-hidden">Your updated plan</h2>
      ${notice(head[0], head[1], `<ul style="margin:0;padding-left:1.1em">${(r.reasons || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
        ${r.notification ? `<p style="margin-top:6px">${esc(r.notification)}</p>` : ""}`)}
      <p class="small muted"><a href="#/progress">See your progress and recovery timeline</a></p>
    </section>
    ${g === null ? "" : `
    <section class="card" aria-labelledby="ex-title">
      <div class="card-head"><h2 id="ex-title">Exercises for ${esc(r.level_after)} level</h2>${decisionBadge(r.decision)}</div>
      ${g && g.guidance ? `<div class="guidance">${renderGuidance(g.guidance)}</div>
          ${g.sources?.length ? `<div class="sources"><strong>Sources</strong><ul>${g.sources.map(s =>
            /^https?:/.test(s) ? `<li><a href="${esc(s)}" target="_blank" rel="noopener">${esc(s)}</a></li>` : `<li>${esc(s)}</li>`).join("")}</ul></div>` : ""}`
        : notice("warn", "Exercise instructions unavailable", `<p>${esc(g?.note || "The guidance service didn't respond.")}</p>`)}
      <p class="small muted" style="margin-top:12px">Stop any exercise that causes sharp pain. This isn't medical advice.</p>
    </section>`}`;
}

function notesHtml(notes) {
  return notes.length
    ? `<ul class="log">${notes.slice(0, 8).map(n => `<li><div class="log-date">${fmtDate(n.created_at)}</div>
        <div>${decisionBadge(n.decision)}<p class="log-notes">${esc(n.message)}</p></div></li>`).join("")}</ul>`
    : `<p class="muted">No changes yet. When your level moves up, down or pauses, you'll see why here.</p>`;
}

function decisionBadge(decision) {
  const map = { progress: ["good", "↑ Moved up"], regress: ["warn", "↓ Eased off"], pause: ["bad", "❚❚ Paused"], hold: ["neutral", "→ Holding"] };
  const [kind, label] = map[decision] || ["neutral", esc(decision)];
  return `<span class="badge badge-${kind}">${label}</span>`;
}

const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
