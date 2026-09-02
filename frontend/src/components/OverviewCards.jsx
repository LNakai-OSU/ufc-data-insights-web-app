export default function OverviewCards({ overview }) {
  if (!overview) return null;

  const cards = [
    { label: "Fighters", value: overview.fighters },
    { label: "Fights", value: overview.fights },
    { label: "Events", value: overview.events },
    { label: "Weight Classes", value: overview.weight_classes },
  ];

  return (
    <div className="card-row">
      {cards.map((c) => (
        <div className="stat-card" key={c.label}>
          <div className="stat-value">{c.value.toLocaleString()}</div>
          <div className="stat-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
