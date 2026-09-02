import { useEffect, useState } from "react";
import { getActiveYears, getDivisionLeaderboard, getWeightClasses } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export default function DivisionLeaderboard() {
  const [weightClasses, setWeightClasses] = useState([]);
  const [yearRange, setYearRange] = useState(null);
  const [weightClass, setWeightClass] = useState("Lightweight");
  const [year, setYear] = useState(null);
  const [month, setMonth] = useState("");
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const nav = useDetailNav();

  useEffect(() => {
    getWeightClasses().then((wcs) => setWeightClasses(wcs.map((w) => w.name)));
    getActiveYears().then((r) => {
      setYearRange(r);
      setYear(r.max_year);
    });
  }, []);

  useEffect(() => {
    if (!weightClass || !year) return;
    getDivisionLeaderboard(weightClass, year, month || undefined)
      .then(setRows)
      .catch((e) => setError(e.message));
  }, [weightClass, year, month]);

  if (!yearRange) return null;

  const years = [];
  for (let y = yearRange.max_year; y >= yearRange.min_year; y--) years.push(y);

  return (
    <div className="chart-card">
      <h3>Division leaderboard</h3>
      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        <select className="text-input" style={{ width: "auto" }} value={weightClass} onChange={(e) => setWeightClass(e.target.value)}>
          {weightClasses.map((wc) => <option key={wc} value={wc}>{wc}</option>)}
        </select>
        <select className="text-input" style={{ width: "auto" }} value={year} onChange={(e) => setYear(Number(e.target.value))}>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <select className="text-input" style={{ width: "auto" }} value={month} onChange={(e) => setMonth(e.target.value)}>
          <option value="">All months</option>
          {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
        </select>
      </div>
      {error && <div className="error-text">{error}</div>}
      {rows && rows.length === 0 && <p className="muted">No fights in this division for that period.</p>}
      {rows && rows.length > 0 && (
        <table className="fight-history">
          <thead>
            <tr>
              <th>Fighter</th>
              <th style={{ textAlign: "right" }}>Wins</th>
              <th style={{ textAlign: "right" }}>Fights</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.fighter_id}>
                <td>
                  <button className="link-btn" onClick={() => nav.openFighter(r.fighter_id)}>
                    {r.first_name} {r.last_name}
                  </button>
                  {r.nickname && <span className="muted"> "{r.nickname}"</span>}
                </td>
                <td style={{ textAlign: "right" }}>{r.wins_in_period}</td>
                <td style={{ textAlign: "right" }}>{r.fights_in_period}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {nav.view && (
        <Modal onClose={nav.close}>
          <DetailView nav={nav} />
        </Modal>
      )}
    </div>
  );
}
