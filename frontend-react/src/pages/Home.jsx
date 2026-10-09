// "My plan": the step-by-step overview, with the next step highlighted.
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../lib/AppContext.jsx";
import { cap, daysSince, painWord } from "../lib/format.js";
import { Loading } from "../components/ui.jsx";

export default function Home() {
  const { user, status: s, refreshStatus } = useApp();
  useEffect(() => { refreshStatus(); }, [refreshStatus]);
  if (!s) return <Loading />;

  const name = (user.full_name || "").split(" ")[0];
  const latest = s.history[s.history.length - 1];
  const injury = s.injuries[0];

  const steps = [
    { n: 1, to: "/injury", title: "Report your injury", done: s.hasInjury,
      text: s.hasInjury ? `${cap(injury.injury_type)}, reported ${daysSince(injury.date_reported)} day(s) ago.`
                        : "Tell us where it hurts and how bad it is. Takes about a minute." },
    { n: 2, to: "/checkin", title: "Log daily check-ins", done: s.checkins >= 4, progress: Math.min(s.checkins / 4, 1),
      text: s.checkins >= 4 ? `${s.checkins} check-ins logged. Keep checking in every day.`
                            : `Rate your pain and movement each day. ${s.checkins} of 4 logged so we can spot a trend.` },
    { n: 3, to: "/exercises", title: "Get your exercises", done: s.hasPlan,
      text: s.hasPlan ? `You're on ${s.state.level} exercises. Update your plan after new check-ins.`
                      : "Get exercises matched to your pain level and progress." },
    { n: 4, to: "/progress", title: "Track your progress", done: s.checkins >= 4,
      text: "See your pain and movement over time and how long recovery should take." },
    { n: 5, to: "/insurance", title: "Insurance insights", done: s.claims.length > 0, optional: true,
      text: s.claims.length ? `${s.claims.length} claim(s) on file. See how your recovery compares.`
                            : "Optional: file a claim and see how your recovery compares with similar patients." },
  ];
  const next = steps.find(st => !st.done && !st.optional) || steps.find(st => !st.done);
  const lastDays = latest && daysSince(latest.timestamp);

  return (
    <>
      <div className="page-head">
        <p className="eyebrow">My plan</p>
        <h1>{name && `Hi ${name}, `}{next ? "here's your next step" : "you're all caught up"}</h1>
        <p className="lede">
          {next ? <>Follow the steps in order. Your next step is <strong>{next.title.toLowerCase()}</strong>.</>
                : "Log today's check-in to keep your plan up to date."}
        </p>
      </div>

      <div className="tiles">
        <div className="tile">
          <div className="tile-label">Latest pain</div>
          <div className="tile-value">{latest ? <>{latest.score}<small> / 10</small></> : "–"}</div>
          <div className="tile-note">{latest ? painWord(latest.score) : "No check-ins yet"}</div>
        </div>
        <div className="tile">
          <div className="tile-label">Exercise level</div>
          <div className="tile-value" style={{ fontSize: "1.4rem", padding: "6px 0 3px" }}>{s.hasPlan ? cap(s.state.level) : "Not set"}</div>
          <div className="tile-note">{s.hasPlan ? "Set by your recommendation engine" : "Set in step 3"}</div>
        </div>
        <div className="tile">
          <div className="tile-label">Check-ins</div>
          <div className="tile-value">{s.checkins}</div>
          <div className="tile-note">{latest ? `Last one ${lastDays === 0 ? "today" : `${lastDays} day(s) ago`}` : "Start in step 2"}</div>
        </div>
      </div>

      <section className="card" aria-labelledby="steps-title">
        <h2 id="steps-title">Your recovery steps</h2>
        <ol className="steps">
          {steps.map(st => {
            const isNext = st === next;
            return (
              <li key={st.n} className={`step${st.done ? " is-done" : ""}${isNext ? " is-next" : ""}`}>
                <span className="step-dot" aria-hidden="true">{st.done ? "✓" : st.n}</span>
                <div>
                  <h3>
                    {st.title}{" "}
                    {st.done ? <span className="badge badge-good step-status">Done</span>
                      : isNext ? <span className="badge badge-brand step-status">Next</span>
                      : st.optional ? <span className="badge badge-neutral step-status">Optional</span> : null}
                  </h3>
                  <p>{st.text}</p>
                  {st.progress !== undefined && !st.done && (
                    <div className="progress-bar" style={{ marginTop: 8, maxWidth: 240 }} role="progressbar"
                      aria-label="Check-ins toward a trend" aria-valuemin="0" aria-valuemax="4" aria-valuenow={s.checkins}>
                      <span style={{ width: `${st.progress * 100}%` }} />
                    </div>
                  )}
                </div>
                <Link className={`btn ${isNext ? "btn-primary" : "btn-ghost"} btn-sm`} to={st.to}>
                  {isNext ? "Start" : st.done ? "Open" : "Go"}
                </Link>
              </li>
            );
          })}
        </ol>
      </section>
    </>
  );
}
