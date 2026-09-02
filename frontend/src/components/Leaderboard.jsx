import { useEffect, useState } from "react";
import { getLeaderboard, getWeightClasses } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

const METRICS = [
  { key: "sig_strikes", label: "Sig. strikes landed (career)", format: (v) => v.toLocaleString() },
  { key: "accuracy", label: "Striking accuracy (min. 150 attempts)", format: (v) => `${v}%` },
  { key: "ko_wins", label: "KO/TKO wins", format: (v) => v },
  { key: "sub_wins", label: "Submission wins", format: (v) => v },
  {
    key: "control_time",
    label: "Control time (career)",
    format: (v) => `${Math.floor(v / 60)}:${String(v % 60).padStart(2, "0")}`,
  },
  { key: "takedowns", label: "Takedowns landed (career)", format: (v) => v },
];

export default function Leaderboard() {
  const [metric, setMetric] = useState("sig_strikes");
  const [weightClasses, setWeightClasses] = useState([]);
  const [weightClass, setWeightClass] = useState("");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const nav = useDetailNav();

  useEffect(() => {
    getWeightClasses().then((wcs) => setWeightClasses(wcs.map((w) => w.name)));
  }, []);

  useEffect(() => {
    getLeaderboard(metric, { weightClass: weightClass || undefined, limit: 10 })
      .then(setRows)
      .catch((e) => setError(e.message));
  }, [metric, weightClass]);

  const activeMetric = METRICS.find((m) => m.key === metric);

  return (
    <div className="chart-card">
      <h3>Leaderboard</h3>
      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        <select className="text-input" style={{ width: "auto" }} value={metric} onChange={(e) => setMetric(e.target.value)}>
          {METRICS.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>
        <select className="text-input" style={{ width: "auto" }} value={weightClass} onChange={(e) => setWeightClass(e.target.value)}>
          <option value="">All divisions</option>
          {weightClasses.map((wc) => <option key={wc} value={wc}>{wc}</option>)}
        </select>
      </div>
      {error && <div className="error-text">{error}</div>}
      <table className="fight-history">
        <thead>
          <tr>
            <th>#</th>
            <th>Fighter</th>
            <th style={{ textAlign: "right" }}>{activeMetric.label}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.fighter_id}>
              <td>{i + 1}</td>
              <td>
                <button className="link-btn" onClick={() => nav.openFighter(r.fighter_id)}>
                  {r.first_name} {r.last_name}
                </button>
              </td>
              <td style={{ textAlign: "right" }}>{activeMetric.format(r.value)}</td>
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
