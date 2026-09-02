import { useEffect, useState } from "react";
import { getRivalries } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import Modal from "./Modal";

export default function RivalriesTable() {
  const [data, setData] = useState([]);
  const nav = useDetailNav();

  useEffect(() => {
    getRivalries().then(setData);
  }, []);

  if (!data.length) return null;

  return (
    <div className="chart-card">
      <h3>Rivalries (fought 2+ times)</h3>
      <ul className="title-timeline">
        {data.map((r, i) => (
          <li key={i}>
            <button className="link-btn" onClick={() => nav.openFighter(r.a_id)}>
              {r.a_first} {r.a_last}
            </button>
            {" vs. "}
            <button className="link-btn" onClick={() => nav.openFighter(r.b_id)}>
              {r.b_first} {r.b_last}
            </button>
            <span className="tag">{r.fight_count}× fought</span>
          </li>
        ))}
      </ul>

      {nav.view && (
        <Modal onClose={nav.close}>
          <DetailView nav={nav} />
        </Modal>
      )}
    </div>
  );
}
