// Step 5: insurance insights dashboard (Step 6 backend: /insurance/...). Shows only the user's own claims.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { profile, painToSeverity } from "../lib/state.js";
import { useApp } from "../lib/AppContext.jsx";
import { fmtIsoDate } from "../lib/format.js";
import { BusyButton, Guide, Loading, NeedsStep, Notice, PageHead, RISK, RiskBadge } from "../components/ui.jsx";
import { ProfilePrompt } from "../components/ProfileFields.jsx";

const STATUS_WORDS = { faster: "Faster than expected", slower: "Slower than expected", on_track: "On track",
                       not_enough_data: "Not enough data yet" };

export default function Insurance() {
  const { user, status: s, refreshStatus } = useApp();
  const [selected, setSelected] = useState(null);
  const [report, setReport] = useState(null);          // { claimId, data | error }
  const [hasProfile, setHasProfile] = useState(profile.isComplete());
  const [injury, setInjury] = useState("");
  const [weeks, setWeeks] = useState(6);
  const [suggested, setSuggested] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reportRef = useRef(null);
  const scrollOnLoad = useRef(false);

  useEffect(() => { refreshStatus(); }, [refreshStatus]);

  const latestInjury = s?.injuries[0];
  const claims = s?.claims || [];

  // Fill the form: the latest injury, and the recovery model's estimate as the expected weeks
  useEffect(() => {
    if (!latestInjury) return;
    setInjury(i => i || latestInjury.injury_type);
    if (!profile.isComplete()) return;
    const p = profile.get();
    api.predictRecovery(Number(p.age), painToSeverity(latestInjury.pain_level), p.exercise_frequency)
      .then(r => { setSuggested(Math.round(r.predicted_recovery_weeks)); setWeeks(Math.round(r.predicted_recovery_weeks)); })
      .catch(() => {});
  }, [latestInjury?.id]);   // eslint-disable-line react-hooks/exhaustive-deps

  // Open the newest claim by default
  useEffect(() => {
    if (selected === null && claims.length) setSelected(claims[claims.length - 1].claim_id);
  }, [claims.length]);   // eslint-disable-line react-hooks/exhaustive-deps

  const loadReport = useCallback(async claimId => {
    setReport({ claimId, loading: true });
    const p = profile.get();
    try {
      setReport({ claimId, data: await api.claimReport(claimId, Number(p.age), p.exercise_frequency) });
    } catch (err) {
      setReport({ claimId, error: err.message });
    }
  }, []);

  useEffect(() => { if (selected !== null && hasProfile) loadReport(selected); }, [selected, hasProfile, loadReport]);
  useEffect(() => {
    if (report?.data && scrollOnLoad.current) {
      reportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      scrollOnLoad.current = false;
    }
  }, [report]);

  if (!s) return <Loading />;

  const head = <PageHead eyebrow="Step 5 of 5 · Optional" title="Insurance insights"
    lede="See how your recovery compares with similar patients after a claim." />;
  if (!s.hasInjury) {
    return <>{head}<NeedsStep text="Report your injury first, then you can file a claim." to="/injury" label="Go to step 1: Report injury" /></>;
  }

  const open = id => { scrollOnLoad.current = true; setSelected(id); if (id === selected && hasProfile) loadReport(id); };

  const submit = async e => {
    e.preventDefault();
    if (!injury.trim() || !(Number(weeks) >= 1)) { setError("Enter the injury and expected weeks."); return; }
    setError(""); setBusy(true);
    try {
      const r = await api.submitClaim(user.user_id, injury.trim(), Number(weeks));
      await refreshStatus();
      open(r.claim_id);
    } catch (err) {
      setError(`Couldn't submit: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {head}
      <Guide steps={["File a claim for your injury (once).", "Keep logging daily check-ins.",
                     "Open your claim to see how you compare, your risk level, and your expected recovery date."]} />

      <div className="grid-2" style={{ alignItems: "start" }}>
        <section className="card" aria-labelledby="claims-title">
          <h2 id="claims-title">Your claims</h2>
          {claims.length ? (
            <div className="claim-list">
              {[...claims].reverse().map(c => (
                <button key={c.claim_id} className="claim-btn" type="button" aria-pressed={c.claim_id === selected}
                  onClick={() => open(c.claim_id)}>
                  <span><strong>Claim #{c.claim_id}</strong> · {c.injury_type}<br />
                    <span className="small muted">Expected {c.expected_recovery_weeks} weeks</span></span>
                  <span aria-hidden="true">›</span>
                </button>
              ))}
            </div>
          ) : <p className="muted">No claims yet.</p>}
        </section>

        <form className="card" onSubmit={submit} noValidate>
          <h2>{claims.length ? "File another claim" : "File a claim"}</h2>
          <div className="field">
            <label htmlFor="claim-injury">Injury</label>
            <input type="text" id="claim-injury" value={injury} onChange={e => setInjury(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="claim-weeks">Expected recovery (weeks)</label>
            <span className="hint" id="weeks-hint">
              The insurer's estimate.{suggested && ` The recovery model suggests about ${suggested} weeks.`}
            </span>
            <input type="number" id="claim-weeks" className="input-narrow" min="1" max="104" value={weeks}
              onChange={e => setWeeks(e.target.value)} aria-describedby="weeks-hint" />
          </div>
          <div aria-live="assertive">{error && <Notice kind="bad"><p>{error}</p></Notice>}</div>
          <div className="actions">
            <BusyButton busy={busy} busyLabel="Submitting…" className={`btn ${claims.length ? "btn-secondary" : "btn-primary"}`}>
              Submit claim
            </BusyButton>
          </div>
        </form>
      </div>

      <div ref={reportRef}>
        {selected !== null && !hasProfile && (
          <div className="card"><ProfilePrompt onSave={() => setHasProfile(true)} /></div>
        )}
        {hasProfile && report?.loading && <div className="card"><Loading text="Analyzing your claim…" /></div>}
        {hasProfile && report?.error && <Notice kind="warn" title="Report not available yet"><p>{report.error}</p></Notice>}
        {hasProfile && report?.data && <ClaimReport r={report.data} />}
      </div>
    </>
  );
}

function ClaimReport({ r }) {
  const [, , label] = RISK[r.risk.risk_level];
  const t = r.predictive_timeline, u = r.pt_utilization, h = r.historical_comparison, rt = r.recovery_tracking;
  const [bust] = useState(() => Date.now());   // fresh chart images for each report
  const status = STATUS_WORDS[rt.status] || rt.status;

  return (
    <>
      <section className="card" aria-labelledby="report-title">
        <div className="card-head">
          <h2 id="report-title">Claim #{r.claim_id}: {r.injury_type}</h2>
          <RiskBadge level={r.risk.risk_level} />
        </div>
        {r.flagged_for_early_intervention && (
          <Notice kind="bad" title="Flagged for early intervention">
            <p>A care manager or physical therapist should follow up on this recovery.</p>
          </Notice>
        )}
        {rt.weekly.length === 0 && (
          <Notice kind="info" title="No check-ins since this claim was filed">
            <p>Tracking starts with check-ins after {fmtIsoDate(t.claim_date)}. <Link to="/checkin">Log a check-in</Link>.</p>
          </Notice>
        )}
        <h3>What this means for you</h3>
        <ul className="insights">{r.insights.map(i => <li key={i}>{i}</li>)}</ul>
      </section>

      <section className="card" aria-labelledby="tl-title">
        <h2 id="tl-title">Predicted recovery timeline</h2>
        <p className="small muted">Claim filed {fmtIsoDate(t.claim_date)} · {t.weeks_since_claim} weeks ago</p>
        <div className="timeline">
          <div>
            <div className="t-label">Insurer's estimate</div>
            <div className="t-date">{fmtIsoDate(t.insurer_expected_date)}</div>
            <div className="t-note">{t.insurer_expected_weeks} weeks</div>
          </div>
          <div>
            <div className="t-label">Recovery model</div>
            <div className="t-date">{fmtIsoDate(t.model_expected_date)}</div>
            <div className="t-note">{t.model_predicted_weeks ? `About ${Math.round(t.model_predicted_weeks)} weeks` : "Unavailable"}</div>
          </div>
          <div>
            <div className="t-label">At your current pace</div>
            <div className="t-date">{fmtIsoDate(t.projected_date_from_your_trend)}</div>
            <div className="t-note">{t.projected_weeks_from_your_trend
              ? `About ${Math.round(t.projected_weeks_from_your_trend)} weeks` : "Needs 2+ weeks of improving check-ins"}</div>
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="cmp-title">
        <div className="card-head">
          <h2 id="cmp-title">Recovery trend vs similar patients</h2>
          <span className="small muted">
            {h.n_patients} similar patients · usually {Math.round(h.p25_weeks)} to {Math.round(h.p75_weeks)} weeks
          </span>
        </div>
        <img className="chart-img" src={`/insurance/claims/${r.claim_id}/chart/recovery-trend.png?t=${bust}`}
          alt={`Line chart of your weekly average pain since the claim compared with the expected pain for similar patients. Your status: ${status}.`} />
        <p className="small muted" style={{ marginTop: 8 }}>
          Status: <strong>{status}</strong>. Pain started at {rt.starting_pain}/10, now {rt.latest_pain}/10.
        </p>
      </section>

      <div className="grid-2">
        <section className="card" aria-labelledby="util-title">
          <h2 id="util-title">Therapy engagement</h2>
          <div className="tiles" style={{ gridTemplateColumns: "repeat(2, 1fr)", marginBottom: 8 }}>
            <div className="tile">
              <div className="tile-label">Check-ins per week</div>
              <div className="tile-value">{u.average_per_week}<small> / {u.target_per_week}</small></div>
            </div>
            <div className="tile">
              <div className="tile-label">Engagement</div>
              <div className="tile-value">{u.engagement_pct}%</div>
            </div>
          </div>
          <p className="small muted">{u.note}</p>
        </section>
        <section className="card" aria-labelledby="risk-title">
          <h2 id="risk-title">Why {label.toLowerCase()}</h2>
          <ul style={{ paddingLeft: "1.1em" }}>{r.risk.reasons.map(x => <li key={x}>{x}</li>)}</ul>
          <p className="small muted">Risk score {r.risk.risk_score}. 0-1 is low, 2-3 medium, 4 or more high.</p>
        </section>
      </div>

      <section className="card" aria-labelledby="util-chart-title" style={{ marginTop: 20 }}>
        <h2 id="util-chart-title">Check-ins per week</h2>
        <img className="chart-img" src={`/insurance/claims/${r.claim_id}/chart/utilization.png?t=${bust}`}
          alt={`Bar chart of check-ins per week: ${u.checkins_per_week.join(", ")}. Target is ${u.target_per_week} per week.`} />
      </section>
    </>
  );
}
