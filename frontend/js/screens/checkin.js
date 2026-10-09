// Step 2: daily check-in with pain and mobility sliders (POST /pain/submit), plus the recovery log.
import { api } from "../api.js";
import { session } from "../state.js";
import { loadStatus } from "../status.js";
import { $, esc, busy, notice, pageHead, guide, slider, wireSlider, loading, fmtDate, fmtDay, fmtTime, toDate,
         painWord, mobilityWord, toast } from "../ui.js";

export async function render(main) {
  main.innerHTML = loading();
  const status = await loadStatus();

  if (!status.hasInjury) {
    main.innerHTML = `${pageHead("Step 2 of 5", "Daily check-in")}
      <div class="card empty"><p>Report your injury first so your check-ins have something to track.</p>
      <a class="btn btn-primary" href="#/injury">Go to step 1: Report injury</a></div>`;
    return;
  }

  const last = status.history[status.history.length - 1];
  const checkedInToday = last && toDate(last.timestamp).toDateString() === new Date().toDateString();

  main.innerHTML = `
    ${pageHead("Step 2 of 5", "Daily check-in", "Takes 30 seconds. Check in once a day, at about the same time.")}
    ${guide(["Slide to rate your pain right now.", "Slide to rate how well you can move the injured area.",
             "Add a note if something changed, then save.", "After 4 check-ins your exercise plan can adjust to your trend."])}

    <div class="grid-2" style="align-items:start">
      <form class="card" id="checkin-form" novalidate>
        <h2>Today's check-in</h2>
        ${checkedInToday ? `<p class="small muted">You already checked in today. Another one is fine if something changed.</p>` : ""}
        ${slider({ id: "score", label: "Pain", hint: "How much does it hurt right now?", value: last ? last.score : 5, kind: "pain" })}
        ${slider({ id: "mobility", label: "Mobility", hint: "How well can you move the injured area?", value: last ? last.mobility : 5, kind: "mobility" })}
        <div class="field">
          <label for="notes">Notes <span class="muted">(optional)</span></label>
          <textarea id="notes" maxlength="300" placeholder="e.g. walked 20 minutes, a little sore after"></textarea>
        </div>
        <div id="checkin-error" aria-live="assertive"></div>
        <div class="actions"><button class="btn btn-primary" type="submit" id="checkin-submit">Save check-in</button></div>
      </form>

      <section class="card" aria-labelledby="log-title">
        <div class="card-head"><h2 id="log-title">Recovery log</h2><span class="muted small" id="log-count"></span></div>
        <div id="trend-box"></div>
        <div id="log"></div>
      </section>
    </div>
    <div id="after-save"></div>`;

  const form = $("#checkin-form");
  wireSlider(form, "score", "pain");
  wireSlider(form, "mobility", "mobility");
  drawLog(status.history);

  form.addEventListener("submit", async e => {
    e.preventDefault();
    await busy($("#checkin-submit"), "Saving…", async () => {
      try {
        await api.submitCheckin(session.userId, Number($("#score").value), Number($("#mobility").value), $("#notes").value.trim());
        $("#notes").value = "";
        $("#checkin-error").innerHTML = "";
        const s = await loadStatus();
        drawLog(s.history);
        toast("Check-in saved");
        $("#after-save").innerHTML = s.checkins >= 4
          ? `<div class="card"><h2>Next: update your exercises</h2>
             <p>You have ${s.checkins} check-ins, enough for your plan to follow your trend.</p>
             <div class="actions"><a class="btn btn-primary" href="#/exercises">Go to step 3: Exercises</a>
             <a class="btn btn-ghost" href="#/progress">See my progress</a></div></div>`
          : `<div class="card"><h2>Nice work</h2><p>${4 - s.checkins} more check-in(s) until your plan can follow your trend. Come back tomorrow.</p>
             <div class="actions"><a class="btn btn-secondary" href="#/exercises">See today's exercises</a></div></div>`;
      } catch (err) {
        $("#checkin-error").innerHTML = notice("bad", "Couldn't save", `<p>${esc(err.message)}</p>`);
      }
    });
  });
}

function drawLog(history) {
  $("#log-count").textContent = `${history.length} check-in${history.length === 1 ? "" : "s"}`;

  // Same rule as trend() in engine/rules.py: last 3 check-ins vs the 3 before them
  const scores = history.map(h => h.score);
  let trend = "";
  if (scores.length >= 4) {
    const recent = scores.slice(-3), earlier = scores.slice(-6, -3);
    const change = avg(recent) - avg(earlier);
    trend = change <= -1 ? notice("good", "Pain is going down", "<p>Your last 3 check-ins are lower than the ones before.</p>")
          : change >= 1 ? notice("warn", "Pain is going up", "<p>Your last 3 check-ins are higher. Your plan may ease off.</p>")
          : notice("info", "Pain is steady", "<p>No big change over your last few check-ins.</p>");
  } else {
    trend = `<p class="small muted">${4 - scores.length} more check-in(s) to see your trend.</p>`;
  }
  $("#trend-box").innerHTML = trend;

  if (!history.length) { $("#log").innerHTML = `<p class="empty">No check-ins yet. Your first one will show up here.</p>`; return; }
  $("#log").innerHTML = `<ul class="log">${[...history].reverse().slice(0, 30).map(h => `
    <li>
      <div class="log-date">${fmtDate(h.timestamp)}<small>${fmtDay(h.timestamp)} ${fmtTime(h.timestamp)}</small></div>
      <div>
        <div class="log-metrics">
          <span class="badge badge-neutral">Pain ${h.score}/10 · ${painWord(h.score)}</span>
          <span class="badge badge-neutral">Mobility ${h.mobility}/10 · ${mobilityWord(h.mobility)}</span>
        </div>
        ${h.notes && h.notes !== "n/a" ? `<p class="log-notes">${esc(h.notes)}</p>` : ""}
      </div>
    </li>`).join("")}</ul>
    ${history.length > 30 ? `<p class="small muted">Showing the latest 30.</p>` : ""}`;
}

const avg = a => a.reduce((x, y) => x + y, 0) / a.length;
