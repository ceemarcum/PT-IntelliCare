// Sign in / create account. After this, the user_id is remembered so no screen asks for it.
import { api } from "../api.js";
import { session } from "../state.js";
import { $, esc, busy, notice } from "../ui.js";

export async function render(main) {
  main.innerHTML = `
  <div class="auth">
    <div class="auth-intro">
      <h1>Your recovery, one step at a time</h1>
      <p class="lede">Log how you feel each day and get exercises that change as you heal.</p>
    </div>
    <div class="card">
      <div class="tabs" role="tablist" aria-label="Sign in or create account">
        <button role="tab" id="tab-login" aria-selected="true" aria-controls="auth-form">Sign in</button>
        <button role="tab" id="tab-register" aria-selected="false" aria-controls="auth-form">Create account</button>
      </div>
      <div id="auth-error" aria-live="assertive"></div>
      <form id="auth-form" novalidate>
        <div class="field" id="name-field" hidden>
          <label for="full_name">Full name</label>
          <input type="text" id="full_name" autocomplete="name">
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input type="email" id="email" autocomplete="email" required>
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input type="password" id="password" autocomplete="current-password" required minlength="6">
        </div>
        <button class="btn btn-primary" type="submit" id="auth-submit" style="width:100%">Sign in</button>
      </form>
    </div>
  </div>`;

  let mode = "login";
  const setMode = m => {
    mode = m;
    $("#tab-login").setAttribute("aria-selected", m === "login");
    $("#tab-register").setAttribute("aria-selected", m === "register");
    $("#name-field").hidden = m === "login";
    $("#password").autocomplete = m === "login" ? "current-password" : "new-password";
    $("#auth-submit").textContent = m === "login" ? "Sign in" : "Create account";
    $("#auth-error").innerHTML = "";
  };
  $("#tab-login").addEventListener("click", () => setMode("login"));
  $("#tab-register").addEventListener("click", () => setMode("register"));

  $("#auth-form").addEventListener("submit", async e => {
    e.preventDefault();
    const email = $("#email").value.trim(), password = $("#password").value, name = $("#full_name").value.trim();
    const problems = [];
    if (!/^\S+@\S+\.\S+$/.test(email)) problems.push("Enter a valid email.");
    if (password.length < 6) problems.push("Password needs at least 6 characters.");
    if (mode === "register" && !name) problems.push("Enter your name.");
    if (problems.length) { $("#auth-error").innerHTML = notice("bad", "", `<p>${problems.join(" ")}</p>`); return; }

    await busy($("#auth-submit"), mode === "login" ? "Signing in…" : "Creating…", async () => {
      try {
        if (mode === "register") await api.register(email, name, password);
        const res = await api.login(email, password);
        session.set({ user_id: res.user_id, email, full_name: res.full_name || name });
        location.hash = mode === "register" ? "#/injury" : "#/home";
      } catch (err) {
        $("#auth-error").innerHTML = notice("bad", "", `<p>${esc(err.message)}</p>`);
      }
    });
  });
}
