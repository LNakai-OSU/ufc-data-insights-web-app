import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getFightPaceByYear } from "../api";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.year}</strong>
      <div>{d.sig_strikes_per_minute} sig. strikes landed / min</div>
    </div>
  );
}

export default function FightPaceChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getFightPaceByYear().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Fight pace over time</h3>
      <p className="muted" style={{ marginTop: 0, fontSize: "0.78em" }}>
        Approximate - every round is treated as a full 5 minutes.
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis dataKey="year" tick={{ fill: INK.muted, fontSize: 11 }} axisLine={{ stroke: INK.grid }} tickLine={false} interval={4} />
          <YAxis tick={{ fill: INK.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="sig_strikes_per_minute" stroke={SEQUENTIAL_BLUE} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
