import { useEffect, useState } from "react";
import { getHomeCountryEffect } from "../api";

export default function HomeCountryEffectCard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getHomeCountryEffect().then(setData);
  }, []);

  if (!data) return null;

  return (
    <div className="chart-card">
      <h3>Home country effect</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Win rate when the event is held in the fighter's own birth country vs. everywhere else.
      </p>
      <div className="compare-grid">
        <div className="compare-cell">
          <div className="compare-value">{data.home.win_pct}%</div>
          <div className="compare-label">Home ({data.home.total.toLocaleString()} fights)</div>
        </div>
        <div className="compare-cell">
          <div className="compare-value">{data.away.win_pct}%</div>
          <div className="compare-label">Away ({data.away.total.toLocaleString()} fights)</div>
        </div>
      </div>
    </div>
  );
}
