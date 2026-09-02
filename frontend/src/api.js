const BASE_URL = "http://localhost:8000";

async function getJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getOverview() {
  return getJSON("/api/overview");
}

export function getStanceWinRate() {
  return getJSON("/api/stats/stance-win-rate");
}

export function getWeightClasses() {
  return getJSON("/api/stats/weight-classes");
}

export function getMethods() {
  return getJSON("/api/stats/methods");
}

export function getActiveYears() {
  return getJSON("/api/stats/active-years");
}

export function getFightersByCountry(year) {
  return getJSON(`/api/stats/fighters-by-country?year=${year}`);
}

export function getFightersFromCountry(country, year) {
  return getJSON(`/api/stats/fighters-by-country/${encodeURIComponent(country)}?year=${year}`);
}

export function getFightsByYear() {
  return getJSON("/api/stats/fights-by-year");
}

export function getFinishRateByYear() {
  return getJSON("/api/stats/finish-rate-by-year");
}

export function getLeaderboard(metric, { weightClass, limit = 10 } = {}) {
  const params = new URLSearchParams({ metric, limit });
  if (weightClass) params.set("weight_class", weightClass);
  return getJSON(`/api/stats/leaderboard?${params}`);
}

export function getDivisionLeaderboard(weightClass, year, month) {
  const params = new URLSearchParams({ weight_class: weightClass, year });
  if (month) params.set("month", month);
  return getJSON(`/api/stats/division-leaderboard?${params}`);
}

export function getTitleHistory(weightClass) {
  return getJSON(`/api/stats/title-history?weight_class=${encodeURIComponent(weightClass)}`);
}

export function getDivisionRankings(weightClass) {
  return getJSON(`/api/stats/division-rankings?weight_class=${encodeURIComponent(weightClass)}`);
}

export function searchFighters(q) {
  return getJSON(`/api/fighters?q=${encodeURIComponent(q)}&limit=10`);
}

export function getFighterDetail(fighterId) {
  return getJSON(`/api/fighters/${encodeURIComponent(fighterId)}`);
}

export function getEventDetail(eventId) {
  return getJSON(`/api/events/${encodeURIComponent(eventId)}`);
}

export function getChampionshipRoundsFade() {
  return getJSON("/api/stats/championship-rounds-fade");
}

export function getFirstRoundFinishRate() {
  return getJSON("/api/stats/first-round-finish-rate");
}

export function getReachAdvantage() {
  return getJSON("/api/stats/reach-advantage");
}

export function getStanceMatchups() {
  return getJSON("/api/stats/stance-matchups");
}

export function getStrikingStyleWinRate() {
  return getJSON("/api/stats/striking-style-win-rate");
}

export function getAgePerformanceCurve() {
  return getJSON("/api/stats/age-performance-curve");
}

export function getWinStreaks() {
  return getJSON("/api/stats/win-streaks");
}

export function getFightPaceByYear() {
  return getJSON("/api/stats/fight-pace-by-year");
}

export function getSplitDecisionRateByYear() {
  return getJSON("/api/stats/split-decision-rate-by-year");
}

export function getCountryStyles() {
  return getJSON("/api/stats/country-styles");
}

export function getHomeCountryEffect() {
  return getJSON("/api/stats/home-country-effect");
}

export function getTitleInsights() {
  return getJSON("/api/stats/title-insights");
}

export function getFastestFinishes() {
  return getJSON("/api/stats/fastest-finishes");
}

export function getRivalries() {
  return getJSON("/api/stats/rivalries");
}

export async function askChat(question) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return body;
}
