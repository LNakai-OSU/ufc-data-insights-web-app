import { useEffect, useState } from "react";
import { getEventDetail, getFighterDetail } from "./api";

// Drives fighter<->event click-through (opponent name -> that fighter,
// event name -> that event's fight card, and back again) from a single
// piece of state, so FighterDetailCard/EventDetailCard don't need to know
// where they're being rendered (inline vs. in a Modal) or manage their
// own fetch lifecycle - the parent just renders `nav.data` for whichever
// `nav.view.type` is current. Navigating replaces the current view rather
// than stacking - there's no back button, clicking through just moves on.
export function useDetailNav() {
  const [view, setView] = useState(null); // { type: 'fighter' | 'event', id }
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!view) return;
    const fetcher = view.type === "fighter" ? getFighterDetail(view.id) : getEventDetail(view.id);
    fetcher
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [view]);

  function open(nextView) {
    setLoading(true);
    setData(null);
    setError(null);
    setView(nextView);
  }

  return {
    view,
    data,
    loading,
    error,
    openFighter: (id) => open({ type: "fighter", id }),
    openEvent: (id) => open({ type: "event", id }),
    close: () => setView(null),
  };
}
