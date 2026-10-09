// Step 3: exercise recommendations from the engine (POST /engine/recommend), which combines
// check-in trends, the autoencoder, the recovery model (Linear Regression) and the RAG.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { profile, EXERCISE_OPTIONS } from "../lib/state.js";
import { useApp } from "../lib/AppContext.jsx";
import { cap, fmtDate } from "../lib/format.js";
import { BusyButton, DecisionBadge, Guide, Loading, NeedsStep, Notice, PageHead } from "../components/ui.jsx";
import GuidanceText from "../components/GuidanceText.jsx";

const LEVELS = ["beginner", "intermediate", "advanced"];
const LEVEL_NOTES = { beginner: "Gentle range of motion", intermediate: "Building strength", advanced: "Full activity" };

export default function Exercises() {
  const { user, status, refreshStatus } = useApp();
  const saved = profile.get();
  const [notes, setNotes] = useState([]);
  const [age, setAge] = useState(saved.age || "");
  const [exercise, setExercise] = useState(saved.exercise_frequency || EXERCISE_OPTIONS[2]);
  const [editProfile, setEditProfile] = useState(!profile.isComplete());
  const [withGuidance, setWithGuidance] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const resultRef = useRef(null);

  const loadNotes = useCallback(() => api.notifications(user.user_id).then(setNotes).catch(() => {}), [user.user_id]);
  useEffect(() => { refreshStatus(); loadNotes(); }, [refreshStatus, loadNotes]);
  useEffect(() => { if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [result]);

  if (!status) return <Loading />;
  if (!status.hasInjury) {
    return <><PageHead eyebrow="Step 3 of 5" title="Your exercises" />
      <NeedsStep text="Report your injury first so we know which exercises fit." to="/injury" label="Go to step 1: Report injury" /></>;
  }

  const level = result?.level_after || status.state.level || "beginner";

  const submit = async e => {
    e.preventDefault();
    const ageNum = Number(age);
    if (!(ageNum >= 1 && ageNum <= 120)) { setError("Enter your age."); setEditProfile(true); return; }
    profile.set({ age: ageNum, exercise_frequency: exercise });
    setError(""); setBusy(true);
    try {
      setResult(await api.recommend(user.user_id, ageNum, exercise, withGuidance));
      await Promise.all([refreshStatus(), loadNotes()]);
    } catch (err) {
      setError(`Couldn't update your plan: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead eyebrow="Step 3 of 5" title="Your exercises"
        lede="Your plan moves up when pain goes down, and eases off when pain goes up." />
      <Guide steps={["Log your check-in first (step 2).", <>Press <strong>Update my plan</strong>.</>,
                     "We check your pain trend and models, set your level, and show exercises for it."]} />

      <section className="card" aria-labelledby="level-title">
        <div className="card-head">
          <h2 id="level-title">Your level</h2>
          {status.state.updated_at && <span className="small muted">Updated {fmtDate(status.state.updated_at)}</span>}
        </div>
        <div className="ladder" role="list">
          {LEVELS.map((l, i) => (
            <div key={l} role="listitem" aria-current={l === level ? "step" : undefined}
              className={`rung${l === level ? " is-current" : i < LEVELS.indexOf(level) ? " is-past" : ""}`}>
              {cap(l)}<small>{LEVEL_NOTES[l]}</small>
            </div>
          ))}
        </div>
        {status.checkins < 4 && (
          <p className="small muted" style={{ marginTop: 12 }}>You have {status.checkins} check-in(s). Your level can change after 4.</p>
        )}
      </section>

      <form className="card" onSubmit={submit} noValidate>
        <h2>Update my plan</h2>
        {editProfile ? (
          <>
            <div className="field">
              <label htmlFor="age">Your age</label>
              <input type="number" id="age" className="input-narrow" min="1" max="120" value={age} onChange={e => setAge(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="exercise">How often do you exercise?</label>
              <select id="exercise" value={exercise} onChange={e => setExercise(e.target.value)}>
                {EXERCISE_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          </>
        ) : (
          <p className="small muted">
            Using age {age} and "{exercise}"{" "}
            <button type="button" className="link-button" onClick={() => setEditProfile(true)}>Change</button>
          </p>
        )}
        <label className="chip" style={{ display: "inline-block", marginBottom: 14 }}>
          <input type="checkbox" checked={withGuidance} onChange={e => setWithGuidance(e.target.checked)} />
          <span>Include exercise instructions</span>
        </label>
        <p className="hint">Instructions come from physical therapy guides and take about 10 seconds.</p>
        <div aria-live="assertive">{error && <Notice kind="bad"><p>{error}</p></Notice>}</div>
        <div className="actions">
          <BusyButton busy={busy} busyLabel={withGuidance ? "Building your plan…" : "Updating…"}>Update my plan</BusyButton>
        </div>
      </form>

      <div ref={resultRef} aria-live="polite">{result && <PlanResult r={result} />}</div>

      <section className="card" aria-labelledby="notes-title">
        <h2 id="notes-title">Plan updates</h2>
        {notes.length ? (
          <ul className="log">
            {notes.slice(0, 8).map(n => (
              <li key={n.id}>
                <div className="log-date">{fmtDate(n.created_at)}</div>
                <div><DecisionBadge decision={n.decision} /><p className="log-notes">{n.message}</p></div>
              </li>
            ))}
          </ul>
        ) : <p className="muted">No changes yet. When your level moves up, down or pauses, you'll see why here.</p>}
      </section>
    </>
  );
}

const HEADLINES = {
  progress: r => ["good", `You moved up to ${r.level_after}`],
  regress: r => ["warn", `Back to ${r.level_after} for now`],
  pause: () => ["bad", "Progress paused"],
  hold: r => ["info", `Staying at ${r.level_after}`],
};

function PlanResult({ r }) {
  const [kind, title] = (HEADLINES[r.decision] || (() => ["info", "Plan updated"]))(r);
  const g = r.exercise_guidance;
  return (
    <>
      <section className="card" aria-labelledby="result-title">
        <h2 id="result-title" className="visually-hidden">Your updated plan</h2>
        <Notice kind={kind} title={title}>
          <ul style={{ margin: 0, paddingLeft: "1.1em" }}>{(r.reasons || []).map(x => <li key={x}>{x}</li>)}</ul>
          {r.notification && <p style={{ marginTop: 6 }}>{r.notification}</p>}
        </Notice>
        <p className="small muted"><Link to="/progress">See your progress and recovery timeline</Link></p>
      </section>

      {g !== null && (
        <section className="card" aria-labelledby="ex-title">
          <div className="card-head">
            <h2 id="ex-title">Exercises for {r.level_after} level</h2>
            <DecisionBadge decision={r.decision} />
          </div>
          {g?.guidance ? (
            <>
              <GuidanceText text={g.guidance} />
              {g.sources?.length > 0 && (
                <div className="sources">
                  <strong>Sources</strong>
                  <ul>{g.sources.map(s => <li key={s}>{/^https?:/.test(s)
                    ? <a href={s} target="_blank" rel="noopener noreferrer">{s}</a> : s}</li>)}</ul>
                </div>
              )}
            </>
          ) : (
            <Notice kind="warn" title="Exercise instructions unavailable">
              <p>{g?.note || "The guidance service didn't respond."}</p>
            </Notice>
          )}
          <p className="small muted" style={{ marginTop: 12 }}>Stop any exercise that causes sharp pain. This isn't medical advice.</p>
        </section>
      )}
    </>
  );
}
