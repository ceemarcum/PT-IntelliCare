// Step 5: insurance insights dashboard (Step 6 backend: /insurance/...).
import { api } from "../api.js";
import { session, profile, painToSeverity } from "../state.js";
import { loadStatus } from "../status.js";
import { $, $$, esc, busy, notice, pageHead, guide, loading, fmtIsoDate } from "../ui.js";
import { profilePrompt } from "../profilePrompt.js";

const RISK = { low: ["good", "✓", "Low risk"], medium: ["warn", "!", "Medium risk"], high: ["bad", "!", "High risk"] };

export async function render(main) {
  main.innerHTML = `
    ${pageHead("Step 5 of 5 · Optional", "Insurance insights", "See how your recovery compares with similar patients after a claim.")}
    <div id="ins-panel"></div>`;
  try { await renderMine($("#ins-panel")); }
  catch (err) { $("#ins-panel").innerHTML = notice("bad", "Couldn't load", `<p>${esc(err.message)}</p>`); }
}

// ---------------- patient view ----------------
async function renderMine(panel) {
  const s = await loadStatus();
  const claims = s.claims;
  const p = profile.get();

  if (!s.hasInjury) {
    panel.innerHTML = `<div class="card empty"><p>Report your injury first, then you can file a claim.</p>
      <a class="btn btn-primary" href="#/injury">Go to step 1: Report injury</a></div>`;
    return;
  }

  panel.innerHTML = `
    ${guide(["File a claim for your injury (once).", "Keep logging daily check-ins.",
             "Open your claim to see how you compare, your risk level, and your expected recovery date."])}
    <div class="grid-2" style="align-items:start">
      <section class="card" aria-labelledby="claims-title">
        <h2 id="claims-title">Your claims</h2>
        ${claims.length ? `<div class="claim-list">${claims.slice().reverse().map(c => `
            <button class="claim-btn" type="button" data-claim="${c.claim_id}" aria-pressed="false">
              <span><strong>Claim #${c.claim_id}</strong> · ${esc(c.injury_type)}<br>
              <span class="small muted">Expected ${c.expected_recovery_weeks} weeks</span></span><span aria-hidden="true">›</span>
            </button>`).join("")}</div>`
          : `<p class="muted">No claims yet.</p>`}
      </section>

      <form class="card" id="claim-form" novalidate>
        <h2>${claims.length ? "File another claim" : "File a claim"}</h2>
        <div class="field"><label for="claim-injury">Injury</label>
          <input type="text" id="claim-injury" value="${esc(s.injuries[0].injury_type)}"></div>
        <div class="field"><label for="claim-weeks">Expected recovery (weeks)</label>
          <span class="hint" id="weeks-hint">The insurer's estimate.</span>
          <input type="number" id="claim-weeks" class="input-narrow" min="1" max="104" value="6" aria-describedby="weeks-hint"></div>
        <div id="claim-error" aria-live="assertive"></div>
        <div class="actions"><button class="btn ${claims.length ? "btn-secondary" : "btn-primary"}" type="submit" id="claim-submit">Submit claim</button></div>
      </form>
    </div>
    <div id="report"></div>`;

  // Suggest the recovery model's estimate as the expected weeks
  if (profile.isComplete()) {
    api.predictRecovery(Number(p.age), painToSeverity(s.injuries[0].pain_level), p.exercise_frequency).then(r => {
      $("#claim-weeks").value = Math.round(r.predicted_recovery_weeks);
      $("#weeks-hint").textContent = `The insurer's estimate. The recovery model suggests about ${Math.round(r.predicted_recovery_weeks)} weeks.`;
    }).catch(() => {});
  }

  $("#claim-form").addEventListener("submit", async e => {
    e.preventDefault();
    const injury = $("#claim-injury").value.trim(), weeks = Number($("#claim-weeks").value);
    if (!injury || !(weeks >= 1)) { $("#claim-error").innerHTML = notice("bad", "", "<p>Enter the injury and expected weeks.</p>"); return; }
    await busy($("#claim-submit"), "Submitting…", async () => {
      try {
        const r = await api.submitClaim(session.userId, injury, weeks);
        await renderMine(panel);
        openClaim(panel, r.claim_id);
      } catch (err) { $("#claim-error").innerHTML = notice("bad", "Couldn't submit", `<p>${esc(err.message)}</p>`); }
    });
  });

  $$(".claim-btn", panel).forEach(b => b.addEventListener("click", () => openClaim(panel, Number(b.dataset.claim))));
  if (claims.length) openClaim(panel, claims[claims.length - 1].claim_id, false);
}

async function openClaim(panel, claimId, scroll = true) {
  $$(".claim-btn", panel).forEach(b => b.setAttribute("aria-pressed", Number(b.dataset.claim) === claimId));
  const box = $("#report", panel);
  if (!profile.isComplete()) {
    box.innerHTML = `<div class="card"></div>`;
    profilePrompt(box.firstElementChild, () => openClaim(panel, claimId, scroll));
    return;
  }
  box.innerHTML = `<div class="card">${loading("Analyzing your claim…")}</div>`;
  const p = profile.get();
  try {
    const r = await api.claimReport(claimId, Number(p.age), p.exercise_frequency);
    box.innerHTML = reportHtml(r);
    if (scroll) box.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    box.innerHTML = notice("warn", "Report not available yet", `<p>${esc(err.message)}</p>`);
  }
}

function reportHtml(r) {
  const [kind, icon, label] = RISK[r.risk.risk_level];
  const t = r.predictive_timeline, u = r.pt_utilization, h = r.historical_comparison, rt = r.recovery_tracking;
  const bust = `?t=${Date.now()}`;   // always get a fresh chart
  return `
    <section class="card" aria-labelledby="report-title">
      <div class="card-head">
        <h2 id="report-title">Claim #${r.claim_id}: ${esc(r.injury_type)}</h2>
        <span class="badge badge-${kind}"><span aria-hidden="true">${icon}</span>${label}</span>
      </div>
      ${r.flagged_for_early_intervention ? notice("bad", "Flagged for early intervention",
          "<p>A care manager or physical therapist should follow up on this recovery.</p>") : ""}
      ${rt.weekly.length === 0 ? notice("info", "No check-ins since this claim was filed", `<p>Tracking starts with check-ins after ${fmtIsoDate(t.claim_date)}. <a href="#/checkin">Log a check-in</a>.</p>`) : ""}
      <h3>What this means for you</h3>
      <ul class="insights">${r.insights.map(i => `<li>${esc(i)}</li>`).join("")}</ul>
    </section>

    <section class="card" aria-labelledby="tl-title">
      <h2 id="tl-title">Predicted recovery timeline</h2>
      <p class="small muted">Claim filed ${fmtIsoDate(t.claim_date)} · ${t.weeks_since_claim} weeks ago</p>
      <div class="timeline">
        <div><div class="t-label">Insurer's estimate</div><div class="t-date">${fmtIsoDate(t.insurer_expected_date)}</div>
          <div class="t-note">${t.insurer_expected_weeks} weeks</div></div>
        <div><div class="t-label">Recovery model</div><div class="t-date">${fmtIsoDate(t.model_expected_date)}</div>
          <div class="t-note">${t.model_predicted_weeks ? `About ${Math.round(t.model_predicted_weeks)} weeks` : "Unavailable"}</div></div>
        <div><div class="t-label">At your current pace</div><div class="t-date">${fmtIsoDate(t.projected_date_from_your_trend)}</div>
          <div class="t-note">${t.projected_weeks_from_your_trend ? `About ${Math.round(t.projected_weeks_from_your_trend)} weeks` : "Needs 2+ weeks of improving check-ins"}</div></div>
      </div>
    </section>

    <section class="card" aria-labelledby="cmp-title">
      <div class="card-head"><h2 id="cmp-title">Recovery trend vs similar patients</h2>
        <span class="small muted">${h.n_patients} similar patients · usually ${Math.round(h.p25_weeks)} to ${Math.round(h.p75_weeks)} weeks</span></div>
      <img class="chart-img" src="/insurance/claims/${r.claim_id}/chart/recovery-trend.png${bust}"
        alt="Line chart of your weekly average pain since the claim compared with the expected pain for similar patients. Your status: ${esc(statusWord(rt.status))}.">
      <p class="small muted" style="margin-top:8px">Status: <strong>${statusWord(rt.status)}</strong>. Pain started at ${rt.starting_pain}/10, now ${rt.latest_pain}/10.</p>
    </section>

    <div class="grid-2">
      <section class="card" aria-labelledby="util-title">
        <h2 id="util-title">Therapy engagement</h2>
        <div class="tiles" style="grid-template-columns:repeat(2,1fr);margin-bottom:8px">
          <div class="tile"><div class="tile-label">Check-ins per week</div><div class="tile-value">${u.average_per_week}<small> / ${u.target_per_week}</small></div></div>
          <div class="tile"><div class="tile-label">Engagement</div><div class="tile-value">${u.engagement_pct}%</div></div>
        </div>
        <p class="small muted">${esc(u.note)}</p>
      </section>
      <section class="card" aria-labelledby="risk-title">
        <h2 id="risk-title">Why ${label.toLowerCase()}</h2>
        <ul style="padding-left:1.1em">${r.risk.reasons.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
        <p class="small muted">Risk score ${r.risk.risk_score}. 0-1 is low, 2-3 medium, 4 or more high.</p>
      </section>
    </div>
    <section class="card" aria-labelledby="util-chart-title" style="margin-top:20px">
      <h2 id="util-chart-title">Check-ins per week</h2>
      <img class="chart-img" src="/insurance/claims/${r.claim_id}/chart/utilization.png${bust}"
        alt="Bar chart of check-ins per week: ${u.checkins_per_week.join(", ")}. Target is ${u.target_per_week} per week.">
    </section>
`;
}

const statusWord = s => ({ faster: "Faster than expected", slower: "Slower than expected", on_track: "On track",
                           not_enough_data: "Not enough data yet" }[s] || s);
