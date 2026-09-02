import { useEffect, useState } from "react";
import { getChampionshipRoundsFade } from "../api";

export default function ChampionshipRoundsFade() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getChampionshipRoundsFade().then(setData);
  }, []);

  if (!data?.early || !data?.late) return null;
  const { early, late } = data;

  return (
    <div className="chart-card">
      <h3>Championship rounds: early vs. late</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Rounds 1-3 vs. 4-5, in fights that actually reached round 4 (5-round/main-event bouts only).
      </p>
      <div className="compare-rows">
        <div className="compare-stat-row">
          <span className="left">{early.avg_sig_str_landed}</span>
          <span className="stat-name">Sig. strikes landed / round</span>
          <span className="right">{late.avg_sig_str_landed}</span>
        </div>
        <div className="compare-stat-row">
          <span className="left">{early.sig_str_accuracy}%</span>
          <span className="stat-name">Sig. strike accuracy</span>
          <span className="right">{late.sig_str_accuracy}%</span>
        </div>
        <div className="compare-stat-row">
          <span className="left">{early.avg_td_landed}</span>
          <span className="stat-name">Takedowns / round</span>
          <span className="right">{late.avg_td_landed}</span>
        </div>
        <div className="compare-stat-row">
          <span className="left mono">Rounds 1-3</span>
          <span />
          <span className="right mono">Rounds 4-5</span>
        </div>
      </div>
    </div>
  );
}
