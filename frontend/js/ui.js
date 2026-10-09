// Small helpers shared by the screens.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// Escape anything that came from the user or the server before putting it in HTML
export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

let toastTimer;
export function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

// Backend timestamps are UTC without a "Z", so add it before converting to local time
export const toDate = ts => new Date(/Z|[+-]\d\d:?\d\d$/.test(ts) ? ts : ts + "Z");
export const fmtDate = ts => toDate(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
export const fmtDay = ts => toDate(ts).toLocaleDateString(undefined, { weekday: "short" });
export const fmtTime = ts => toDate(ts).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
export const fmtIsoDate = iso => iso ? new Date(iso + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "Not enough data";
export const daysSince = ts => Math.max(0, Math.floor((Date.now() - toDate(ts)) / 86400000));

const ICONS = { good: "✓", warn: "!", bad: "!", info: "i" };
export function notice(kind, title, body = "") {
  return `<div class="notice notice-${kind}" role="${kind === "bad" ? "alert" : "status"}">
    <span class="notice-icon" aria-hidden="true">${ICONS[kind]}</span>
    <div>${title ? `<p><strong>${title}</strong></p>` : ""}${body}</div></div>`;
}

export function pageHead(eyebrow, title, lede) {
  return `<div class="page-head"><p class="eyebrow">${eyebrow}</p><h1>${title}</h1>${lede ? `<p class="lede">${lede}</p>` : ""}</div>`;
}

export function guide(steps) {
  return `<div class="guide"><span class="guide-icon" aria-hidden="true">?</span><div><strong>How this works</strong>
    <ol>${steps.map(s => `<li>${s}</li>`).join("")}</ol></div></div>`;
}

export const loading = (text = "Loading…") => `<div class="loading"><span class="spinner" aria-hidden="true"></span>${text}</div>`;

// Disable a button and show a spinner while an async task runs
export async function busy(button, label, task) {
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="spinner" aria-hidden="true"></span>${label}`;
  try { return await task(); }
  finally { button.disabled = false; button.innerHTML = original; }
}

// Pain words match the survey's severity answers
export function painWord(score) {
  if (score === 0) return "No pain";
  if (score <= 1) return "Barely there";
  if (score <= 3) return "Mild";
  if (score <= 5) return "Moderate";
  if (score <= 7) return "Severe";
  return "Very severe";
}
export function mobilityWord(score) {
  if (score <= 2) return "Very limited";
  if (score <= 4) return "Limited";
  if (score <= 6) return "Getting there";
  if (score <= 8) return "Good";
  return "Full movement";
}

// A labelled 0-10 slider. kind: "pain" or "mobility"
export function slider({ id, label, hint, value, kind }) {
  const word = kind === "pain" ? painWord : mobilityWord;
  const ends = kind === "pain" ? ["0 No pain", "10 Worst pain"] : ["0 Can't move it", "10 Full movement"];
  return `<div class="field">
    <label for="${id}">${label}</label>${hint ? `<span class="hint" id="${id}-hint">${hint}</span>` : ""}
    <div class="slider-box">
      <div class="slider-top">
        <span class="slider-value" id="${id}-value" aria-hidden="true">${value}<small> / 10</small></span>
        <span class="slider-word" id="${id}-word" aria-hidden="true">${word(value)}</span>
      </div>
      <input type="range" id="${id}" name="${id}" min="0" max="10" step="1" value="${value}" class="${kind}-track"
        aria-valuetext="${value} out of 10, ${word(value)}" ${hint ? `aria-describedby="${id}-hint"` : ""}>
      <div class="slider-scale" aria-hidden="true"><span>${ends[0]}</span><span>${ends[1]}</span></div>
    </div></div>`;
}
export function wireSlider(root, id, kind, onChange) {
  const input = $(`#${id}`, root);
  const word = kind === "pain" ? painWord : mobilityWord;
  input.addEventListener("input", () => {
    const v = Number(input.value);
    $(`#${id}-value`, root).innerHTML = `${v}<small> / 10</small>`;
    $(`#${id}-word`, root).textContent = word(v);
    input.setAttribute("aria-valuetext", `${v} out of 10, ${word(v)}`);
    onChange?.(v);
  });
}

// The RAG answer is plain text with a little markdown (numbered lists, bullets, bold, headings)
export function renderGuidance(text) {
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  let out = "", list = null;
  const close = () => { if (list) { out += `</${list}>`; list = null; } };
  for (const raw of String(text || "").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) { close(); continue; }
    let m;
    if ((m = line.match(/^#{1,6}\s+(.*)/))) { close(); out += `<h4>${inline(m[1])}</h4>`; }
    else if ((m = line.match(/^\d+[.)]\s+(.*)/))) {
      // a numbered line that's only a heading ("1. Start with these exercises:") reads better as a heading
      if (/:\s*\**$/.test(m[1]) && m[1].length < 80) { close(); out += `<h4>${inline(m[1].replace(/:\s*(\*\*)?$/, "$1"))}</h4>`; }
      else { if (list !== "ol") { close(); out += "<ol>"; list = "ol"; } out += `<li>${inline(m[1])}</li>`; }
    }
    else if ((m = line.match(/^[-*•]\s+(.*)/))) { if (list !== "ul") { close(); out += "<ul>"; list = "ul"; } out += `<li>${inline(m[1])}</li>`; }
    else { close(); out += `<p>${inline(line)}</p>`; }
  }
  close();
  return out;
}
