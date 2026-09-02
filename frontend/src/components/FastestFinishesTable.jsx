import { useEffect, useState } from "react";
import { getFastestFinishes } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

function formatTime(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function FastestFinishesTable() {
  const [data, setData] = useState([]);
  const nav = useDetailNav();

  useEffect(() => {
    getFastestFinishes().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card wide">
      <h3>Fastest finishes (round 1)</h3>
      <table className="fight-history">
        <thead>
          <tr>
            <th>Time</th>
            <th>Winner</th>
            <th>Opponent</th>
            <th>Method</th>
            <th>Event</th>
          </tr>
        </thead>
        <tbody>
          {data.map((f) => {
            const winnerIsF1 = f.winner_id === f.fighter_1_id;
            const winnerId = f.winner_id;
            const winnerName = winnerIsF1 ? f.fighter_1_name_raw : f.fighter_2_name_raw;
            const opponentId = winnerIsF1 ? f.fighter_2_id : f.fighter_1_id;
            const opponentName = winnerIsF1 ? f.fighter_2_name_raw : f.fighter_1_name_raw;
            return (
              <tr key={f.fight_id}>
                <td className="mono">{formatTime(f.time_seconds)}</td>
                <td>
                  {winnerId ? (
                    <button className="link-btn" onClick={() => nav.openFighter(winnerId)}>{winnerName}</button>
                  ) : (
                    winnerName
                  )}
                </td>
                <td>
                  {opponentId ? (
                    <button className="link-btn" onClick={() => nav.openFighter(opponentId)}>{opponentName}</button>
                  ) : (
                    opponentName
                  )}
                </td>
                <td>{f.method}</td>
                <td className="muted">{f.event_name}</td>
              </tr>
            );
          })}
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
