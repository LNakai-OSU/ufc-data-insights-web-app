import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAgePerformanceCurve } from "../api";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.age_bucket}</strong>
      <div>{d.accuracy}% sig. strike accuracy</div>
    </div>
  );
}

export default function AgeCurveChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getAgePerformanceCurve().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Striking accuracy by age</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis dataKey="age_bucket" tick={{ fill: INK.muted, fontSize: 11 }} axisLine={{ stroke: INK.grid }} tickLine={false} />
          <YAxis tick={{ fill: INK.muted, fontSize: 12 }} axisLine={false} tickLine={false} unit="%" domain={[35, 55]} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey="accuracy" stroke={SEQUENTIAL_BLUE} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
