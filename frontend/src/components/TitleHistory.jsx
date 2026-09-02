import { useEffect, useState } from "react";
import { getTitleHistory, getWeightClasses } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

export default function TitleHistory() {
  const [weightClasses, setWeightClasses] = useState([]);
  const [weightClass, setWeightClass] = useState("Lightweight");
  const [fights, setFights] = useState(null);
  const [error, setError] = useState(null);
  const nav = useDetailNav();

  useEffect(() => {
    getWeightClasses().then((wcs) => setWeightClasses(wcs.map((w) => w.name)));
  }, []);

  useEffect(() => {
    if (!weightClass) return;
    getTitleHistory(weightClass).then(setFights).catch((e) => setError(e.message));
  }, [weightClass]);

  return (
    <div className="chart-card">
      <h3>Championship history</h3>
      <select className="text-input" style={{ width: "auto", marginBottom: 10 }} value={weightClass} onChange={(e) => setWeightClass(e.target.value)}>
        {weightClasses.map((wc) => <option key={wc} value={wc}>{wc}</option>)}
      </select>
      {error && <div className="error-text">{error}</div>}
      {fights && fights.length === 0 && <p className="muted">No title fights recorded for this division.</p>}

      <ul className="title-timeline">
        {fights?.map((f) => {
          const FighterLink = ({ id, name }) =>
            id ? <button className="link-btn" onClick={() => nav.openFighter(id)}>{name}</button> : name;

          const isDecided = f.result === "fighter_1_win" || f.result === "fighter_2_win";
          const winnerIsFighter1 = f.winner_id === f.fighter_1_id;

          return (
            <li key={f.fight_id}>
              <span className="muted">{f.event_date ?? "date unknown"}</span>{" "}
              {isDecided ? (
                <>
                  <FighterLink id={f.winner_id} name={winnerIsFighter1 ? f.fighter_1_name_raw : f.fighter_2_name_raw} />
                  {" def. "}
                  <FighterLink
                    id={winnerIsFighter1 ? f.fighter_2_id : f.fighter_1_id}
                    name={winnerIsFighter1 ? f.fighter_2_name_raw : f.fighter_1_name_raw}
                  />
                  {" "}
                  <span className="muted">by {f.method ?? "decision"}</span>
                </>
              ) : (
                <>
                  <FighterLink id={f.fighter_1_id} name={f.fighter_1_name_raw} />
                  {" vs. "}
                  <FighterLink id={f.fighter_2_id} name={f.fighter_2_name_raw} />
                  {" "}
                  <span className="muted">({f.result === "draw" ? "draw" : "no contest"})</span>
                </>
              )}
              {f.is_interim_title && <span className="tag gold-tag">Interim</span>}
            </li>
          );
        })}
      </ul>

      {nav.view && (
        <Modal onClose={nav.close}>
          <DetailView nav={nav} />
        </Modal>
      )}
    </div>
  );
}
