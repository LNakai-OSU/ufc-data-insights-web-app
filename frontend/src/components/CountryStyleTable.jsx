import { useEffect, useState } from "react";
import { getCountryStyles } from "../api";

export default function CountryStyleTable() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getCountryStyles().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card wide">
      <h3>Finishing style by country</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Share of each country's wins that came by submission/KO, ranked by submission rate. Min. 15 fighters per country.
      </p>
      <table className="fight-history">
        <thead>
          <tr>
            <th>Country</th>
            <th style={{ textAlign: "right" }}>Fighters</th>
            <th style={{ textAlign: "right" }}>Sub. win %</th>
            <th style={{ textAlign: "right" }}>KO win %</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.country}>
              <td>{r.country}</td>
              <td style={{ textAlign: "right" }} className="mono">{r.fighter_count}</td>
              <td style={{ textAlign: "right" }} className="mono">{r.sub_win_pct}%</td>
              <td style={{ textAlign: "right" }} className="mono">{r.ko_win_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
