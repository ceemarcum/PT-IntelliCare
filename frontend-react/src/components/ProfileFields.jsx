// Age and exercise habits: the recovery model and autoencoder need these, and the users table doesn't store them.
import { useState } from "react";
import { profile, EXERCISE_OPTIONS } from "../lib/state.js";
import { Notice } from "./ui.jsx";

// Inline "two quick questions" form, shown when this browser doesn't know them yet
export function ProfilePrompt({ onSave }) {
  const p = profile.get();
  const [age, setAge] = useState(p.age || "");
  const [exercise, setExercise] = useState(p.exercise_frequency || EXERCISE_OPTIONS[2]);
  const [error, setError] = useState("");

  const submit = e => {
    e.preventDefault();
    const n = Number(age);
    if (!(n >= 1 && n <= 120)) { setError("Enter your age."); return; }
    profile.set({ age: n, exercise_frequency: exercise });
    onSave();
  };

  return (
    <>
      <Notice kind="info" title="Two quick questions"><p>The recovery models need your age and how often you exercise.</p></Notice>
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="pp-age">Your age</label>
          <input type="number" id="pp-age" className="input-narrow" min="1" max="120" value={age}
            onChange={e => setAge(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="pp-ex">How often do you exercise?</label>
          <select id="pp-ex" value={exercise} onChange={e => setExercise(e.target.value)}>
            {EXERCISE_OPTIONS.map(o => <option key={o}>{o}</option>)}
          </select>
        </div>
        <div aria-live="assertive">{error && <Notice kind="bad"><p>{error}</p></Notice>}</div>
        <button className="btn btn-primary" type="submit">Continue</button>
      </form>
    </>
  );
}

// Radio cards for the exercise question (used on the injury form)
export function ExerciseOptions({ value, onChange }) {
  return (
    <fieldset>
      <legend>How often do you exercise?</legend>
      <div className="options">
        {EXERCISE_OPTIONS.map(opt => (
          <label className="option" key={opt}>
            <input type="radio" name="exercise" value={opt} checked={value === opt} onChange={() => onChange(opt)} />
            <span>{opt}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
