import { useEffect, useState } from "react";
import { getStanceMatchups } from "../api";

export default function StanceMatchupTable() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getStanceMatchups().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Stance matchup win rates</h3>
      <p className="muted" style={{ marginTop: 0 }}>Win rate of "your stance" facing "opponent stance," min. 20 fights.</p>
      <table className="fight-history">
        <thead>
          <tr>
            <th>Your stance</th>
            <th>Vs.</th>
            <th style={{ textAlign: "right" }}>Win rate</th>
            <th style={{ textAlign: "right" }}>Fights</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={`${r.my_stance}-${r.opp_stance}`}>
              <td>{r.my_stance}</td>
              <td>{r.opp_stance}</td>
              <td style={{ textAlign: "right" }} className="mono">{r.win_pct}%</td>
              <td style={{ textAlign: "right" }} className="mono">{r.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
