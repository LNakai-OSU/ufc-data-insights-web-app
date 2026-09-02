import { formatHeight } from "../formatters";

// Renders a fighter's bio + fight history. Shared by FighterSearch (shown
// inline, there's room) and WorldMap's country panel (shown in a Modal,
// since the narrow sidebar doesn't have room for the fight history table).
//
// onSelectFighter/onSelectEvent are optional - when provided (via
// useDetailNav, see DetailView.jsx), the opponent name and event name in
// each fight-history row become clickable, navigating to that fighter's
// or event's own detail view in place. Opponent name is only clickable
// when the row has an opponent_id - some fight-history rows don't (the
// source only gives opponent names for bouts, and name-based resolution
// during data load is sometimes ambiguous - see db/schema.sql).
export default function FighterDetailCard({ fighter, onSelectFighter, onSelectEvent }) {
  if (!fighter) return null;

  return (
    <div className="fighter-detail">
      <h4>
        {fighter.first_name} {fighter.last_name}
        {fighter.nickname && <span className="muted"> "{fighter.nickname}"</span>}
      </h4>
      <div className="fighter-bio-grid">
        <div><span className="muted">Stance</span> {fighter.stance ?? "—"}</div>
        <div><span className="muted">Height</span> {formatHeight(fighter.height_in)}</div>
        <div><span className="muted">Reach</span> {fighter.reach_in ? `${fighter.reach_in}"` : "—"}</div>
        <div><span className="muted">Weight</span> {fighter.weight_lbs ? `${fighter.weight_lbs} lbs` : "—"}</div>
      </div>

      <table className="fight-history">
        <thead>
          <tr>
            <th>Date</th>
            <th>Event</th>
            <th>Opponent</th>
            <th>Result</th>
            <th>Method</th>
          </tr>
        </thead>
        <tbody>
          {fighter.fights.map((f) => (
            <tr key={f.fight_id}>
              <td>{f.event_date ?? "—"}</td>
              <td>
                {onSelectEvent ? (
                  <button className="link-btn" onClick={() => onSelectEvent(f.event_id)}>
                    {f.event_name}
                  </button>
                ) : (
                  f.event_name
                )}
              </td>
              <td>
                {onSelectFighter && f.opponent_id ? (
                  <button className="link-btn" onClick={() => onSelectFighter(f.opponent_id)}>
                    {f.opponent_name}
                  </button>
                ) : (
                  f.opponent_name
                )}
              </td>
              <td className={`outcome outcome-${f.outcome}`}>{f.outcome}</td>
              <td>{f.method ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
