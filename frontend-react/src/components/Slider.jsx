// A labelled 0-10 slider. kind: "pain" (green to red) or "mobility" (light to blue).
import { painWord, mobilityWord } from "../lib/format.js";

export default function Slider({ id, label, hint, value, onChange, kind }) {
  const word = (kind === "pain" ? painWord : mobilityWord)(value);
  const ends = kind === "pain" ? ["0 No pain", "10 Worst pain"] : ["0 Can't move it", "10 Full movement"];
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {hint && <span className="hint" id={`${id}-hint`}>{hint}</span>}
      <div className="slider-box">
        <div className="slider-top" aria-hidden="true">
          <span className="slider-value">{value}<small> / 10</small></span>
          <span className="slider-word">{word}</span>
        </div>
        <input type="range" id={id} min="0" max="10" step="1" value={value} className={`${kind}-track`}
          onChange={e => onChange(Number(e.target.value))}
          aria-valuetext={`${value} out of 10, ${word}`} aria-describedby={hint ? `${id}-hint` : undefined} />
        <div className="slider-scale" aria-hidden="true"><span>{ends[0]}</span><span>{ends[1]}</span></div>
      </div>
    </div>
  );
}
