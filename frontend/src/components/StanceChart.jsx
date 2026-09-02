import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.stance}</strong>
      <div>{d.win_pct}% win rate</div>
      <div className="muted">{d.wins} wins of {d.total_fights} decided fights</div>
    </div>
  );
}

export default function StanceChart({ data }) {
  if (!data?.length) return null;
  const sorted = [...data].sort((a, b) => b.win_pct - a.win_pct);

  return (
    <div className="chart-card">
      <h3>Win rate by stance</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={sorted} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis dataKey="stance" tick={{ fill: INK.muted, fontSize: 12 }} axisLine={{ stroke: INK.grid }} tickLine={false} />
          <YAxis
            tick={{ fill: INK.muted, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            unit="%"
            domain={[0, (max) => Math.ceil(max / 10) * 10]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
          <Bar dataKey="win_pct" fill={SEQUENTIAL_BLUE} radius={[4, 4, 0, 0]} maxBarSize={56} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
