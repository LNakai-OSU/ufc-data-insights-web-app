import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getReachAdvantage } from "../api";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.reach_bucket}</strong>
      <div>{d.win_pct}% win rate ({d.wins} of {d.total})</div>
    </div>
  );
}

export default function ReachAdvantageChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getReachAdvantage().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Win rate by reach advantage</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis dataKey="reach_bucket" tick={{ fill: INK.muted, fontSize: 11 }} axisLine={{ stroke: INK.grid }} tickLine={false} />
          <YAxis tick={{ fill: INK.muted, fontSize: 12 }} axisLine={false} tickLine={false} unit="%" domain={[35, 60]} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
          <Bar dataKey="win_pct" fill={SEQUENTIAL_BLUE} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
