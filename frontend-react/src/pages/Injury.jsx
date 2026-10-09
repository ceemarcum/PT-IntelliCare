// Step 1: injury input form (POST /injury/submit). Also asks for age and exercise habits, which the models need.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { profile } from "../lib/state.js";
import { useApp } from "../lib/AppContext.jsx";
import { cap, fmtDate, painWord } from "../lib/format.js";
import { BusyButton, Guide, Notice, PageHead } from "../components/ui.jsx";
import Slider from "../components/Slider.jsx";
import { ExerciseOptions } from "../components/ProfileFields.jsx";

const INJURIES = ["Knee", "Lower back", "Shoulder", "Ankle", "Hip", "Neck", "Wrist", "Elbow"];
const SYMPTOMS = ["Stiffness", "Swelling", "Sharp pain", "Dull ache", "Weakness", "Limited motion", "Numbness or tingling"];

export default function Injury() {
  const { user, status, refreshStatus } = useApp();
  const saved = profile.get();
  const [injury, setInjury] = useState("knee");
  const [otherInjury, setOtherInjury] = useState("");
  const [symptoms, setSymptoms] = useState([]);
  const [notes, setNotes] = useState("");
  const [pain, setPain] = useState(5);
  const [age, setAge] = useState(saved.age || "");
  const [exercise, setExercise] = useState(saved.exercise_frequency || "");
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const result = useRef(null);

  useEffect(() => { refreshStatus(); }, [refreshStatus]);
  useEffect(() => { if (done) result.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [done]);

  const current = status?.injuries[0];
  const toggleSymptom = s => setSymptoms(list => list.includes(s) ? list.filter(x => x !== s) : [...list, s]);
  const needsWarning = pain >= 8 || symptoms.some(s => s.includes("numbness"));

  const submit = async e => {
    e.preventDefault();
    const injuryType = injury === "other" ? otherInjury.trim().toLowerCase() : injury;
    const symptomText = [...symptoms, notes.trim()].filter(Boolean).join(", ");
    const ageNum = Number(age);
    const problems = [];
    if (!injuryType) problems.push("Describe your injury.");
    if (!symptomText) problems.push("Pick at least one symptom.");
    if (!(ageNum >= 1 && ageNum <= 120)) problems.push("Enter your age.");
    if (!exercise) problems.push("Choose how often you exercise.");
    setErrors(problems);
    if (problems.length) return;

    setBusy(true);
    try {
      await api.submitInjury(user.user_id, injuryType, symptomText, pain);
      profile.set({ age: ageNum, exercise_frequency: exercise });
      await refreshStatus();
      setDone({ injuryType, pain });
    } catch (err) {
      setErrors([`Couldn't save: ${err.message}`]);
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div ref={result}>
        <PageHead eyebrow="Step 1 of 5" title="Report your injury" />
        <Notice kind="good" title="Injury saved">
          <p>{cap(done.injuryType)} with {painWord(done.pain).toLowerCase()} pain ({done.pain}/10).</p>
        </Notice>
        <div className="card">
          <h2>Next: log your first check-in</h2>
          <p>Check in once a day. After 4 check-ins your plan can start adjusting to your progress.</p>
          <div className="actions">
            <Link className="btn btn-primary" to="/checkin">Go to daily check-in</Link>
            <Link className="btn btn-ghost" to="/exercises">See exercises now</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHead eyebrow="Step 1 of 5" title="Report your injury" lede="This sets up your plan. You can report a new injury any time." />
      <Guide steps={["Pick where it hurts and what it feels like.", "Slide to rate your pain right now.",
                     "Tell us your age and how often you exercise, so recovery estimates fit you."]} />
      {current && (
        <Notice kind="info" title={`Current injury: ${current.injury_type}`}>
          <p>Reported {fmtDate(current.date_reported)} with pain {current.pain_level}/10. Submitting this form adds a new
            injury and your plan will follow the newest one.</p>
        </Notice>
      )}

      <form className="card" onSubmit={submit} noValidate>
        <fieldset>
          <legend>Where is your injury?</legend>
          <div className="chips">
            {[...INJURIES, "Other"].map(name => (
              <label className="chip" key={name}>
                <input type="radio" name="injury" value={name.toLowerCase()} checked={injury === name.toLowerCase()}
                  onChange={() => setInjury(name.toLowerCase())} />
                <span>{name}</span>
              </label>
            ))}
          </div>
          {injury === "other" && (
            <div className="field" style={{ margin: "12px 0 0" }}>
              <label htmlFor="other-injury">Describe the injury</label>
              <input type="text" id="other-injury" maxLength="60" placeholder="e.g. hamstring" value={otherInjury}
                onChange={e => setOtherInjury(e.target.value)} />
            </div>
          )}
        </fieldset>

        <fieldset>
          <legend>What does it feel like?</legend>
          <span className="hint">Pick all that apply.</span>
          <div className="chips">
            {SYMPTOMS.map(name => (
              <label className="chip" key={name}>
                <input type="checkbox" checked={symptoms.includes(name.toLowerCase())}
                  onChange={() => toggleSymptom(name.toLowerCase())} />
                <span>{name}</span>
              </label>
            ))}
          </div>
          <div className="field" style={{ margin: "12px 0 0" }}>
            <label htmlFor="symptom-notes">Anything else? <span className="muted">(optional)</span></label>
            <input type="text" id="symptom-notes" maxLength="120" placeholder="e.g. hurts more going down stairs"
              value={notes} onChange={e => setNotes(e.target.value)} />
          </div>
        </fieldset>

        <Slider id="pain" label="How bad is the pain right now?" value={pain} onChange={setPain} kind="pain" />
        <div aria-live="polite">
          {needsWarning && (
            <Notice kind="warn" title="Check with a professional">
              <p>With pain this high, or numbness or tingling, see a doctor or physical therapist before starting exercises.</p>
            </Notice>
          )}
        </div>

        <div className="field">
          <label htmlFor="age">Your age</label>
          <input type="number" id="age" className="input-narrow" min="1" max="120" inputMode="numeric" value={age}
            onChange={e => setAge(e.target.value)} />
        </div>
        <ExerciseOptions value={exercise} onChange={setExercise} />

        <div aria-live="assertive">
          {errors.length > 0 && (
            <Notice kind="bad" title="Please fix these:"><ul>{errors.map(x => <li key={x}>{x}</li>)}</ul></Notice>
          )}
        </div>
        <div className="actions"><BusyButton busy={busy} busyLabel="Saving…">Save injury</BusyButton></div>
      </form>
    </>
  );
}
