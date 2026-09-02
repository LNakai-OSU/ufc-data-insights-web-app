import { scaleQuantize } from "d3-scale";
import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { getActiveYears, getFightersByCountry, getFightersFromCountry } from "../api";
import { toAtlasCountryName } from "../countryNameMap";
import { useDetailNav } from "../useDetailNav";
import DetailView from "./DetailView";
import GloveLoader from "./GloveLoader";
import Modal from "./Modal";

// 50m (not 110m) resolution specifically because the 110m atlas drops small
// countries entirely (Cabo Verde, Guam) rather than just naming them
// differently - no override in countryNameMap.js can fix a missing shape.
const GEO_URL = "/countries-50m.json";
// Sequential blue ramp (magnitude encoding), light-to-dark against the
// light map surface - on a light ground darker reads as "more" (see
// colors.js for the same light-mode blue used elsewhere).
const SEQUENTIAL_STEPS = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
const NO_DATA_FILL = "#e1e0d9";
const SELECTED_FILL = "#e0b04a";
const HOVER_FILL = "#eb6834";
const MAP_STROKE = "#fcfcfb";

export default function WorldMap() {
  const [yearRange, setYearRange] = useState(null);
  const [year, setYear] = useState(null);
  const [countryData, setCountryData] = useState([]);
  const [atlasNames, setAtlasNames] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const [error, setError] = useState(null);

  const [selectedAtlasName, setSelectedAtlasName] = useState(null);
  const [selectedFighters, setSelectedFighters] = useState(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  const nav = useDetailNav();

  useEffect(() => {
    getActiveYears()
      .then((r) => {
        setYearRange(r);
        setYear(r.max_year);
      })
      .catch((e) => setError(e.message));

    fetch(GEO_URL)
      .then((r) => r.json())
      .then((topo) => {
        setAtlasNames(new Set(topo.objects.countries.geometries.map((g) => g.properties.name)));
      });
  }, []);

  useEffect(() => {
    if (year == null) return;
    getFightersByCountry(year).then(setCountryData).catch((e) => setError(e.message));
  }, [year]);

  function handleYearChange(newYear) {
    setYear(newYear);
    setSelectedAtlasName(null);
    setSelectedFighters(null);
  }

  const countsByAtlasName = useMemo(() => {
    const map = new Map();
    for (const row of countryData) {
      map.set(toAtlasCountryName(row.country), row.fighter_count);
    }
    return map;
  }, [countryData]);

  // Reverse lookup: an atlas name like "United Kingdom" can be fed by
  // several raw birthplace_country values (England/Scotland/Wales/United
  // Kingdom), so a click needs to query all of them, not just one.
  const rawCountriesByAtlasName = useMemo(() => {
    const map = new Map();
    for (const row of countryData) {
      const atlasName = toAtlasCountryName(row.country);
      if (!map.has(atlasName)) map.set(atlasName, []);
      map.get(atlasName).push(row.country);
    }
    return map;
  }, [countryData]);

  const unmatchedCountries = useMemo(() => {
    if (!atlasNames) return [];
    return countryData.filter((row) => !atlasNames.has(toAtlasCountryName(row.country)));
  }, [countryData, atlasNames]);

  const maxCount = Math.max(1, ...countryData.map((d) => d.fighter_count));
  const colorScale = scaleQuantize().domain([1, maxCount]).range(SEQUENTIAL_STEPS);

  function handleCountryClick(atlasName) {
    if (selectedAtlasName === atlasName) {
      setSelectedAtlasName(null);
      setSelectedFighters(null);
      return;
    }

    const rawCountries = rawCountriesByAtlasName.get(atlasName);
    if (!rawCountries) return; // no fighters there that year - nothing to show

    setSelectedAtlasName(atlasName);
    setSelectedFighters(null);
    setSelectedLoading(true);
    Promise.all(rawCountries.map((c) => getFightersFromCountry(c, year)))
      .then((lists) => {
        const merged = lists.flat().sort((a, b) => a.last_name.localeCompare(b.last_name));
        setSelectedFighters(merged);
      })
      .catch((e) => setError(e.message))
      .finally(() => setSelectedLoading(false));
  }

  if (!yearRange) return null;

  return (
    <div className="chart-card">
      <div className="map-header">
        <h3>Where active fighters are from</h3>
        <div className="year-display">{year}</div>
      </div>
      <input
        type="range"
        min={yearRange.min_year}
        max={yearRange.max_year}
        value={year}
        onChange={(e) => handleYearChange(Number(e.target.value))}
        className="year-slider"
      />
      {error && <div className="error-text">{error}</div>}

      <div className="map-layout">
        <div className="map-wrap">
          <ComposableMap projectionConfig={{ scale: 140 }} height={340} style={{ width: "100%", height: "auto" }}>
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const name = geo.properties.name;
                  const count = countsByAtlasName.get(name);
                  const isSelected = selectedAtlasName === name;
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill={isSelected ? SELECTED_FILL : count ? colorScale(count) : NO_DATA_FILL}
                      stroke={MAP_STROKE}
                      strokeWidth={0.5}
                      onMouseEnter={() => setTooltip({ name, count: count ?? 0 })}
                      onMouseLeave={() => setTooltip(null)}
                      onClick={() => handleCountryClick(name)}
                      style={{
                        default: { outline: "none", cursor: count ? "pointer" : "default" },
                        hover: { outline: "none", fill: isSelected ? SELECTED_FILL : HOVER_FILL },
                        pressed: { outline: "none" },
                      }}
                    />
                  );
                })
              }
            </Geographies>
          </ComposableMap>
          {tooltip && (
            <div className="map-tooltip">
              <strong>{tooltip.name}</strong>: {tooltip.count} active fighter{tooltip.count === 1 ? "" : "s"} in {year}
              {tooltip.count > 0 && <div className="muted">Click to see who</div>}
            </div>
          )}
        </div>

        {selectedAtlasName && (
          <div className="country-panel">
            <div className="country-panel-header">
              <h4>{selectedAtlasName}, {year}</h4>
              <button className="close-btn" onClick={() => handleCountryClick(selectedAtlasName)}>×</button>
            </div>
            {selectedLoading && <GloveLoader size="sm" />}
            {selectedFighters && (
              <ul className="country-fighter-list">
                {selectedFighters.map((f) => (
                  <li key={f.fighter_id}>
                    <button className="fighter-result-btn" onClick={() => nav.openFighter(f.fighter_id)}>
                      {f.first_name} {f.last_name}
                      {f.nickname && <span className="muted"> "{f.nickname}"</span>}
                      <span className="tag">{f.fights_that_year} fight{f.fights_that_year === 1 ? "" : "s"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <p className="muted map-caveat">
        Gray = no fighters that year, or birthplace not yet known (nationality
        data is being backfilled from UFC.com in the background and fills in
        over time). Click a colored country to see who.
      </p>
      {unmatchedCountries.length > 0 && (
        <p className="muted map-caveat">
          Not shown on map (country name not recognized):{" "}
          {unmatchedCountries.map((c) => `${c.country} (${c.fighter_count})`).join(", ")}
        </p>
      )}

      {nav.view && (
        <Modal onClose={nav.close}>
          <DetailView nav={nav} />
        </Modal>
      )}
    </div>
  );
}
