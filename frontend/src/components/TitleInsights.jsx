import { useEffect, useState } from "react";
import { getTitleInsights } from "../api";

export default function TitleInsights() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getTitleInsights().then(setData);
  }, []);

  if (!data) return null;

  const titleRow = data.finish_rates.find((r) => r.is_title_bout);
  const nonTitleRow = data.finish_rates.find((r) => !r.is_title_bout);

  return (
    <div className="chart-card wide">
      <h3>Title fight insights</h3>

      {titleRow && nonTitleRow && (
        <div className="compare-grid" style={{ maxWidth: 420 }}>
          <div className="compare-cell">
            <div className="compare-value">{titleRow.finish_pct}%</div>
            <div className="compare-label">Title fight finish rate</div>
          </div>
          <div className="compare-cell">
            <div className="compare-value">{nonTitleRow.finish_pct}%</div>
            <div className="compare-label">Non-title finish rate</div>
          </div>
        </div>
      )}

      <p className="muted" style={{ marginBottom: 6 }}>
        Avg. title reign by division (first win to last successful defense - a champion with no
        defense yet shows as 0 days, not "still champion").
      </p>
      <table className="fight-history">
        <thead>
          <tr>
            <th>Division</th>
            <th style={{ textAlign: "right" }}>Avg. reign (days)</th>
            <th style={{ textAlign: "right" }}>Reigns</th>
          </tr>
        </thead>
        <tbody>
          {data.reign_lengths.map((r) => (
            <tr key={r.weight_class}>
              <td>{r.weight_class}</td>
              <td style={{ textAlign: "right" }} className="mono">{r.avg_reign_days ?? "—"}</td>
              <td style={{ textAlign: "right" }} className="mono">{r.reigns_counted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
