// Step 2: daily check-in with pain and mobility sliders (POST /pain/submit), plus the recovery log.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { useApp } from "../lib/AppContext.jsx";
import { fmtDate, fmtDay, fmtTime, mobilityWord, painWord, toDate } from "../lib/format.js";
import { BusyButton, Guide, Loading, NeedsStep, Notice, PageHead } from "../components/ui.jsx";
import Slider from "../components/Slider.jsx";

const avg = a => a.reduce((x, y) => x + y, 0) / a.length;

export default function Checkin() {
  const { user, status, refreshStatus, toast } = useApp();
  const [score, setScore] = useState(null);
  const [mobility, setMobility] = useState(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => { refreshStatus(); }, [refreshStatus]);
  if (!status) return <Loading />;
  if (!status.hasInjury) {
    return <><PageHead eyebrow="Step 2 of 5" title="Daily check-in" />
      <NeedsStep text="Report your injury first so your check-ins have something to track." to="/injury"
        label="Go to step 1: Report injury" /></>;
  }

  const history = status.history;
  const last = history[history.length - 1];
  const painValue = score ?? (last ? last.score : 5);
  const mobilityValue = mobility ?? (last ? last.mobility : 5);
  const checkedInToday = last && toDate(last.timestamp).toDateString() === new Date().toDateString();

  const submit = async e => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.submitCheckin(user.user_id, painValue, mobilityValue, notes.trim());
      setNotes(""); setError(""); setSaved(true);
      await refreshStatus();
      toast("Check-in saved");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead eyebrow="Step 2 of 5" title="Daily check-in" lede="Takes 30 seconds. Check in once a day, at about the same time." />
      <Guide steps={["Slide to rate your pain right now.", "Slide to rate how well you can move the injured area.",
                     "Add a note if something changed, then save.", "After 4 check-ins your exercise plan can adjust to your trend."]} />

      <div className="grid-2" style={{ alignItems: "start" }}>
        <form className="card" onSubmit={submit} noValidate>
          <h2>Today's check-in</h2>
          {checkedInToday && <p className="small muted">You already checked in today. Another one is fine if something changed.</p>}
          <Slider id="score" label="Pain" hint="How much does it hurt right now?" value={painValue} onChange={setScore} kind="pain" />
          <Slider id="mobility" label="Mobility" hint="How well can you move the injured area?" value={mobilityValue}
            onChange={setMobility} kind="mobility" />
          <div className="field">
            <label htmlFor="notes">Notes <span className="muted">(optional)</span></label>
            <textarea id="notes" maxLength="300" placeholder="e.g. walked 20 minutes, a little sore after"
              value={notes} onChange={e => setNotes(e.target.value)} />
          </div>
          <div aria-live="assertive">{error && <Notice kind="bad" title="Couldn't save"><p>{error}</p></Notice>}</div>
          <div className="actions"><BusyButton busy={busy} busyLabel="Saving…">Save check-in</BusyButton></div>
        </form>

        <section className="card" aria-labelledby="log-title">
          <div className="card-head">
            <h2 id="log-title">Recovery log</h2>
            <span className="muted small">{history.length} check-in{history.length === 1 ? "" : "s"}</span>
          </div>
          <Trend scores={history.map(h => h.score)} />
          <RecoveryLog history={history} />
        </section>
      </div>

      {saved && (status.checkins >= 4 ? (
        <div className="card">
          <h2>Next: update your exercises</h2>
          <p>You have {status.checkins} check-ins, enough for your plan to follow your trend.</p>
          <div className="actions">
            <Link className="btn btn-primary" to="/exercises">Go to step 3: Exercises</Link>
            <Link className="btn btn-ghost" to="/progress">See my progress</Link>
          </div>
        </div>
      ) : (
        <div className="card">
          <h2>Nice work</h2>
          <p>{4 - status.checkins} more check-in(s) until your plan can follow your trend. Come back tomorrow.</p>
          <div className="actions"><Link className="btn btn-secondary" to="/exercises">See today's exercises</Link></div>
        </div>
      ))}
    </>
  );
}

// Same rule as trend() in engine/rules.py: last 3 check-ins vs the 3 before them
function Trend({ scores }) {
  if (scores.length < 4) return <p className="small muted">{4 - scores.length} more check-in(s) to see your trend.</p>;
  const change = avg(scores.slice(-3)) - avg(scores.slice(-6, -3));
  if (change <= -1) return <Notice kind="good" title="Pain is going down"><p>Your last 3 check-ins are lower than the ones before.</p></Notice>;
  if (change >= 1) return <Notice kind="warn" title="Pain is going up"><p>Your last 3 check-ins are higher. Your plan may ease off.</p></Notice>;
  return <Notice kind="info" title="Pain is steady"><p>No big change over your last few check-ins.</p></Notice>;
}

function RecoveryLog({ history }) {
  if (!history.length) return <p className="empty">No check-ins yet. Your first one will show up here.</p>;
  return (
    <>
      <ul className="log">
        {[...history].reverse().slice(0, 30).map(h => (
          <li key={h.id}>
            <div className="log-date">{fmtDate(h.timestamp)}<small>{fmtDay(h.timestamp)} {fmtTime(h.timestamp)}</small></div>
            <div>
              <div className="log-metrics">
                <span className="badge badge-neutral">Pain {h.score}/10 · {painWord(h.score)}</span>
                <span className="badge badge-neutral">Mobility {h.mobility}/10 · {mobilityWord(h.mobility)}</span>
              </div>
              {h.notes && h.notes !== "n/a" && <p className="log-notes">{h.notes}</p>}
            </div>
          </li>
        ))}
      </ul>
      {history.length > 30 && <p className="small muted">Showing the latest 30.</p>}
    </>
  );
}
