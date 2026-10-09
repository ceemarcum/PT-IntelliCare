// Step 1: injury input form (POST /injury/submit). Also asks for age and exercise habits, which the models need.
import { api } from "../api.js";
import { session, profile, EXERCISE_OPTIONS } from "../state.js";
import { loadStatus } from "../status.js";
import { $, $$, esc, busy, notice, pageHead, guide, slider, wireSlider, loading, fmtDate, painWord } from "../ui.js";

const INJURIES = ["Knee", "Lower back", "Shoulder", "Ankle", "Hip", "Neck", "Wrist", "Elbow"];
const SYMPTOMS = ["Stiffness", "Swelling", "Sharp pain", "Dull ache", "Weakness", "Limited motion", "Numbness or tingling"];

export async function render(main) {
  main.innerHTML = loading();
  const status = await loadStatus();
  const p = profile.get();
  const current = status.injuries[0];

  main.innerHTML = `
    ${pageHead("Step 1 of 5", "Report your injury", "This sets up your plan. You can report a new injury any time.")}
    ${guide(["Pick where it hurts and what it feels like.", "Slide to rate your pain right now.",
             "Tell us your age and how often you exercise, so recovery estimates fit you."])}
    ${current ? notice("info", `Current injury: ${esc(current.injury_type)}`,
      `<p>Reported ${fmtDate(current.date_reported)} with pain ${current.pain_level}/10. Submitting this form adds a new injury and your plan will follow the newest one.</p>`) : ""}
    <div id="injury-result"></div>

    <form class="card" id="injury-form" novalidate>
      <fieldset>
        <legend>Where is your injury?</legend>
        <div class="chips" id="injury-chips">
          ${INJURIES.map((name, i) => `<label class="chip"><input type="radio" name="injury" value="${name.toLowerCase()}" ${i === 0 ? "checked" : ""}><span>${name}</span></label>`).join("")}
          <label class="chip"><input type="radio" name="injury" value="other"><span>Other</span></label>
        </div>
        <div class="field" id="other-field" hidden style="margin:12px 0 0">
          <label for="other-injury">Describe the injury</label>
          <input type="text" id="other-injury" maxlength="60" placeholder="e.g. hamstring">
        </div>
      </fieldset>

      <fieldset>
        <legend>What does it feel like?</legend>
        <span class="hint">Pick all that apply.</span>
        <div class="chips">
          ${SYMPTOMS.map(name => `<label class="chip"><input type="checkbox" name="symptom" value="${name.toLowerCase()}"><span>${name}</span></label>`).join("")}
        </div>
        <div class="field" style="margin:12px 0 0">
          <label for="symptom-notes">Anything else? <span class="muted">(optional)</span></label>
          <input type="text" id="symptom-notes" maxlength="120" placeholder="e.g. hurts more going down stairs">
        </div>
      </fieldset>

      ${slider({ id: "pain", label: "How bad is the pain right now?", value: 5, kind: "pain" })}
      <div id="pain-warning" aria-live="polite"></div>

      <div class="grid-2" style="gap:0 20px">
        <div class="field">
          <label for="age">Your age</label>
          <input type="number" id="age" class="input-narrow" min="1" max="120" inputmode="numeric" value="${esc(p.age || "")}" required>
        </div>
      </div>
      <fieldset>
        <legend>How often do you exercise?</legend>
        <div class="options">
          ${EXERCISE_OPTIONS.map(opt => `<label class="option"><input type="radio" name="exercise" value="${esc(opt)}" ${p.exercise_frequency === opt ? "checked" : ""}><span>${esc(opt)}</span></label>`).join("")}
        </div>
      </fieldset>

      <div id="form-error" aria-live="assertive"></div>
      <div class="actions"><button class="btn btn-primary" type="submit" id="injury-submit">Save injury</button></div>
    </form>`;

  const form = $("#injury-form");
  $$('input[name="injury"]', form).forEach(r => r.addEventListener("change", () => {
    $("#other-field").hidden = form.injury.value !== "other";
  }));

  // Safety note for high pain or numbness (same advice the RAG gives)
  const checkWarning = () => {
    const pain = Number($("#pain").value);
    const numb = $$('input[name="symptom"]:checked', form).some(c => c.value.includes("numbness"));
    $("#pain-warning").innerHTML = pain >= 8 || numb
      ? notice("warn", "Check with a professional", "<p>With pain this high, or numbness or tingling, see a doctor or physical therapist before starting exercises.</p>")
      : "";
  };
  wireSlider(form, "pain", "pain", checkWarning);
  $$('input[name="symptom"]', form).forEach(c => c.addEventListener("change", checkWarning));

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const injuryType = form.injury.value === "other" ? $("#other-injury").value.trim().toLowerCase() : form.injury.value;
    const symptoms = [...$$('input[name="symptom"]:checked', form).map(c => c.value), $("#symptom-notes").value.trim()]
      .filter(Boolean).join(", ");
    const pain = Number($("#pain").value);
    const age = Number($("#age").value);
    const exercise = form.exercise.value;

    const problems = [];
    if (!injuryType) problems.push("Describe your injury.");
    if (!symptoms) problems.push("Pick at least one symptom.");
    if (!(age >= 1 && age <= 120)) problems.push("Enter your age.");
    if (!exercise) problems.push("Choose how often you exercise.");
    if (problems.length) {
      $("#form-error").innerHTML = notice("bad", "Please fix these:", `<ul>${problems.map(x => `<li>${x}</li>`).join("")}</ul>`);
      return;
    }
    $("#form-error").innerHTML = "";

    await busy($("#injury-submit"), "Saving…", async () => {
      try {
        await api.submitInjury(session.userId, injuryType, symptoms, pain);
        profile.set({ age, exercise_frequency: exercise });
        await loadStatus();
        form.hidden = true;
        $("#injury-result").innerHTML = `
          ${notice("good", "Injury saved", `<p>${esc(cap(injuryType))} with ${painWord(pain).toLowerCase()} pain (${pain}/10).</p>`)}
          <div class="card">
            <h2>Next: log your first check-in</h2>
            <p>Check in once a day. After 4 check-ins your plan can start adjusting to your progress.</p>
            <div class="actions">
              <a class="btn btn-primary" href="#/checkin">Go to daily check-in</a>
              <a class="btn btn-ghost" href="#/exercises">See exercises now</a>
            </div>
          </div>`;
        $("#injury-result").scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) {
        $("#form-error").innerHTML = notice("bad", "Couldn't save", `<p>${esc(err.message)}</p>`);
      }
    });
  });
}

const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
