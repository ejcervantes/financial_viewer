import { useEffect, useMemo, useState } from "react";
import type { GuardianArticle, Headline } from "../types";
import { loadGuardian } from "../data";
import { fmtDate } from "../format";

// Official file required by the Guardian Open Platform terms §6(b)(vi).
const GUARDIAN_LOGO = "https://static.guim.co.uk/sys-images/Guardian/Pix/pictures/2010/03/01/poweredbyguardianBLACK.png";

// Remove scripts and inline event handlers only; the text itself is shown unedited (terms §6(c)(i)).
function safeHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script").forEach((n) => n.remove());
  doc.querySelectorAll("*").forEach((el) => {
    for (const a of [...el.attributes]) if (a.name.toLowerCase().startsWith("on")) el.removeAttribute(a.name);
    if (el.tagName === "A") { el.setAttribute("target", "_blank"); el.setAttribute("rel", "noopener noreferrer"); }
  });
  return doc.body.innerHTML;
}

export default function ArticleModal({ h, onClose }: { h: Headline; onClose: () => void }) {
  const isGuardian = h.source === "The Guardian";
  // undefined = loading, null = not available (show the link only)
  const [article, setArticle] = useState<GuardianArticle | null | undefined>(isGuardian && h.id ? undefined : null);

  useEffect(() => {
    if (!isGuardian || !h.id) return;
    loadGuardian().then((g) => setArticle(g.articles[h.id!] ?? null)).catch(() => setArticle(null));
  }, [isGuardian, h.id]);

  useEffect(() => {
    // Capture phase so Escape closes only this window, not the event panel behind it.
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } };
    window.addEventListener("keydown", k, true);
    return () => window.removeEventListener("keydown", k, true);
  }, [onClose]);

  const body = useMemo(() => (article ? safeHtml(article.body) : ""), [article]);
  const year = (article?.date || h.date).slice(0, 4);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <article className="modal" role="dialog" aria-modal="true" aria-label={h.title} onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        <p className="modal-source">{h.source} · {fmtDate(article?.date || h.date)}</p>
        <h2 className="modal-title">{article?.headline ?? h.title}</h2>

        {isGuardian ? (
          <>
            {article === undefined && <p className="muted">Loading article…</p>}
            {article && (
              <>
                {article.byline && <p className="modal-byline">{article.byline}</p>}
                <div className="modal-body" dangerouslySetInnerHTML={{ __html: body }} />
                <p className="modal-copy">© {year} Guardian News &amp; Media Limited or its affiliated companies. All rights reserved. Republished through the Guardian Open Platform for personal, non-commercial use.</p>
              </>
            )}
            {article === null && <p className="muted">The article text isn't available right now. You can read it on theguardian.com.</p>}
            <div className="modal-foot">
              <a className="modal-link" href={article?.url ?? h.url} target="_blank" rel="noopener noreferrer">Original article on theguardian.com ↗</a>
              <a href="https://www.theguardian.com/open-platform" target="_blank" rel="noopener noreferrer">
                <img className="modal-logo" src={GUARDIAN_LOGO} alt="Powered by The Guardian" />
              </a>
            </div>
          </>
        ) : (
          <>
            {h.abstract ? <p className="modal-abstract">{h.abstract}</p> : <p className="muted">No summary available.</p>}
            <div className="modal-foot">
              <a className="modal-link button" href={h.url} target="_blank" rel="noopener noreferrer">Read the full article at nytimes.com ↗</a>
              <span className="muted">Data provided by The New York Times</span>
            </div>
          </>
        )}
      </article>
    </div>
  );
}
