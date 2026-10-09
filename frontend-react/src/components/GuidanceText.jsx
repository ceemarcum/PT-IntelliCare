// Shows the RAG answer, which is plain text with a little markdown (numbered lists, bullets, bold, headings).
// Built as React elements (no innerHTML), so nothing in the answer can run as code.

function inline(text, keyBase) {
  return text.split(/(\*\*.+?\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={`${keyBase}-${i}`}>{part.slice(2, -2)}</strong>
      : part);
}

export default function GuidanceText({ text }) {
  const blocks = [];
  let list = null;
  const close = () => { if (list) { blocks.push(list); list = null; } };

  String(text || "").split(/\r?\n/).forEach((raw, n) => {
    const line = raw.trim();
    let m;
    if (!line) { close(); return; }
    if ((m = line.match(/^#{1,6}\s+(.*)/))) { close(); blocks.push({ type: "h4", text: m[1], key: n }); return; }
    if ((m = line.match(/^\d+[.)]\s+(.*)/))) {
      // a numbered line that's only a heading ("1. Start with these exercises:") reads better as a heading
      if (/:\s*\**$/.test(m[1]) && m[1].length < 80) {
        close(); blocks.push({ type: "h4", text: m[1].replace(/:\s*(\*\*)?$/, "$1"), key: n }); return;
      }
      if (!list || list.type !== "ol") { close(); list = { type: "ol", items: [], key: n }; }
      list.items.push(m[1]); return;
    }
    if ((m = line.match(/^[-*•]\s+(.*)/))) {
      if (!list || list.type !== "ul") { close(); list = { type: "ul", items: [], key: n }; }
      list.items.push(m[1]); return;
    }
    close(); blocks.push({ type: "p", text: line, key: n });
  });
  close();

  return (
    <div className="guidance">
      {blocks.map(b => {
        if (b.type === "ol" || b.type === "ul") {
          const List = b.type;
          return <List key={b.key}>{b.items.map((it, i) => <li key={i}>{inline(it, `${b.key}-${i}`)}</li>)}</List>;
        }
        const Tag = b.type;
        return <Tag key={b.key}>{inline(b.text, b.key)}</Tag>;
      })}
    </div>
  );
}
