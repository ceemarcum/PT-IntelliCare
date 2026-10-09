// SVG line chart (0-10 scale) with a hover crosshair and tooltip. No chart library needed.
import { useEffect, useRef, useState } from "react";

// Turn "var(--series-1)" into its actual color (some browsers don't read CSS variables in SVG attributes)
const color = v => v.startsWith("var(")
  ? getComputedStyle(document.documentElement).getPropertyValue(v.slice(4, -1)).trim() : v;

/**
 * points: [{ date: Date, label: "Mar 3", tip: "Mar 3, 9:00 AM", values: { pain: 6, mobility: 4 } }]
 * series: [{ key: "pain", name: "Pain", color: "#2a78d6" }]
 */
export default function LineChart({ points, series, height = 280, yMax = 10 }) {
  const box = useRef(null);
  const [width, setWidth] = useState(640);
  const [hover, setHover] = useState(null);   // index of the point under the pointer

  useEffect(() => {
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(entry.contentRect.width, 280)));
    ro.observe(box.current);
    return () => ro.disconnect();
  }, []);

  const C = { grid: color("var(--grid)"), muted: color("var(--muted)"), surface: color("var(--surface)"),
              "ink-2": color("var(--ink-2)") };
  series = series.map(s => ({ ...s, color: color(s.color) }));

  const m = { top: 12, right: 92, bottom: 30, left: 34 };
  const w = width - m.left - m.right, h = height - m.top - m.bottom;
  const t0 = points[0].date.getTime(), t1 = points[points.length - 1].date.getTime();
  const x = d => m.left + (t1 === t0 ? w / 2 : ((d.getTime() - t0) / (t1 - t0)) * w);
  const y = v => m.top + h - (v / yMax) * h;

  // x labels: up to 6, spread out so they don't overlap
  const step = Math.max(1, Math.ceil(points.length / 6));
  const xLabels = [];
  points.forEach((p, i) => {
    if (i % step && i !== points.length - 1) return;
    const px = Math.round(x(p.date));
    if (xLabels.some(l => Math.abs(l.x - px) < 48)) return;
    xLabels.push({ x: px, text: p.label });
  });

  // direct labels at the end of each line, nudged apart if they'd overlap
  const ends = series.map(s => {
    const last = points[points.length - 1];
    return { s, x: x(last.date), y: y(last.values[s.key]), v: last.values[s.key] };
  }).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 16) ends[i].y = ends[i - 1].y + 16;

  const onMove = e => {
    const rect = e.currentTarget.ownerSVGElement.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (width / rect.width);
    let best = 0;
    points.forEach((p, i) => { if (Math.abs(x(p.date) - mx) < Math.abs(x(points[best].date) - mx)) best = i; });
    setHover(best);
  };

  const hp = hover !== null ? points[hover] : null;
  const tipTop = hp ? Math.min(...series.map(s => y(hp.values[s.key] ?? 0))) - 10 : 0;

  return (
    <div className="chart">
      <div className="chart-legend">
        {series.map(s => <span key={s.key}><i style={{ background: s.color }} />{s.name}</span>)}
      </div>
      <div ref={box} style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${width} ${height}`} role="img"
          aria-label={`${series.map(s => s.name).join(" and ")} over ${points.length} check-ins`}>
          {[0, 2, 4, 6, 8, 10].filter(v => v <= yMax).map(v => (
            <g key={v}>
              <line x1={m.left} x2={m.left + w} y1={y(v)} y2={y(v)} stroke={C["grid"]} strokeWidth={v === 0 ? 1.2 : 1} />
              <text x={m.left - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fill={C["muted"]}>{v}</text>
            </g>
          ))}
          {xLabels.map(l => (
            <text key={l.x} x={l.x} y={height - 8} textAnchor="middle" fontSize="11" fill={C["muted"]}>{l.text}</text>
          ))}
          {series.map(s => (
            <g key={s.key}>
              {points.length > 1 && (
                <path d={points.map((p, i) => `${i ? "L" : "M"}${x(p.date)},${y(p.values[s.key])}`).join("")}
                  fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
              )}
              {points.map((p, i) => (
                <circle key={i} cx={x(p.date)} cy={y(p.values[s.key])} r="4.5" fill={s.color}
                  stroke={C["surface"]} strokeWidth="2" />
              ))}
            </g>
          ))}
          {ends.map(e => (
            <text key={e.s.key} x={e.x + 10} y={e.y + 4} fontSize="12" fill={C["ink-2"]} fontWeight="600">
              {e.s.name} {e.v}
            </text>
          ))}
          {hp && (
            <line x1={x(hp.date)} x2={x(hp.date)} y1={m.top} y2={m.top + h} stroke={C["muted"]} strokeDasharray="3 3" />
          )}
          <rect x={m.left - 10} y="0" width={w + 20} height={height} fill="transparent"
            onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)} />
        </svg>
        {hp && (
          <div className="chart-tip" style={{
            left: `${Math.min(Math.max((x(hp.date) / width) * 100, 12), 88)}%`,
            top: `${(tipTop / height) * 100}%`,
          }}>
            <b>{hp.tip || hp.label}</b>
            {series.map(s => (
              <div key={s.key}><i style={{ background: s.color }} />{s.name}: <b>{hp.values[s.key]}</b> / {yMax}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
