// Step 4: progress dashboard. Read-only: it never changes the exercise level.
import { api } from "../api.js";
import { profile, painToSeverity } from "../state.js";
import { loadStatus } from "../status.js";
import { $, esc, notice, pageHead, loading, fmtDate, fmtTime, toDate, daysSince, painWord, mobilityWord } from "../ui.js";
import { lineChart } from "../chart.js";
import { profilePrompt } from "../profilePrompt.js";

export async function render(main) {
  main.innerHTML = loading();
  const s = await loadStatus();

  if (!s.history.length) {
    main.innerHTML = `${pageHead("Step 4 of 5", "Your progress")}
      <div class="card empty"><p>Your progress shows up after your first check-in.</p>
      <a class="btn btn-primary" href="${s.hasInjury ? "#/checkin" : "#/injury"}">${s.hasInjury ? "Go to step 2: Daily check-in" : "Go to step 1: Report injury"}</a></div>`;
    return;
  }

  const first = s.history[0], latest = s.history[s.history.length - 1];
  const painChange = latest.score - first.score, mobChange = latest.mobility - first.mobility;
  const injury = s.injuries[0];
  const p = profile.get();

  main.innerHTML = `
    ${pageHead("Step 4 of 5", "Your progress", `Since your first check-in on ${fmtDate(first.timestamp)}.`)}

    <div class="tiles">
      ${tile("Pain now", `${latest.score}<small> / 10</small>`, painWord(latest.score), painChange, true)}
      ${tile("Mobility now", `${latest.mobility}<small> / 10</small>`, mobilityWord(latest.mobility), mobChange, false)}
      <div class="tile"><div class="tile-label">Check-ins</div><div class="tile-value">${s.checkins}</div>
        <div class="tile-note">${injury ? `Over ${daysSince(injury.date_reported) + 1} day(s)` : ""}</div></div>
      <div class="tile"><div class="tile-label">Exercise level</div>
        <div class="tile-value" style="font-size:1.4rem;padding:6px 0 3px">${s.hasPlan ? cap(s.state.level) : "Not set"}</div>
        <div class="tile-note"><a href="#/exercises">${s.hasPlan ? "Update plan" : "Get exercises"}</a></div></div>
    </div>

    <section class="card" aria-labelledby="trend-title">
      <div class="card-head"><h2 id="trend-title">Pain and mobility over time</h2>
        <span class="small muted">Lower pain and higher mobility mean you're improving</span></div>
      <div id="trend-chart"></div>
      <details style="margin-top:10px"><summary class="small">Show as a table</summary>
        <div class="table-wrap"><table><thead><tr><th>Date</th><th>Pain</th><th>Mobility</th></tr></thead>
        <tbody>${s.history.map(h => `<tr><td>${fmtDate(h.timestamp)} ${fmtTime(h.timestamp)}</td><td>${h.score}</td><td>${h.mobility}</td></tr>`).join("")}</tbody></table></div>
      </details>
    </section>

    <div class="grid-2">
      <section class="card" aria-labelledby="timeline-title"><h2 id="timeline-title">Recovery timeline</h2><div id="timeline">${loading()}</div></section>
      <section class="card" aria-labelledby="typical-title"><h2 id="typical-title">Is my recovery typical?</h2><div id="typical">${loading()}</div></section>
    </div>`;

  const shortSpan = toDate(latest.timestamp) - toDate(first.timestamp) < 2 * 86400000;
  const points = s.history.map(h => ({
    date: toDate(h.timestamp), label: shortSpan ? fmtTime(h.timestamp) : fmtDate(h.timestamp), tip: `${fmtDate(h.timestamp)}, ${fmtTime(h.timestamp)}`,
    values: { pain: h.score, mobility: h.mobility },
  }));
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const stopChart = lineChart($("#trend-chart"), points,
    [{ key: "pain", name: "Pain", color: css("--series-1") }, { key: "mobility", name: "Mobility", color: css("--series-2") }]);

  // Models: recovery model, Linear Regression (how long) and autoencoder (typical or unusual)
  if (!profile.isComplete()) {
    $("#typical").innerHTML = `<p class="muted">Answer the questions on the left to see this.</p>`;
    profilePrompt($("#timeline"), () => { stopChart(); render(main); });
    return stopChart;
  }
  const severityNow = painToSeverity(latest.score);
  const severityStart = painToSeverity(injury ? injury.pain_level : first.score);

  api.predictRecovery(Number(p.age), severityStart, p.exercise_frequency).then(r => {
    const start = injury ? injury.date_reported : first.timestamp;
    const weeks = Math.max(0, (Date.now() - toDate(start)) / (7 * 86400000));
    const pct = Math.min(weeks / r.predicted_recovery_weeks, 1) * 100;
    const [lo, hi] = r.likely_range_weeks;
    const done = new Date(toDate(start).getTime() + r.predicted_recovery_weeks * 7 * 86400000);
    $("#timeline").innerHTML = `
      <p style="font-size:1.1rem;margin-bottom:10px"><strong>Week ${Math.floor(weeks) + 1}</strong> of about <strong>${Math.round(r.predicted_recovery_weeks)} weeks</strong></p>
      <div class="progress-bar" role="progressbar" aria-label="Recovery timeline" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"><span style="width:${pct}%"></span></div>
      <p class="small muted" style="margin-top:10px">Expected around <strong>${done.toLocaleDateString(undefined, { month: "long", day: "numeric" })}</strong>.
        Most people like you take ${Math.round(lo)} to ${Math.round(hi)} weeks.</p>
      ${weeks > hi ? notice("warn", "Taking longer than expected", "<p>Check in with your physical therapist about your plan.</p>") : ""}
      <p class="small muted">Estimate from the recovery model, based on your starting pain, age and exercise habits.</p>`;
  }).catch(err => { $("#timeline").innerHTML = notice("warn", "Estimate unavailable", `<p>${esc(err.message)}</p>`); });

  api.anomalyCheck(Number(p.age), severityNow, p.exercise_frequency).then(r => {
    $("#typical").innerHTML = r.is_anomaly
      ? notice("warn", "Your profile looks unusual", `<p>${esc(r.message)} Your plan pauses moving up until this settles. Talk with your physical therapist.</p>`)
      : notice("good", "Yes, it looks typical", `<p>${esc(r.message)}</p>`);
    $("#typical").innerHTML += `<p class="small muted">Compares your current pain, age and exercise habits with the survey group.</p>`;
  }).catch(err => { $("#typical").innerHTML = notice("warn", "Check unavailable", `<p>${esc(err.message)}</p>`); });

  return stopChart;
}

function tile(label, value, word, change, lowerIsBetter) {
  let note = word;
  if (change !== 0) {
    const better = lowerIsBetter ? change < 0 : change > 0;
    note += ` · <span class="${better ? "delta-good" : "delta-bad"}">${change > 0 ? "▲" : "▼"} ${Math.abs(change)} since start</span>`;
  }
  return `<div class="tile"><div class="tile-label">${label}</div><div class="tile-value">${value}</div><div class="tile-note">${note}</div></div>`;
}

const cap = s => (s || "").charAt(0).toUpperCase() + (s || "").slice(1);
