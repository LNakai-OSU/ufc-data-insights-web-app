import EventDetailCard from "./EventDetailCard";
import FighterDetailCard from "./FighterDetailCard";
import GloveLoader from "./GloveLoader";

// Renders whatever `nav` (a useDetailNav() instance) currently points at -
// a fighter or an event - with its loading/error state. Presentational
// only, no Modal here: WorldMap wraps this in a Modal (its panel is too
// narrow for the full card), FighterSearch renders it inline in the space
// it already has.
export default function DetailView({ nav }) {
  if (!nav.view) return null;

  if (nav.loading) return <GloveLoader size="sm" />;
  if (nav.error) return <div className="error-text">{nav.error}</div>;
  if (!nav.data) return null;

  if (nav.view.type === "fighter") {
    return <FighterDetailCard fighter={nav.data} onSelectFighter={nav.openFighter} onSelectEvent={nav.openEvent} />;
  }
  return <EventDetailCard event={nav.data} onSelectFighter={nav.openFighter} />;
}
