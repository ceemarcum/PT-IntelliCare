// Formatting helpers shared by the pages.

// Backend timestamps are UTC without a "Z", so add it before converting to local time
export const toDate = ts => new Date(/Z|[+-]\d\d:?\d\d$/.test(ts) ? ts : ts + "Z");
export const fmtDate = ts => toDate(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
export const fmtDay = ts => toDate(ts).toLocaleDateString(undefined, { weekday: "short" });
export const fmtTime = ts => toDate(ts).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
export const fmtIsoDate = iso => iso
  ? new Date(iso + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
  : "Not enough data";
export const daysSince = ts => Math.max(0, Math.floor((Date.now() - toDate(ts)) / 86400000));
export const cap = s => (s || "").charAt(0).toUpperCase() + (s || "").slice(1);

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
