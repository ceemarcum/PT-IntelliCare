// "My plan": the step-by-step overview, with the next step highlighted.
import { session } from "../state.js";
import { loadStatus } from "../status.js";
import { esc, loading, painWord, daysSince } from "../ui.js";

export async function render(main) {
  main.innerHTML = loading();
  const s = await loadStatus();
  const name = (session.get().full_name || "").split(" ")[0];
  const latest = s.history[s.history.length - 1];
  const injury = s.injuries[0];

  const steps = [
    { n: 1, route: "injury", title: "Report your injury", done: s.hasInjury,
      text: s.hasInjury ? `${esc(cap(injury.injury_type))}, reported ${daysSince(injury.date_reported)} day(s) ago.`
                        : "Tell us where it hurts and how bad it is. Takes about a minute." },
    { n: 2, route: "checkin", title: "Log daily check-ins", done: s.checkins >= 4,
      text: s.checkins >= 4 ? `${s.checkins} check-ins logged. Keep checking in every day.`
                            : `Rate your pain and movement each day. ${s.checkins} of 4 logged so we can spot a trend.`,
      progress: Math.min(s.checkins / 4, 1) },
    { n: 3, route: "exercises", title: "Get your exercises", done: s.hasPlan,
      text: s.hasPlan ? `You're on ${s.state.level} exercises. Update your plan after new check-ins.`
                      : "Get exercises matched to your pain level and progress." },
    { n: 4, route: "progress", title: "Track your progress", done: s.checkins >= 4,
      text: "See your pain and movement over time and how long recovery should take." },
    { n: 5, route: "insurance", title: "Insurance insights", done: s.claims.length > 0, optional: true,
      text: s.claims.length ? `${s.claims.length} claim(s) on file. See how your recovery compares.`
                            : "Optional: file a claim and see how your recovery compares with similar patients." },
  ];
  const next = steps.find(st => !st.done && !st.optional) || steps.find(st => !st.done);

  main.innerHTML = `
    <div class="page-head">
      <p class="eyebrow">My plan</p>
      <h1>${name ? `Hi ${esc(name)}, ` : ""}${next ? "here's your next step" : "you're all caught up"}</h1>
      <p class="lede">${next ? `Follow the steps in order. Your next step is <strong>${next.title.toLowerCase()}</strong>.`
                             : "Log today's check-in to keep your plan up to date."}</p>
    </div>

    <div class="tiles">
      <div class="tile"><div class="tile-label">Latest pain</div>
        <div class="tile-value">${latest ? `${latest.score}<small> / 10</small>` : "–"}</div>
        <div class="tile-note">${latest ? painWord(latest.score) : "No check-ins yet"}</div></div>
      <div class="tile"><div class="tile-label">Exercise level</div>
        <div class="tile-value" style="font-size:1.4rem;padding:6px 0 3px">${s.hasPlan ? cap(s.state.level) : "Not set"}</div>
        <div class="tile-note">${s.hasPlan ? "Set by your recommendation engine" : "Set in step 3"}</div></div>
      <div class="tile"><div class="tile-label">Check-ins</div>
        <div class="tile-value">${s.checkins}</div>
        <div class="tile-note">${latest ? `Last one ${daysSince(latest.timestamp) === 0 ? "today" : daysSince(latest.timestamp) + " day(s) ago"}` : "Start in step 2"}</div></div>
    </div>

    <section class="card" aria-labelledby="steps-title">
      <h2 id="steps-title">Your recovery steps</h2>
      <ol class="steps">
        ${steps.map(st => {
          const isNext = st === next;
          return `<li class="step ${st.done ? "is-done" : ""} ${isNext ? "is-next" : ""}">
            <span class="step-dot" aria-hidden="true">${st.done ? "✓" : st.n}</span>
            <div>
              <h3>${st.title}
                ${st.done ? `<span class="badge badge-good step-status">Done</span>` : isNext ? `<span class="badge badge-brand step-status">Next</span>` : st.optional ? `<span class="badge badge-neutral step-status">Optional</span>` : ""}</h3>
              <p>${st.text}</p>
              ${st.progress !== undefined && !st.done ? `<div class="progress-bar" style="margin-top:8px;max-width:240px" role="progressbar" aria-label="Check-ins toward a trend" aria-valuemin="0" aria-valuemax="4" aria-valuenow="${s.checkins}"><span style="width:${st.progress * 100}%"></span></div>` : ""}
            </div>
            <a class="btn ${isNext ? "btn-primary" : "btn-ghost"} btn-sm" href="#/${st.route}">${isNext ? "Start" : st.done ? "Open" : "Go"}</a>
          </li>`;
        }).join("")}
      </ol>
    </section>`;
}

const cap = s => (s || "").charAt(0).toUpperCase() + (s || "").slice(1);
