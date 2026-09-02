import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getFightsByYear } from "../api";
import { INK, SEQUENTIAL_BLUE } from "../colors";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.year}</strong>
      <div>{d.fight_count.toLocaleString()} fights</div>
    </div>
  );
}

export default function FightsByYearChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    getFightsByYear().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Fights per year</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          <XAxis
            dataKey="year"
            tick={{ fill: INK.muted, fontSize: 11 }}
            axisLine={{ stroke: INK.grid }}
            tickLine={false}
            interval={4}
          />
          <YAxis tick={{ fill: INK.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
          <Bar dataKey="fight_count" fill={SEQUENTIAL_BLUE} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
