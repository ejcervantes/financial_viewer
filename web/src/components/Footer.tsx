import type { Meta } from "../types";
import { fmtDate } from "../format";

export default function Footer({ meta }: { meta: Meta }) {
  return (
    <footer className="footer">
      <details>
        <summary>How it's calculated</summary>
        <ul>
          <li>Data: Yahoo Finance (adjusted close), daily. Returns in local currency.</li>
          <li>Base price: last close before the announcement. Day 0: session in progress at the announcement, or the next session to open. Horizons are 5, 21 and 63 sessions after day 0, counted on each market's own calendar.</li>
          <li>Absolute = sector return. vs. market = sector return minus benchmark return over the same window (SPY, STOXX Europe 600, Hang Seng; Shanghai Composite for China Defense, because CSI 300 history is not available from the data source).</li>
          <li>China and several other sectors use equal-weighted baskets of large caps, rebalanced daily; days with fewer than two constituents are shown as insufficient data.</li>
          <li>US "Banks" uses XLF (Financials) for its longer history. European sector ETFs have data from 2008.</li>
          <li>Baskets use current large caps; historical results may carry survivorship bias.</li>
          <li>Longer horizons include other news; reactions are not attributable to a single event.</li>
          <li>Episode drawdown = largest peak-to-trough fall of the sector inside the episode's dates.</li>
          <li>Context and analysis texts are written by an AI model (Claude) from the numbers shown and general historical knowledge. They may be inaccurate. Not financial advice.</li>
          <li>Uncertainty indices: Baker, Bloom & Davis (EPU); Caldara & Iacoviello (GPR).</li>
        </ul>
      </details>
      <p className="attrib">
        Not financial advice. Past reactions do not predict future ones.
        {" "}Data provided by The New York Times · Powered by The Guardian · Market data: Yahoo Finance · EPU: Baker, Bloom & Davis via FRED · GPR: Caldara & Iacoviello.
      </p>
      <p className="attrib muted">Prices through {fmtDate(meta.data_through)} · updated {fmtDate(meta.generated_at)}</p>
    </footer>
  );
}
