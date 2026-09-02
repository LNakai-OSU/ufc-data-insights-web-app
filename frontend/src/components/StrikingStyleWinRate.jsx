import { useEffect, useState } from "react";
import { getStrikingStyleWinRate } from "../api";

export default function StrikingStyleWinRate() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getStrikingStyleWinRate().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Volume vs. accuracy: which wins more?</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Fighters split at the median on career strike volume and accuracy (min. 5 fights), then each group's overall win rate.
      </p>
      <table className="fight-history">
        <thead>
          <tr>
            <th>Volume</th>
            <th>Accuracy</th>
            <th style={{ textAlign: "right" }}>Win rate</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={`${r.volume_group}-${r.accuracy_group}`}>
              <td>{r.volume_group}</td>
              <td>{r.accuracy_group}</td>
              <td style={{ textAlign: "right" }} className="mono">{r.win_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
