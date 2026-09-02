"""Run: python -m birthplace_scrape.test_parsing"""
from .parsing import candidate_slugs, parse_birthplace, parse_country, slugify_name

# Real structure, copied from curl-fetched https://www.ufc.com/athlete/jon-jones
REAL_BIO_HTML = """
<div class="c-bio__info-details">
  <div class="c-bio__row--1col">
    <div class="c-bio__field">
      <div class="c-bio__label">Status</div>
      <div class="c-bio__text">Active</div>
    </div>
  </div>
  <div class="c-bio__row--1col">
    <div class="c-bio__field c-bio__field--border-bottom-small-screens">
      <div class="c-bio__label">Place of Birth</div>
      <div class="c-bio__text">Rochester, United States</div>
    </div>
  </div>
  <div class="c-bio__row--2col">
    <div class="c-bio__field c-bio__field--border-bottom-small-screens">
      <div class="c-bio__label">Trains at</div>
      <div class="c-bio__text">Team Jones</div>
    </div>
  </div>
</div>
"""

NO_BIRTHPLACE_HTML = """
<div class="c-bio__info-details">
  <div class="c-bio__field"><div class="c-bio__label">Status</div><div class="c-bio__text">Retired</div></div>
</div>
"""


def check(label, actual, expected):
    status = "OK" if actual == expected else "FAIL"
    print(f"[{status}] {label}: {actual!r} (expected {expected!r})")
    if actual != expected:
        raise AssertionError(label)


check("parse real bio HTML", parse_birthplace(REAL_BIO_HTML), "Rochester, United States")
check("missing field returns None", parse_birthplace(NO_BIRTHPLACE_HTML), None)

check("country from US birthplace", parse_country("Rochester, United States"), "United States")
check("country from international birthplace", parse_country("Dublin, Ireland"), "Ireland")
check("country from city-state-country", parse_country("Las Vegas, Nevada, United States"), "United States")
check("country from no-comma value", parse_country("Brazil"), "Brazil")
check("country from empty", parse_country(""), None)

check("simple slug", slugify_name("Jon", "Jones"), "jon-jones")
check("accented slug", slugify_name("José", "Aldo"), "jose-aldo")
check("slug with apostrophe", slugify_name("Conor", "McGregor"), "conor-mcgregor")
check("slug strips extra punctuation", slugify_name("B.J.", "Penn"), "b-j-penn")

check("no suffix - single candidate", candidate_slugs("Jon", "Jones"), ["jon-jones"])
check(
    "Jr. suffix - fallback without it",
    candidate_slugs("Michael", "Aswell Jr."),
    ["michael-aswell-jr", "michael-aswell"],
)
check(
    "III suffix - fallback without it",
    candidate_slugs("Ronnie", "Lawson III"),
    ["ronnie-lawson-iii", "ronnie-lawson"],
)

print("\nAll birthplace parsing checks passed.")
