import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getSplitDecisionRateByYear } from "../api";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.year}</strong>
      <div>{d.split_pct}% of decisions were split ({d.split_decisions} of {d.total_decisions})</div>
    </div>
  );
}

export default function SplitDecisionChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getSplitDecisionRateByYear().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Split decisions over time</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis dataKey="year" tick={{ fill: INK.muted, fontSize: 11 }} axisLine={{ stroke: INK.grid }} tickLine={false} interval={4} />
          <YAxis tick={{ fill: INK.muted, fontSize: 12 }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="split_pct" stroke={SEQUENTIAL_BLUE} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
