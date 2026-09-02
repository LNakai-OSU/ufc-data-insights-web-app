// Reconciles UFC.com's country-name phrasing (from fighters.birthplace_country)
// with the Natural Earth names used by the world-atlas topojson (e.g. UFC.com
// says "United States", the atlas says "United States of America"; British
// fighters' birthplaces often say "England"/"Scotland"/"Wales" rather than
// "United Kingdom"). Extend this as real scraped data surfaces new mismatches -
// unmapped names are surfaced in the UI rather than silently dropped, see
// WorldMap.jsx's unmatchedCountries handling.
const OVERRIDES = {
  "United States": "United States of America",
  USA: "United States of America",
  England: "United Kingdom",
  Scotland: "United Kingdom",
  Wales: "United Kingdom",
  "Northern Ireland": "United Kingdom",
  "Czech Republic": "Czechia",
  "Ivory Coast": "Côte d'Ivoire",
  "Cote d'Ivoire": "Côte d'Ivoire",
  "The Netherlands": "Netherlands",
  Holland: "Netherlands",
  "North Macedonia": "Macedonia",
  Swaziland: "eSwatini",
  Eswatini: "eSwatini",
  "Bosnia and Herzegovina": "Bosnia and Herz.",
  "Central African Republic": "Central African Rep.",
  "Dominican Republic": "Dominican Rep.",
  "Equatorial Guinea": "Eq. Guinea",
  "South Sudan": "S. Sudan",
  "Western Sahara": "W. Sahara",
  "Democratic Republic of the Congo": "Dem. Rep. Congo",
  "DR Congo": "Dem. Rep. Congo",
  "Republic of the Congo": "Congo",
};

export function toAtlasCountryName(ufcCountryName) {
  return OVERRIDES[ufcCountryName] ?? ufcCountryName;
}
