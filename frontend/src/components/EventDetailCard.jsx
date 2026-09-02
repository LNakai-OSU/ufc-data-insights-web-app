function FighterName({ id, name, onSelectFighter }) {
  if (!id) return <>{name}</>; // no id to navigate to - e.g. ambiguous/unresolved fighter match
  return (
    <button className="link-btn" onClick={() => onSelectFighter(id)}>
      {name}
    </button>
  );
}

export default function EventDetailCard({ event, onSelectFighter }) {
  if (!event) return null;

  return (
    <div className="event-detail">
      <h4>{event.name}</h4>
      <p className="muted">
        {event.event_date ?? "Date unknown"}
        {event.location && ` · ${event.location}`}
      </p>

      <table className="fight-history">
        <thead>
          <tr>
            <th>Weight Class</th>
            <th>Fighter 1</th>
            <th>Fighter 2</th>
            <th>Winner</th>
            <th>Method</th>
            <th>Round</th>
          </tr>
        </thead>
        <tbody>
          {event.fights.map((f) => (
            <tr key={f.fight_id}>
              <td>
                {f.weight_class ?? "—"}
                {f.is_title_bout && <span className="tag">Title</span>}
              </td>
              <td className={f.winner_id === f.fighter_1_id ? "outcome outcome-win" : ""}>
                <FighterName id={f.fighter_1_id} name={f.fighter_1_name_raw} onSelectFighter={onSelectFighter} />
              </td>
              <td className={f.winner_id === f.fighter_2_id ? "outcome outcome-win" : ""}>
                <FighterName id={f.fighter_2_id} name={f.fighter_2_name_raw} onSelectFighter={onSelectFighter} />
              </td>
              <td>
                {f.result === "draw" ? "Draw" : f.result === "no_contest" ? "No Contest" : (f.winner_id === f.fighter_1_id ? f.fighter_1_name_raw : f.fighter_2_name_raw)}
              </td>
              <td>{f.method ?? "—"}</td>
              <td>{f.round ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
