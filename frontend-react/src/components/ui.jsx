// Small building blocks shared by the pages.
import { Link } from "react-router-dom";

const ICONS = { good: "✓", warn: "!", bad: "!", info: "i" };

export function Notice({ kind = "info", title, children }) {
  return (
    <div className={`notice notice-${kind}`} role={kind === "bad" ? "alert" : "status"}>
      <span className="notice-icon" aria-hidden="true">{ICONS[kind]}</span>
      <div>
        {title && <p><strong>{title}</strong></p>}
        {children}
      </div>
    </div>
  );
}

export function PageHead({ eyebrow, title, lede }) {
  return (
    <div className="page-head">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {lede && <p className="lede">{lede}</p>}
    </div>
  );
}

export function Guide({ steps }) {
  return (
    <div className="guide">
      <span className="guide-icon" aria-hidden="true">?</span>
      <div>
        <strong>How this works</strong>
        <ol>{steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
      </div>
    </div>
  );
}

export function Loading({ text = "Loading…" }) {
  return <div className="loading"><span className="spinner" aria-hidden="true" />{text}</div>;
}

// "Do step X first" card
export function NeedsStep({ text, to, label }) {
  return (
    <div className="card empty">
      <p>{text}</p>
      <Link className="btn btn-primary" to={to}>{label}</Link>
    </div>
  );
}

// A submit button that shows a spinner while busy
export function BusyButton({ busy, busyLabel, className = "btn btn-primary", children, ...rest }) {
  return (
    <button className={className} type="submit" disabled={busy} {...rest}>
      {busy ? <><span className="spinner" aria-hidden="true" />{busyLabel}</> : children}
    </button>
  );
}

const DECISIONS = { progress: ["good", "↑ Moved up"], regress: ["warn", "↓ Eased off"], pause: ["bad", "❚❚ Paused"],
                    hold: ["neutral", "→ Holding"] };

export function DecisionBadge({ decision }) {
  const [kind, label] = DECISIONS[decision] || ["neutral", decision];
  return <span className={`badge badge-${kind}`}>{label}</span>;
}

export const RISK = { low: ["good", "✓", "Low risk"], medium: ["warn", "!", "Medium risk"], high: ["bad", "!", "High risk"] };

export function RiskBadge({ level }) {
  const [kind, icon, label] = RISK[level];
  return <span className={`badge badge-${kind}`}><span aria-hidden="true">{icon}</span>{label}</span>;
}
