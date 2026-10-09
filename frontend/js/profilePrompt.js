// Asks for age and exercise habits when this browser doesn't have them yet (e.g. signing in on a new device).
import { profile, EXERCISE_OPTIONS } from "./state.js";
import { esc, notice } from "./ui.js";

export function profilePrompt(container, onSave) {
  const p = profile.get();
  container.innerHTML = `
    ${notice("info", "Two quick questions", "<p>The recovery models need your age and how often you exercise.</p>")}
    <form class="profile-prompt" novalidate>
      <div class="field"><label for="pp-age">Your age</label>
        <input type="number" id="pp-age" class="input-narrow" min="1" max="120" value="${esc(p.age || "")}"></div>
      <div class="field"><label for="pp-ex">How often do you exercise?</label>
        <select id="pp-ex">${EXERCISE_OPTIONS.map(o => `<option ${o === p.exercise_frequency ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></div>
      <div class="pp-error" aria-live="assertive"></div>
      <button class="btn btn-primary" type="submit">Continue</button>
    </form>`;
  container.querySelector("form").addEventListener("submit", e => {
    e.preventDefault();
    const age = Number(container.querySelector("#pp-age").value);
    if (!(age >= 1 && age <= 120)) { container.querySelector(".pp-error").innerHTML = notice("bad", "", "<p>Enter your age.</p>"); return; }
    profile.set({ age, exercise_frequency: container.querySelector("#pp-ex").value });
    onSave();
  });
}
