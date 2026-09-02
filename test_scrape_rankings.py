"""Run: python test_scrape_rankings.py"""
from scrape_rankings import fetch_all_rankings_section, normalize_name, parse_rankings

FIXTURE_HTML = """
<div>Some Header</div>
All Rankings
<div class="view-grouping">
  <div class="view-grouping-header">Men's Pound-for-Pound<span>Top Rank</span></div>
  <div class="view-grouping-content">ignored</div>
</div>
<div class="view-grouping">
  <div class="view-grouping-header">Lightweight</div>
  <div class="view-grouping-content">
    <table><caption>
      <div class="rankings--athlete--champion">
        <div class="info"><h5><a href="/athlete/jon-jones">Jon Jones</a></h5><h6><span class="text">Champion</span></h6></div>
      </div>
    </caption>
    <tbody>
      <tr><td class="views-field views-field-weight-class-rank">1</td>
          <td class="views-field views-field-title"><a href="/athlete/x">Fighter One</a></td></tr>
      <tr><td class="views-field views-field-weight-class-rank">2</td>
          <td class="views-field views-field-title"><a href="/athlete/y">Fighter Two</a></td></tr>
    </tbody>
    </table>
  </div>
</div>
All Meta Rankings
<div class="view-grouping">
  <div class="view-grouping-header">Lightweight</div>
  <div class="view-grouping-content">should not be parsed</div>
</div>
"""


def check(label, actual, expected):
    status = "OK" if actual == expected else "FAIL"
    print(f"[{status}] {label}: {actual!r} (expected {expected!r})")
    if actual != expected:
        raise AssertionError(label)


check("normalize accented", normalize_name("Jiří Procházka"), "Jiri Prochazka")
check("normalize curly apostrophe", normalize_name("Lone’er Kavanagh"), "Lone'er Kavanagh")
check("normalize Polish l-stroke", normalize_name("Jan Błachowicz"), "Jan Blachowicz")
check("normalize collapses whitespace", normalize_name("A   B"), "A B")

section = fetch_all_rankings_section(FIXTURE_HTML)
check("section excludes Meta Rankings content", "should not be parsed" in section, False)

rankings = parse_rankings(section)
check("P4P division skipped", any(r["weight_class"].startswith("Men's Pound") for r in rankings), False)
check("champion + 2 contenders parsed", len(rankings), 3)
check("champion is rank 0", rankings[0], {"weight_class": "Lightweight", "rank": 0, "fighter_name": "Jon Jones"})
check("contender ranks", [r["rank"] for r in rankings[1:]], [1, 2])

print("\nAll rankings scraper checks passed.")
