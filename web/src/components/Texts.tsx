import type { EventTexts } from "../types";
import { fmtDate } from "../format";

export function ContextBlock({ t }: { t: EventTexts | undefined }) {
  return (
    <section className="panel-section">
      <h3>Context</h3>
      {t?.context ? <p>{t.context.text}</p> : <p className="muted">Context coming soon.</p>}
      {t?.headlines?.length ? (
        <ul className="headlines">
          {t.headlines.map((h) => (
            <li key={h.url}>
              <a href={h.url} target="_blank" rel="noopener noreferrer">{h.title}</a>
              <span className="muted"> · {h.source}, {fmtDate(h.date)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function AnalysisBlock({ t }: { t: EventTexts | undefined }) {
  return (
    <section className="panel-section">
      <h3>Analysis{t?.analysis?.as_of ? <span className="muted"> · as of {fmtDate(t.analysis.as_of)}</span> : null}</h3>
      {t?.analysis ? (
        <>
          <p>{t.analysis.text}</p>
          <p className="disclaimer">AI-generated · may be inaccurate · not financial advice.</p>
        </>
      ) : <p className="muted">Analysis coming soon.</p>}
    </section>
  );
}
