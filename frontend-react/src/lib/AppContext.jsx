// App-wide state: who is signed in, what they've done so far (drives the step guidance), and toast messages.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { session as sessionStore } from "./state.js";

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

const EMPTY_STATUS = { injuries: [], history: [], state: {}, claims: [], hasInjury: false, checkins: 0, hasPlan: false };

export function AppProvider({ children }) {
  const [user, setUser] = useState(sessionStore.get());
  const [status, setStatus] = useState(null);       // null = not loaded yet
  const [landing, setLanding] = useState("/home");   // where to go right after signing in
  const [toastText, setToastText] = useState("");
  const toastTimer = useRef();

  // Everything the step guidance needs, loaded in one go
  const refreshStatus = useCallback(async () => {
    const id = sessionStore.userId;
    if (!id) { setStatus(EMPTY_STATUS); return EMPTY_STATUS; }
    const [injuries, history, state, claims] = await Promise.all([
      api.injuries(id).catch(() => []),
      api.history(id).catch(() => []),
      api.engineState(id).catch(() => ({})),
      api.claims(id).catch(() => ({})),
    ]);
    const next = {
      injuries, history, state,
      claims: claims.analytics || [],
      hasInjury: injuries.length > 0,
      checkins: history.length,
      hasPlan: Boolean(state.last_decision),
    };
    setStatus(next);
    return next;
  }, []);

  useEffect(() => { if (user) refreshStatus(); }, [user, refreshStatus]);

  const signIn = (u, goTo = "/home") => { sessionStore.set(u); setStatus(null); setLanding(goTo); setUser(u); };
  const signOut = () => { sessionStore.clear(); setStatus(null); setUser(null); };

  const toast = text => {
    setToastText(text);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastText(""), 3200);
  };

  return (
    <AppContext.Provider value={{ user, landing, signIn, signOut, status, refreshStatus, toast }}>
      {children}
      <div className={`toast${toastText ? " show" : ""}`} role="status" aria-live="polite">{toastText}</div>
    </AppContext.Provider>
  );
}

// Which steps are done (for the nav check marks)
export function stepsDone(s) {
  if (!s) return {};
  return { injury: s.hasInjury, checkin: s.checkins >= 4, exercises: s.hasPlan,
           progress: s.checkins >= 4, insurance: s.claims.length > 0 };
}
