// A small SVG line chart (0-10 scale) with a hover crosshair and tooltip. No chart library needed.
import { esc } from "./ui.js";

const NS = "http://www.w3.org/2000/svg";
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function node(tag, attrs, parent) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (parent) parent.appendChild(el);
  return el;
}

/**
 * container: element to draw into
 * points: [{ date: Date, label: "Mar 3", values: { pain: 6, mobility: 4 } }]
 * series: [{ key: "pain", name: "Pain", color: "#2a78d6" }]
 */
export function lineChart(container, points, series, { height = 280, yMax = 10, yLabel = "" } = {}) {
  container.classList.add("chart");
  container.innerHTML = `
    <div class="chart-legend">${series.map(s => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}</div>
    <div class="chart-plot"></div>`;
  const plot = container.querySelector(".chart-plot");
  plot.style.position = "relative";

  const draw = () => {
    plot.innerHTML = "";
    const width = Math.max(plot.clientWidth, 280);
    const m = { top: 12, right: 92, bottom: 30, left: 34 };
    const w = width - m.left - m.right, h = height - m.top - m.bottom;
    const svg = node("svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
      "aria-label": `${series.map(s => s.name).join(" and ")} over ${points.length} check-ins` }, plot);

    const t0 = points[0].date.getTime(), t1 = points[points.length - 1].date.getTime();
    const x = d => m.left + (t1 === t0 ? w / 2 : ((d.getTime() - t0) / (t1 - t0)) * w);
    const y = v => m.top + h - (v / yMax) * h;
    const muted = css("--muted"), grid = css("--grid"), surface = css("--surface");

    // grid and y labels (recessive)
    for (let v = 0; v <= yMax; v += 2) {
      node("line", { x1: m.left, x2: m.left + w, y1: y(v), y2: y(v), stroke: grid, "stroke-width": v === 0 ? 1.2 : 1 }, svg);
      const t = node("text", { x: m.left - 8, y: y(v) + 4, "text-anchor": "end", "font-size": 11, fill: muted }, svg);
      t.textContent = v;
    }
    if (yLabel) {
      const t = node("text", { x: m.left - 8, y: m.top - 2, "text-anchor": "end", "font-size": 11, fill: muted }, svg);
      t.textContent = yLabel;
    }

    // x labels: up to 6, evenly spaced through the check-ins
    const step = Math.max(1, Math.ceil(points.length / 6));
    const shown = new Set();
    points.forEach((p, i) => {
      if (i % step && i !== points.length - 1) return;
      const px = Math.round(x(p.date));
      if ([...shown].some(s => Math.abs(s - px) < 48)) return;
      shown.add(px);
      const t = node("text", { x: px, y: height - 8, "text-anchor": "middle", "font-size": 11, fill: muted }, svg);
      t.textContent = p.label;
    });

    // lines and markers
    const ends = [];
    series.forEach(s => {
      const pts = points.filter(p => p.values[s.key] != null);
      if (pts.length > 1) {
        node("path", { d: pts.map((p, i) => `${i ? "L" : "M"}${x(p.date)},${y(p.values[s.key])}`).join(""),
          fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      }
      pts.forEach(p => node("circle", { cx: x(p.date), cy: y(p.values[s.key]), r: 4.5, fill: s.color, stroke: surface, "stroke-width": 2 }, svg));
      const last = pts[pts.length - 1];
      if (last) ends.push({ s, x: x(last.date), y: y(last.values[s.key]), v: last.values[s.key] });
    });

    // direct labels at the end of each line, nudged apart if they'd overlap
    ends.sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 16) ends[i].y = ends[i - 1].y + 16;
    ends.forEach(e => {
      const t = node("text", { x: e.x + 10, y: e.y + 4, "font-size": 12, fill: css("--ink-2"), "font-weight": 600 }, svg);
      t.textContent = `${e.s.name} ${e.v}`;
    });

    // hover layer: crosshair + tooltip for the nearest check-in
    const cross = node("line", { y1: m.top, y2: m.top + h, stroke: muted, "stroke-width": 1, "stroke-dasharray": "3 3", visibility: "hidden" }, svg);
    const tip = document.createElement("div");
    tip.className = "chart-tip";
    tip.hidden = true;
    plot.appendChild(tip);
    const hit = node("rect", { x: m.left - 10, y: 0, width: w + 20, height, fill: "transparent" }, svg);

    const show = clientX => {
      const box = svg.getBoundingClientRect();
      const mx = (clientX - box.left) * (width / box.width);
      let best = 0;
      points.forEach((p, i) => { if (Math.abs(x(p.date) - mx) < Math.abs(x(points[best].date) - mx)) best = i; });
      const p = points[best], px = x(p.date);
      cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("visibility", "visible");
      tip.innerHTML = `<b>${esc(p.tip || p.label)}</b><br>` +
        series.map(s => `<i style="background:${s.color}"></i>${esc(s.name)}: <b>${p.values[s.key]}</b> / ${yMax}`).join("<br>");
      tip.hidden = false;
      const scale = box.width / width;
      const top = Math.min(...series.map(s => y(p.values[s.key] ?? 0)));
      tip.style.left = `${Math.min(Math.max(px * scale, 70), box.width - 70)}px`;
      tip.style.top = `${top * scale - 10}px`;
    };
    const hide = () => { cross.setAttribute("visibility", "hidden"); tip.hidden = true; };
    hit.addEventListener("pointermove", e => show(e.clientX));
    hit.addEventListener("pointerdown", e => show(e.clientX));
    hit.addEventListener("pointerleave", hide);
  };

  draw();
  let frame;
  const ro = new ResizeObserver(() => { cancelAnimationFrame(frame); frame = requestAnimationFrame(draw); });
  ro.observe(plot);
  return () => ro.disconnect();
}
