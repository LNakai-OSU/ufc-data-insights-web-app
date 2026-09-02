import { useEffect, useState } from "react";
import { searchFighters } from "../api";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";

export default function FighterSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const nav = useDetailNav();

  useEffect(() => {
    if (!query.trim()) return;
    const timeout = setTimeout(() => {
      searchFighters(query).then(setResults).catch((e) => setError(e.message));
    }, 300);
    return () => clearTimeout(timeout);
  }, [query]);

  function handleQueryChange(value) {
    setQuery(value);
    if (!value.trim()) setResults([]);
  }

  return (
    <div className="panel">
      <h3>Fighter lookup</h3>
      <input
        type="text"
        placeholder="Search by name or nickname..."
        value={query}
        onChange={(e) => handleQueryChange(e.target.value)}
        className="text-input"
      />
      {error && <div className="error-text">{error}</div>}

      <div className="fighter-search-body">
        <ul className="fighter-results">
          {results.map((f) => (
            <li key={f.fighter_id}>
              <button className="fighter-result-btn" onClick={() => nav.openFighter(f.fighter_id)}>
                {f.first_name} {f.last_name}
                {f.nickname && <span className="muted"> "{f.nickname}"</span>}
                {f.stance && <span className="tag">{f.stance}</span>}
              </button>
            </li>
          ))}
        </ul>

        <DetailView nav={nav} />
      </div>
    </div>
  );
}
