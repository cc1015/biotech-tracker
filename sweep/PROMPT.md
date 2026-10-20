You are running the daily news sweep for the biotech biotech-tracker in the current directory. Nobody is watching, so finish the whole job in one go.

## 1. Orient
- Read `README.md` and `taxonomy/silos.md` for conventions and silo IDs.
- Read `data/news.csv`. The newest `date` in it tells you where the last sweep stopped. Cover everything from that date up to today. If that's more than 14 days, cover the last 14 days only.

## 1b. Collect and triage leads
Run `python3 sweep/collect_leads.py`. It adds unconfirmed leads from newswires, Google News, SEC Form D filings and Bluesky to `data/leads.csv`. Then handle every row with `status=new`:
- If the event is already in `news.csv`, set `status=known`.
- If it's a real biotech or life-sciences event of the kind this tracker records, confirm it against a primary source (and the trackers, see 3b), add it to `news.csv`, then set `status=promoted`.
- Otherwise set `status=rejected` and give a short reason in `notes`, for example "not biotech", "people move", "opinion piece" or "duplicate story".
Several stories often cover the same event. Promote it once and mark the others `known`.
Form D filings mostly show small, quiet raises. If no press release exists, promote one anyway if it's ≥$5M, with the EDGAR link as `source` and "Form D only" in `notes`.

## 2. Search
Steps 1b and 2 overlap. Use these searches to fill gaps the leads missed.
Run web searches for the window, sending several in parallel:
- biotech venture financings (seed through Series F, crossover rounds)
- biotech IPOs
- biopharma M&A
- licensing and partnership deals over $500M headline value
- AI drug discovery and bio foundation-model companies: financings, deals and launches
- life-sciences moves by tech companies: Alphabet/Isomorphic/DeepMind, NVIDIA, Microsoft, Amazon/AWS, Meta, OpenAI, Anthropic, Apple
- new company launches from venture studios (Flagship, ARCH, Third Rock, Atlas, Foresite)

Prefer primary sources (company press releases, Business Wire, PR Newswire) and trade press (Fierce Biotech, Endpoints, BioSpace, STAT, BioPharma Dive, BioCentury). Use trackers only to find leads, then confirm each one elsewhere.

## 3. Record
- Add each new event to `data/news.csv` and keep the file sorted newest first. Columns: `date,headline,companies,category,silo,amount_usd,source,confirmed_by,notes`.
  - `category` is one of: financing, ipo, m&a, partnership, launch, clinical, regulatory.
  - `silo` uses IDs from `taxonomy/silos.md`, separated by `;`.
  - Skip duplicates. Check the companies and the event, not just the headline text.
- **Include an event only if you have a source URL for it.** Don't fabricate. If you have just one secondary source, add the event anyway and write "single secondary source — verify" in `notes`.
- If a company that isn't in `data/companies.csv` raises $50M or more, launches out of a studio, or is an AI or tech-adjacent biotech, add it. Use `TODO` for any value you couldn't verify. Set `last_verified` to today.
- Add a row to `data/tech_entrants.csv` for each life-sciences move by a tech company.
- If an event changes facts about an existing company (new round, acquired, IPO), update that company's row.
- Quote any field that contains a comma. Use `;` inside fields wherever you can.
- **Source of record:** `source` should be the primary announcement for that specific event (press release, newswire or SEC filing). Use a tracker's page only if nothing else exists, because tracker pages don't link to the individual event.
- **Coverage:** for each new event, add 2–5 rows to `data/coverage.csv`: the primary announcement plus trade-press articles about that specific event. Columns: `event_date,event_headline,url,outlet,title,published,kind,summary,last_verified`. `event_date` and `event_headline` must match the `news.csv` row exactly. `kind` is one of press-release, filing, trade-press, news, tracker. `summary` is 1–2 sentences in your own words (40 words max). Never copy sentences from the article. Fetch every URL and confirm it covers this exact event before adding it.
- **Pharma families:** if an event involves one of the companies in `data/pharma/` (acquisition, merger, spin-off, sale, venture-arm news), add it to that company's `events`, or update an existing one, for example from pending to completed. Use the same fields and give the event a `source`.
- **Builders:** if a new event involves a company that one of the builders in `data/builders/` created, or a builder launches a new company, update that builder's `companies` list (status, outcome, value) with a `source`.
- **Labs and investors:** if a new company is a spinout of an institution in `data/labs/`, add it to that file's `spinouts`. If an investor in `data/investors/` leads or joins a round, add or update the company in its `companies` list. Give every entry a `source`, and update `status`/`outcome` when a known company IPOs, is acquired or shuts down.
- **Products:** for each smaller company or startup in a new event that has no row in `data/products.csv`, add one: `name,product,lead_asset,modality,stage,source,last_verified,notes`. `product` is a plain-English line of 20 words or fewer on what they make or their lead program. Take it from the company's own site or a press release, and use `TODO` for anything you can't confirm. Skip big pharma and big tech.

## 3b. Cross-check against the free trackers
Use these trackers as independent sources, separate from the primary `source`. Fetch each one with WebFetch. Pages are long, so read on with `offset`.
- BioBucks financings: https://www.biobucks.co/biotech-vc-funding-tracker-2026
- BioBucks M&A: https://www.biobucks.co/biotech-ma-tracker-2026
- BioBucks licensing & partnering: https://www.biobucks.co/biotech-bdl-tracker-2026
- Cure financings: https://wewillcure.com/insights/news/funding-and-models/biotech-venture-funding-tracker
- Cure AI drug discovery: https://wewillcure.com/insights/news/ai-and-machine-learning/ai-drug-discovery-venture-funding-tracker-2026
- Fierce Biotech fundraising tracker: https://www.fiercebiotech.com/biotech/fierce-biotech-fundraising-tracker-26 (blocks fetches. Count it only if a search result shows the item in it.)

For every event in the window, and for any older event whose `confirmed_by` is empty:
- Add each tracker that independently lists the event to `confirmed_by`, separated by `;` (`BioBucks`, `Cure`, `Fierce`).
- If the trackers disagree with the row on date or amount, keep the primary-source value and record the difference in `notes`.
- If an event appears only in a tracker, you may add it with the tracker as `source`. Write "Tracker-only; primary source TODO" in `notes` and try to find the primary source.

## 4. Validate
Run this and fix every file that isn't `ok`:
```
python3 -c "import csv,glob
for f in sorted(glob.glob('data/*.csv')):
    rows=list(csv.reader(open(f))); n=len(rows[0]); bad=[i for i,r in enumerate(rows) if len(r)!=n]
    print(f,len(rows)-1,'rows','BAD:'+str(bad) if bad else 'ok')"
```

Then rebuild the front end with `python3 web/build.py`.

## 5. Summarize
Write `notes/sweep-YYYY-MM-DD.md` (today's date) with:
- the window covered and how many rows you added or updated in each file
- 3–6 bullets on patterns: which silos are hot, how companies are being built (studio-built or academic spinout; built around a platform or a single drug), and what tech companies are doing
- items you couldn't verify, and gaps to follow up on
