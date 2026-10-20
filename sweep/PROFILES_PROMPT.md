You are running the monthly profile check for the biotech-tracker in the current directory. Nobody is watching, so finish the whole job in one go.

The daily sweep adds events but never re-checks the profile facts in `data/pharma/`, `data/builders/`, `data/investors/` and `data/labs/`. Your job is to find which of those facts have gone out of date and fix them. Don't add events, companies or spinouts; the daily sweep does that.

## 1. Orient
- Read `docs/conventions.md` (sections "Pharma families", "Builder profiles" and "Labs and investors") for what each field means.
- Read the latest `notes/profiles-*.md`, if any, to see what last month's check changed and left open.

## 2. Check each file
Go through every file in the four folders. Search for recent news on each organization, sending several searches in parallel. Check these fields:
- **Pharma** (`profile`): `ceo` and `ceo_since`, `hq`, `ticker`, `revenue_usd` and `revenue_year` (from the latest full-year results), `employees` and `employees_year`, `top_products` (still the top sellers?), `therapeutic_areas`, `venture_arm`.
- **Builders and investors** (`profile`): `leadership` (departures, new partners), `latest_fund` (a newer or larger fund closed?), `aum_usd`, `hq`, `website`.
- **Labs**: in `profile`, `tech_transfer`, `tech_transfer_url` and `programs`. In `labs`, whether each PI is still at that institution and still runs that lab. If a PI moved, retired or died, update `lab` and `known_for` to say so (for example "moved to Stanford in 2026"). Don't delete the entry.

Rules:
- **Change a value only when a source says it changed.** Prefer the organization's own site, press release, annual report or SEC filing, then trade press. Never change a value from memory, and never guess. If sources disagree, keep the current value and note the disagreement in the changelog.
- Add each new source URL to that profile's `sources` list.
- Set `profile.last_verified` to today's date on every file you checked, whether or not anything changed.
- Keep each file's existing structure, key order and formatting. Convert non-USD revenue to USD at an approximate current rate and say which rate in the changelog.
- If a fact can't be checked this month (a page is blocked, search finds nothing), leave it and list it in the changelog.

## 3. Validate
Run this and fix every file it reports:
```
python3 -c "import glob,json
for f in sorted(glob.glob('data/**/*.json', recursive=True)):
    try: json.load(open(f))
    except Exception as e: print(f, e)"
```
Then rebuild the front end with `python3 web/build.py`.

## 4. Write the changelog
Write `notes/profiles-YYYY-MM.md` (this year and month) with:
- every change, one line each: file, field, old value → new value, source URL
- how many files you checked in each folder, and how many had changes
- facts you couldn't check, and disagreements between sources
