// Sign in / create account. After this, the user_id is remembered so no screen asks for it.
import { useState } from "react";
import { api } from "../lib/api.js";
import { useApp } from "../lib/AppContext.jsx";
import { Brand } from "../components/Layout.jsx";
import { BusyButton, Notice } from "../components/ui.jsx";

export default function Login() {
  const { signIn } = useApp();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = key => e => setForm({ ...form, [key]: e.target.value });

  const switchMode = m => { setMode(m); setError(""); };

  const submit = async e => {
    e.preventDefault();
    const email = form.email.trim(), name = form.full_name.trim();
    const problems = [];
    if (!/^\S+@\S+\.\S+$/.test(email)) problems.push("Enter a valid email.");
    if (form.password.length < 6) problems.push("Password needs at least 6 characters.");
    if (mode === "register" && !name) problems.push("Enter your name.");
    if (problems.length) { setError(problems.join(" ")); return; }

    setBusy(true);
    try {
      if (mode === "register") await api.register(email, name, form.password);
      const res = await api.login(email, form.password);
      // new accounts start at step 1; the login route then redirects there
      signIn({ user_id: res.user_id, email, full_name: res.full_name || name }, mode === "register" ? "/injury" : "/home");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <header className="topbar"><Brand /></header>
      <main id="main">
        <div className="auth">
          <div className="auth-intro">
            <h1>Your recovery, one step at a time</h1>
            <p className="lede">Log how you feel each day and get exercises that change as you heal.</p>
          </div>
          <div className="card">
            <div className="tabs" role="tablist" aria-label="Sign in or create account">
              <button role="tab" type="button" aria-selected={mode === "login"} onClick={() => switchMode("login")}>Sign in</button>
              <button role="tab" type="button" aria-selected={mode === "register"} onClick={() => switchMode("register")}>Create account</button>
            </div>
            <div aria-live="assertive">{error && <Notice kind="bad"><p>{error}</p></Notice>}</div>
            <form onSubmit={submit} noValidate>
              {mode === "register" && (
                <div className="field">
                  <label htmlFor="full_name">Full name</label>
                  <input type="text" id="full_name" autoComplete="name" value={form.full_name} onChange={set("full_name")} />
                </div>
              )}
              <div className="field">
                <label htmlFor="email">Email</label>
                <input type="email" id="email" autoComplete="email" value={form.email} onChange={set("email")} />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input type="password" id="password" value={form.password} onChange={set("password")}
                  autoComplete={mode === "login" ? "current-password" : "new-password"} />
              </div>
              <BusyButton busy={busy} busyLabel={mode === "login" ? "Signing in…" : "Creating…"} style={{ width: "100%" }}>
                {mode === "login" ? "Sign in" : "Create account"}
              </BusyButton>
            </form>
          </div>
        </div>
      </main>
    </>
  );
}
