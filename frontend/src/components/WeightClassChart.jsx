import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.name}</strong>
      <div>{d.fight_count.toLocaleString()} fights</div>
    </div>
  );
}

export default function WeightClassChart({ data }) {
  if (!data?.length) return null;

  return (
    <div className="chart-card wide">
      <h3>Fights by weight class</h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 24, left: 0, bottom: 0 }}
        >
          <CartesianGrid stroke={INK.grid} horizontal={false} />
          <XAxis type="number" tick={{ fill: INK.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="name"
            width={175}
            interval={0}
            tick={{ fill: INK.secondary, fontSize: 11.5 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
          <Bar dataKey="fight_count" fill={SEQUENTIAL_BLUE} radius={[0, 4, 4, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
