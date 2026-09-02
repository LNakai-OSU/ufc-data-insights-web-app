import { useEffect, useState } from "react";
import { getMethods, getOverview, getStanceWinRate, getWeightClasses } from "./api";
import OverviewCards from "./components/OverviewCards";
import StanceChart from "./components/StanceChart";
import WeightClassChart from "./components/WeightClassChart";
import MethodChart from "./components/MethodChart";
import FightsByYearChart from "./components/FightsByYearChart";
import FinishRateChart from "./components/FinishRateChart";
import Leaderboard from "./components/Leaderboard";
import DivisionLeaderboard from "./components/DivisionLeaderboard";
import DivisionRankings from "./components/DivisionRankings";
import TitleHistory from "./components/TitleHistory";
import FighterSearch from "./components/FighterSearch";
import ChatPanel from "./components/ChatPanel";
import WorldMap from "./components/WorldMap";
import GloveLoader from "./components/GloveLoader";
import ChampionshipRoundsFade from "./components/ChampionshipRoundsFade";
import FirstRoundFinishChart from "./components/FirstRoundFinishChart";
import ReachAdvantageChart from "./components/ReachAdvantageChart";
import StanceMatchupTable from "./components/StanceMatchupTable";
import StrikingStyleWinRate from "./components/StrikingStyleWinRate";
import AgeCurveChart from "./components/AgeCurveChart";
import WinStreaksTable from "./components/WinStreaksTable";
import FightPaceChart from "./components/FightPaceChart";
import SplitDecisionChart from "./components/SplitDecisionChart";
import CountryStyleTable from "./components/CountryStyleTable";
import HomeCountryEffectCard from "./components/HomeCountryEffectCard";
import TitleInsights from "./components/TitleInsights";
import FastestFinishesTable from "./components/FastestFinishesTable";
import RivalriesTable from "./components/RivalriesTable";
import "./App.css";

export default function App() {
  const [overview, setOverview] = useState(null);
  const [stanceData, setStanceData] = useState([]);
  const [weightClassData, setWeightClassData] = useState([]);
  const [methodData, setMethodData] = useState([]);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    Promise.all([getOverview(), getStanceWinRate(), getWeightClasses(), getMethods()])
      .then(([ov, stance, wc, methods]) => {
        setOverview(ov);
        setStanceData(stance);
        setWeightClassData(wc);
        setMethodData(methods);
      })
      .catch((e) => setLoadError(e.message));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>UFC Fighter Stats</h1>
        <p className="muted">Fighter and fight data from ufcstats.com</p>
      </header>

      {loadError && (
        <div className="error-text">
          Couldn't load dashboard data: {loadError}. Is the backend running on port 8000?
        </div>
      )}

      <ChatPanel />

      <WorldMap />

      <FighterSearch />

      <div className="section-divider" />

      {overview ? <OverviewCards overview={overview} /> : !loadError && <GloveLoader label="Loading the card" />}

      <div className="chart-grid">
        <StanceChart data={stanceData} />
        <MethodChart data={methodData} />
        <FightsByYearChart />
        <FinishRateChart />
        <Leaderboard />
        <WeightClassChart data={weightClassData} />
      </div>

      <div className="chart-grid">
        <DivisionLeaderboard />
        <DivisionRankings />
        <TitleHistory />
      </div>

      <div className="section-divider" />

      <h2>More insights</h2>
      <div className="chart-grid">
        <ChampionshipRoundsFade />
        <ReachAdvantageChart />
        <AgeCurveChart />
        <FightPaceChart />
        <SplitDecisionChart />
        <HomeCountryEffectCard />
        <StanceMatchupTable />
        <StrikingStyleWinRate />
        <WinStreaksTable />
        <RivalriesTable />
        <FirstRoundFinishChart />
        <CountryStyleTable />
        <TitleInsights />
        <FastestFinishesTable />
      </div>

    </div>
  );
}
