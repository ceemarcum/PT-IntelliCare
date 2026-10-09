// Header, step navigation and the main area that every signed-in page sits in.
import { useEffect, useRef } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useApp, stepsDone } from "../lib/AppContext.jsx";

const NAV = [
  { to: "/home", label: "My plan", num: "⌂" },
  { to: "/injury", label: "Report injury", num: "1" },
  { to: "/checkin", label: "Daily check-in", num: "2" },
  { to: "/exercises", label: "Exercises", num: "3" },
  { to: "/progress", label: "Progress", num: "4" },
  { to: "/insurance", label: "Insurance", num: "5" },
];
const TITLES = Object.fromEntries(NAV.map(n => [n.to, n.label]));

export function Brand() {
  return (
    <NavLink className="brand" to="/home" aria-label="PT IntelliCare home">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
        <rect width="32" height="32" rx="9" fill="currentColor" />
        <path d="M8 20.5c3-1 4.5-6.5 8-6.5s4 4.5 8 3" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
        <circle cx="24" cy="11" r="2.4" fill="#fff" />
      </svg>
      <span>PT IntelliCare</span>
    </NavLink>
  );
}

export default function Layout() {
  const { user, signOut, status } = useApp();
  const done = stepsDone(status);
  const { pathname } = useLocation();
  const main = useRef(null);

  // New page: update the tab title, move focus to the content (for screen readers) and scroll to the top
  useEffect(() => {
    document.title = `${TITLES[pathname] || "PT IntelliCare"} · PT IntelliCare`;
    main.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <>
      <a className="skip-link" href="#main" onClick={e => { e.preventDefault(); main.current?.focus(); }}>Skip to content</a>
      <header className="topbar">
        <Brand />
        <div className="topbar-user">
          <span>{user.full_name || user.email}</span>
          <button className="btn btn-ghost btn-sm" type="button" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <div className="shell">
        <nav className="sidenav" aria-label="Main">
          <ol>
            {NAV.map(n => {
              const isDone = done[n.to.slice(1)];
              return (
                <li key={n.to}>
                  <NavLink to={n.to} className={isDone ? "is-done" : undefined}>
                    <span className="nav-num" aria-hidden="true">{isDone ? "✓" : n.num}</span>{n.label}
                    {isDone && <span className="visually-hidden"> (done)</span>}
                  </NavLink>
                </li>
              );
            })}
          </ol>
        </nav>
        <main id="main" tabIndex="-1" ref={main}>
          <Outlet />
        </main>
      </div>
    </>
  );
}
