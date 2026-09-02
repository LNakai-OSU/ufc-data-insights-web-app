import { useEffect, useState } from "react";
import { getDivisionRankings, getWeightClasses } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

export default function DivisionRankings() {
  const [weightClasses, setWeightClasses] = useState([]);
  const [weightClass, setWeightClass] = useState("Lightweight");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const nav = useDetailNav();

  useEffect(() => {
    getWeightClasses().then((wcs) => setWeightClasses(wcs.map((w) => w.name)));
  }, []);

  useEffect(() => {
    if (!weightClass) return;
    getDivisionRankings(weightClass).then(setData).catch((e) => setError(e.message));
  }, [weightClass]);

  return (
    <div className="chart-card">
      <h3>Division rankings</h3>
      <select className="text-input" style={{ width: "auto", marginBottom: 4 }} value={weightClass} onChange={(e) => setWeightClass(e.target.value)}>
        {weightClasses.map((wc) => <option key={wc} value={wc}>{wc}</option>)}
      </select>
      {data?.scraped_at && (
        <p className="muted" style={{ marginTop: 4, marginBottom: 10 }}>
          Official UFC rankings, as of {new Date(data.scraped_at).toLocaleDateString()}.
        </p>
      )}
      {error && <div className="error-text">{error}</div>}

      {data && (
        <>
          {data.champion ? (
            <div style={{ marginBottom: 8 }}>
              <span className="tag gold-tag">Champion</span>{" "}
              <button className="link-btn" onClick={() => nav.openFighter(data.champion.fighter_id)}>
                {data.champion.name}
              </button>
            </div>
          ) : (
            <p className="muted">No current rankings available for this division.</p>
          )}
          <ul className="title-timeline">
            {data.contenders.map((c) => (
              <li key={c.fighter_id}>
                <span className="muted">#{c.rank}</span>{" "}
                <button className="link-btn" onClick={() => nav.openFighter(c.fighter_id)}>
                  {c.name}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {nav.view && (
        <Modal onClose={nav.close}>
          <DetailView nav={nav} />
        </Modal>
      )}
    </div>
  );
}
