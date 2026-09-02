import { useEffect, useState } from "react";
import { getWinStreaks } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

export default function WinStreaksTable() {
  const [data, setData] = useState([]);
  const nav = useDetailNav();

  useEffect(() => {
    getWinStreaks().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Current win streaks</h3>
      <p className="muted" style={{ marginTop: 0 }}>Avg. opponent win rate = how good the competition was during the streak.</p>
      <table className="fight-history">
        <thead>
          <tr>
            <th>Fighter</th>
            <th style={{ textAlign: "right" }}>Streak</th>
            <th style={{ textAlign: "right" }}>Avg. opponent win rate</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.fighter_id}>
              <td>
                <button className="link-btn" onClick={() => nav.openFighter(r.fighter_id)}>
                  {r.first_name} {r.last_name}
                </button>
              </td>
              <td style={{ textAlign: "right" }} className="mono">{r.current_streak}</td>
              <td style={{ textAlign: "right" }} className="mono">
                {r.avg_opponent_win_pct != null ? `${r.avg_opponent_win_pct}%` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {nav.view && (
        <Modal onClose={nav.close}>
          <DetailView nav={nav} />
        </Modal>
      )}
    </div>
  );
}
