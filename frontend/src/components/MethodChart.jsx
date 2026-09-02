import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CATEGORICAL, INK } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.method_category}</strong>
      <div>{d.fight_count.toLocaleString()} fights</div>
    </div>
  );
}

export default function MethodChart({ data }) {
  if (!data?.length) return null;
  const total = data.reduce((sum, d) => sum + d.fight_count, 0);

  return (
    <div className="chart-card">
      <h3>Method of victory</h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="fight_count"
            nameKey="method_category"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            label={({ fight_count }) => `${Math.round((fight_count / total) * 100)}%`}
            labelLine={false}
          >
            {data.map((d) => (
              <Cell key={d.method_category} fill={CATEGORICAL[d.method_category] ?? INK.muted} />
            ))}
          </Pie>
          <Legend wrapperStyle={{ fontSize: 12, color: INK.secondary }} />
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
