# biotech-tracker

A tracker for the biotech industry, built to answer three questions:

1. **How are biotech startups built?** Where the founders come from, who funds and incubates them, and whether they start as a platform or around a single asset.
2. **Which biological silos produce companies?** The scientific areas (modalities, platforms, disease areas) where new companies keep appearing, and why.
3. **Who is moving in from outside?** Recent news, plus tech companies expanding into life sciences.

## Layout

```
biotech-tracker/
├── README.md               this file
├── taxonomy/
│   └── silos.md            the biological silos and how companies come out of them
├── data/
│   ├── companies.csv       startups / biotechs (one row per company), hand-checked
│   ├── universe.csv        every biotech/pharma company from bulk sources (machine-built)
│   ├── pharma/             one JSON per big pharma: profile + family-tree events (Pharma families tab)
│   ├── products.csv        what smaller companies make (product, lead asset, stage, source)
│   ├── coverage.csv        articles reporting each news event (event pages)
│   ├── aliases.csv         hand-kept alternative names (e.g. ModernaTX → Moderna) for merging duplicates
│   ├── tech_entrants.csv   tech companies' moves into life sciences
│   ├── builders.csv        venture studios & investors that create companies
│   └── news.csv            dated news log (financings, M&A, launches, readouts)
└── notes/                  free-form research notes, one file per topic/week
```

## Conventions

- **Every row needs a `source` URL and a `last_verified` date (YYYY-MM-DD).** Use `TODO` when a value hasn't been checked yet. Don't guess.
- `silo` values should match the IDs in `taxonomy/silos.md` (e.g. `gene-editing`, `ai-discovery`). Separate multiple values with `;`.
- `origin` (how the company was formed) is one of: `academic-spinout`, `studio-built`, `big-tech-spinout`, `pharma-spinout`, `founder-led`, `unknown`.
- `model` is one of `platform`, `asset`, `hybrid`, `tools`, `services`.
- News goes in `news.csv`, newest first. If a news item changes a company's facts, update `companies.csv` as well.

## Questions to answer as the data grows

- Which silos get the most new companies per year, and which are drying up?
- What share of companies are studio-built (Flagship, ARCH, Third Rock…) versus academic spinouts?
- Which universities and labs produce the most founders, broken down by silo?
- Where is tech capital (Alphabet, NVIDIA, OpenAI, Anthropic, Microsoft, Amazon) going, and is it building, partnering or investing?

## Seed data status

- **2026-10-15 web sweep:** `news.csv` now covers March to October 2026. The new and updated rows in `companies.csv` and `tech_entrants.csv` have sources and `last_verified=2026-10-15`. Several of these come only from secondary coverage or trackers, and their `notes` say so.
- The original seed rows still have `last_verified=TODO`. They came from model knowledge, so check them before relying on them.
- Gap: Microsoft and Meta had no 2026 life-sciences moves in the sweep. Search them directly.

## Front end

Run `python3 web/build.py`, then open `web/index.html` in a browser. It needs no server. Rebuild whenever the CSV files change. The daily sweep rebuilds it automatically.

## Confirmation

The `confirmed_by` column in `news.csv` lists the free trackers (BioBucks, Cure, Fierce) that independently list each event. The front end counts the primary `source` plus these trackers and labels each event as 2+ sources, single source or no source.

## Leads

`sweep/collect_leads.py` gathers smaller announcements from newswire RSS feeds, Google News, SEC Form D filings and Bluesky into `data/leads.csv`. These are unconfirmed. The daily sweep checks each lead and marks it `promoted`, `known` or `rejected`. Edit `sweep/lead_sources.json` to change feeds, search terms or Bluesky accounts. Credentials go in `sweep/.env` (see `.env.example`).

## All companies (universe)

`sweep/build_universe.py` builds `data/universe.csv` from ClinicalTrials.gov industry sponsors, Wikidata (industry = biotech or pharma), SEC EDGAR (listed companies with SIC 2834/2835/2836/8731) and SEC Form D data sets (biotech/pharma raises, last 12 quarters). It merges name variants, always includes every `companies.csv` row and marks those rows `curated=yes`. The rows are not checked by hand. The SEC sources are skipped unless `SEC_USER_AGENT` is set in `sweep/.env`. The sweep rebuilds this file every Monday. The front end's **Companies** tab lists it and sorts by estimated size, news coverage, recent activity, trial count or name. Size is estimated from Wikidata headcount, trial count or the last Form D raise, whichever is largest on a shared log scale. Each company opens a profile page (`index.html#co/<id>`) that brings together the hand-checked details, news, tech-company moves, builders, unconfirmed leads and links. It also loads the company's latest trials live from ClinicalTrials.gov. `web/build.py` links companies to news and leads by name, so a common name can occasionally match the wrong company.

### Duplicates and names

When several sources name the same company differently, the builder merges them into one row. It uses Wikidata's alternative names for each company plus `data/aliases.csv`, a file you maintain for cases Wikidata misses (`alias,canonical,note`). A merged company shows its main name (the registered or trial-registry name) with its common name in parentheses, for example **ModernaTX, Inc. (Moderna)** or **GlaxoSmithKline (GSK)**. Other spellings are listed on the profile under "Also listed as". If you spot a duplicate, add a line to `aliases.csv` and run `python3 sweep/build_universe.py --cached && python3 web/build.py`. `--cached` reuses the raw downloads in `sweep/cache/`, so the rebuild takes seconds.

### Logos

`sweep/fetch_logos.py` downloads each company's official logo from Wikimedia Commons, using Wikidata's "logo image" property. It keeps SVG files only, removes scripts and external links, and strips full-size white backgrounds so each logo is transparent. The files are saved as `web/logos/<wikidata id>.svg`. Companies without an SVG logo, including most startups and every company whose Commons logo is PNG or JPG, get a generated initials badge drawn in the page itself. Commons throttles bulk downloads, so the first run is slow. Later runs, including the Monday sweep, fetch only logos that aren't on disk yet. Logos are trademarks of their owners and are shown here only to identify each company.

## Pharma families

`data/pharma/<slug>.json` holds one file per big pharma (the 15 largest by revenue). Each file has:
- `profile`: HQ, CEO, revenue, employees, top products, therapeutic areas, venture arm and sources.
- `events`: a list where each event has `year, type, counterparty, via, result, value_usd, status, description, source`.

`type` is one of acquisition, merger, spin-off, divestiture, joint-venture, stake, venture-arm, rename or founding. `via` names the acquired company the event happened under (Pharmacia's merger with Upjohn, for example, appears under Pfizer with `via: Pharmacia`). `status` is completed, pending or terminated. The **Pharma families** tab draws each company as a timeline tree:
- Acquisitions join the trunk from above, carrying their own earlier history.
- Spin-offs and sales leave below.
- Abandoned deals stop short of the trunk and don't count toward totals.

The data was researched on 2026-10-19 from company releases, SEC filings, trade press and Wikipedia, and every event has a source link. Revenue for Roche, Sanofi, GSK and Novo Nordisk is converted from CHF, EUR, GBP or DKK at approximate 2025 rates. Some values are blank where no source confirmed them.

## Silo pages

Every silo name in the front end links to its page (`index.html#silo/<id>`). The page shows:
- the silo's definition from `taxonomy/silos.md`: enabling discovery, typical origin and notes;
- event count, disclosed value, the mix of event types and a monthly activity chart;
- every event tagged with the silo;
- the companies in it: tagged by hand in `companies.csv`, involved in its news, or whose product line in `products.csv` names the modality (matched by keyword, so check before relying on it);
- the builders focused on it, and the tech companies moving into it.

To add or rename a silo, edit the tables in `taxonomy/silos.md` and rebuild.

## Builder profiles

`data/builders/<slug>.json` holds one file per company builder: a `profile` (type, HQ, founding, founders, leadership, AUM, latest fund, how it builds companies, sources) and a `companies` list. Each company has `name, launched, silo, product, status, outcome, outcome_value_usd, source`. The file is merged onto the matching `builders.csv` row by name. The Ventures tab shows a card per venture builder, and each opens a profile page (`index.html#bd/<slug>`) with its track record, launches per year, silo mix and every company it built.

The data was researched on 2026-10-19. Some entries carry flags:
- `outcome_unverified`: the exit details came from the researcher's memory, not a fetched page. This covers many older Flagship and ARCH exits.
- `founding_unconfirmed`: sources confirm an investment, but not that the builder founded the company.

The page labels both. Check them before relying on them.

## Labs and investors with life-science arms

- `data/labs/<slug>.json`: one file per academic source of spinouts (12 so far: Broad, MIT, Harvard & Wyss, Dana-Farber, Penn, Oxford, Stanford, UCSF, UC Berkeley & IGI, UW Institute for Protein Design, Caltech, Cambridge). Each file has a `profile` (tech-transfer office, programs), `labs` (PI, lab, what it's known for, silos) and `spinouts` (year, founding PI, silo, product, co-founding builder, status, outcome, source). The **Labs** tab shows them, and each opens a page at `index.html#lab/<slug>`.
- `data/investors/<slug>.json`: one file per generalist or tech investor with a dedicated life-science arm (8 so far: a16z Bio + Health, GV, General Catalyst, Thrive, Khosla, Lux, NEA, NVentures). Each file has a `profile` and `companies`, where each company records the investor's `role` (co-founded, led or participated). They appear in the "Investors with life-science arms" section of the **Ventures** tab, and each opens a page at `index.html#iv/<slug>`.

Both were researched on 2026-10-19. The shared web-search limit ran out partway through, so many years, statuses and deal values are blank rather than guessed. Blank statuses show as "Status unknown". Flags mark uncertain entries:
- `origin_unconfirmed`: the science may come from an affiliated institution.
- `founding_unconfirmed` and `builder_unconfirmed`: co-founding wasn't confirmed.
- `outcome_unverified`: exit details weren't checked.

Silo pages and company profiles link to the labs and investors involved.

## Clinical trials

`sweep/fetch_trials.py` takes a snapshot of ClinicalTrials.gov into `data/trials.json`. It covers interventional drug, biologic and genetic studies in phases 1–3 that reached a milestone in the last 90 days: newly registered, results posted, primary completion, or stopped (terminated, suspended or withdrawn, with the reason given). The registry's lead-sponsor class decides whether a trial counts as **industry** or **academic & government** (universities, hospitals, NIH, cooperative groups).
- **Linking:** `web/build.py` links industry sponsors to their company profiles, and academic sponsors to their Labs page, affiliated hospitals included.
- **Silos:** these come from intervention and condition wording, so trials of plain-named small molecules mostly go untagged.
- **Updates:** the daily sweep refreshes the snapshot.
- **Where it shows:** the **Trials** tab, plus trial sections on Labs and silo pages.

## Forecast (deal predictor)

The **Forecast** tab is a signal-based forecast, not a trained model. Each score is a plain sum of named, capped signals taken from the tracker's own data, and every row lists the signals behind it. The weights are in the `W` object in `web/template.html`. It has four parts:
1. **Likely acquisition targets.** Signals: late-stage programs, recent results, approved products, existing pharma partnerships, how active the silo is in M&A, funding momentum, backers, and listing status. Stopped trials count against. Big pharma, companies that are themselves acquirers, already-acquired companies and known subsidiaries are excluded.
2. **Likely buyers for each target.** Each of the 15 pharma families is scored on therapeutic-area overlap, activity in the target's silo, recent deal pace and any existing partnership.
3. **Likely platform partnerships.** Platform and AI companies with funding momentum, paired with the pharmas doing platform deals.
4. **Academia → industry.** Phase 2/3 academic trials of the institution's own agents that just posted results or completed are listed as licensing candidates. Labs are ranked by their recent spinout pace and trial activity.

The page shows a backtest: the target score is run on the news log's actual acquisitions, with each deal itself removed. Results so far are modest: a median 60th-percentile rank, and 3 of 16 in the top 25%. The score has no financial data, so treat it as a way to explore, not a forecast.
