# Profile check — 2026-11 (run 2026-11-03)

First monthly profile check, so there was no earlier `notes/profiles-*.md` to build on. All 40 files now have `profile.last_verified: "2026-11-03"`; this key is new in every file and was added right after `profile.sources`. Every new source URL below was also added to that file's `profile.sources`.

## Summary

| Folder | Files checked | Files with changes |
|---|---|---|
| data/pharma | 15 | 8 |
| data/builders | 5 | 3 |
| data/investors | 8 | 3 |
| data/labs | 12 | 12 |
| **Total** | **40** | **26** |

The checks ran through web search, and the search quota ran out partway through. See "Couldn't check" below.

## Currency conversions

New non-USD values use the same FY2025 average rates already used in each file, so a product list doesn't mix rates. That differs from the "approximate current rate" instruction. Recent spot rates (Aug 2026: EUR/USD 1.153, USD/JPY ~163) would make one list's entries hard to compare.
- **Sanofi:** EUR at 1.13 USD/EUR, the file's existing rate.
- **GSK:** GBP at 1.31 USD/GBP, GSK's own stated FY2025 average in its FY2025 results 6-K. Existing GSK values imply roughly 1.32–1.335 and were left alone. Revenue £32,667m at 1.31 would be $42.79B, against $43.12B stored. Reconcile the rate across the file at some point.
- **Takeda:** JPY at ~153.7 JPY/USD, the rate implied by the file's stored revenue.

## Changes

### Pharma
- **astrazeneca.json** `ticker`: `LSE:AZN` → `LSE:AZN; NYSE:AZN`. Ordinary shares began trading on the NYSE on 2 Feb 2026, and the Nasdaq ADSs were delisted. Source: https://www.astrazeneca.com/media-centre/press-releases/2026/astrazeneca-begins-trading-on-NYSE.html
- **astrazeneca.json** `employees`: 89900 → 96100 (year-end 2025). Source: https://www.sec.gov/Archives/edgar/data/901832/000110465926019130/azn-20251231x20f.htm
- **astrazeneca.json** `top_products`, re-ranked by FY2025 Total Revenue. Source: https://data.fca.org.uk/artefacts/NSM/RNS/59563de3-5a71-4031-9f0b-61dfc61dc769.html
  - Old: Tagrisso 7.25B, Imfinzi 6.06B, Enhertu 2.78B, Farxiga null, Ultomiris null, Calquence null.
  - New: Farxiga 8,492M, Tagrisso 7,254M, Imfinzi 6,063M, Ultomiris 4,718M, Calquence 3,518M, Lynparza 3,279M. Enhertu (2,775M) drops out.
- **gilead.json** `top_products`, re-ranked by FY2025 revenue. Source: https://www.gilead.com/news/news-details/2026/gilead-sciences-announces-fourth-quarter-and-full-year-2025-financial-results
  - Old: Biktarvy null, Descovy null, Veklury 4.5B (2021), Trodelvy null, Yescarta null, Livdelzi null.
  - New: Biktarvy 14,334M, Descovy 2,758M, Genvoya 1,498M, Yescarta 1,495M, Trodelvy 1,397M, Epclusa 1,272M.
  - Veklury was $911M in 2025, about 9th. Livdelzi isn't disclosed separately ("Other Liver Disease" was $874M).
- **gsk.json** `top_products`, completed and re-ranked by FY2025 sales. Source: https://www.sec.gov/Archives/edgar/data/1131399/000165495426000892/a5979rv2.htm
  - Dovato: null → 3,508M (£2,678m).
  - Nucala: null → 2,630M (£2,008m).
  - Arexvy (790M, about 9th) → Benlysta 2,323M (£1,773m).
  - Meningitis vaccines unchanged at 2.11B, now 6th.
- **jnj.json** `top_products[5]`: Carvykti 1,887M → Imbruvica 2,823M. Carvykti ranks about 11th in FY2025. Source: https://www.investor.jnj.com/investor-news/news-details/2026/Johnson--Johnson-reports-Q4-and-Full-Year-2025-results/ (already in sources)
- **merck.json** `top_products[3–5]`, re-ranked by FY2025 revenue. Source: https://www.merck.com/news/merck-highlights-progress-advancing-broad-diverse-pipeline/
  - Old: Bridion 1.8B, Winrevair 1.4B, Capvaxive 759M.
  - New: ProQuad/M-M-R II/Varivax 2,451M, Bridion 1.8B, Lynparza (alliance revenue) 1,450M.
  - Winrevair, at 1,443M, is essentially tied with Lynparza.
- **novartis.json** `top_products[5]`: Pluvicto 1,994M → Jakavi 2,110M. Source: https://www.sec.gov/Archives/edgar/data/1114448/000111444826000007/a260204-99_1.htm
- **novartis.json** `employees` / `employees_year`: 75883 / 2024 → 75267 / 2025 (FTE, 31 Dec 2025). Source: https://www.sec.gov/Archives/edgar/data/0001114448/000111444826000004/nvs-20251231.htm
- **sanofi.json** `top_products[5]`: ALTUVIIIO 1,310M (€1,160M) → Toujeo 1,520M (€1,345M). Source: https://www.sec.gov/Archives/edgar/data/1121404/000112140426000001/pressreleaseq42025english.htm
- **sanofi.json** `employees` / `employees_year`: 82878 / 2024 → 74846 / 2025. The drop follows the 2025 Opella sale. Source: https://www.blog-rh.com/recrutement-sanofi/, which cites the 2025 Universal Registration Document; Contract Pharma reports the same figure.
- **sanofi.json** `venture_arm.fund_size_usd`: null → 1400000000, the evergreen fund's total after a $625M top-up in Sep 2025. Source: https://globalventuring.com/corporate/fundraising/sanofi-ventures-boosts-fund-to-1-4bn/
- **takeda.json** `top_products` Entyvio: null → 6,230M (¥958.0B, FY2025 ending 31 Mar 2026). Source: https://www.sec.gov/Archives/edgar/data/0001395064/000139506426000177/tak-20260331.htm
- **takeda.json** `top_products` Takhzyro: null → 1,460M (¥223.9B). Same source.

### Builders
- **arch.json** `leadership`: "Mark McDonnell — Managing Director" → "Mark McDonnell — Managing Director, CFO & CAO". Source: https://www.archventure.com/team/
- **foresite.json** `leadership`: "Vikram Bajaj — Co-founder & CEO, Foresite Labs; Managing Director, Foresite Capital" → "Vikram Bajaj — Co-founder, Foresite Labs; Advisor, Foresite Capital". He stepped down as Labs CEO in Feb 2026. Source: https://www.foresitecapital.com/team/
- **foresite.json** `leadership`: "Jim Tananbaum — Founder & CEO, Foresite Capital" → "Jim Tananbaum — Founder & CEO, Foresite Capital; Co-founder & CEO, Foresite Labs". Source: https://www.biocentury.com/article/660586/ai-exec-reis-filho-leaves-astrazeneca-for-strategy-role-at-foresite-labs
- **thirdrock.json** `leadership`: "Mark Levin — Founding Partner" → "Mark Levin — Retired Founding Partner". Source: https://www.thirdrockventures.com/people/mark-levin
- **thirdrock.json** `leadership`: "Kevin Starr — Founding Partner" → "Kevin Starr — Retired Founding Partner". Source: https://www.thirdrockventures.com/people/kevin-starr

### Investors
- **a16z-bio.json** `leadership`: "Julie Yoo — Bio + Health team member (title not confirmed)" → "Julie Yoo — General Partner, Bio + Health (healthcare access, payment and patient experience)". Source: https://a16z.com/author/julie-yoo/
- **lux.json** `latest_fund.name`: "Lux Capital Fund IX" → "Lux Ventures IX". The size ($1.5B) and year (2026) are unchanged. Source: https://www.sidley.com/en/newslanding/newsannouncements/2026/01/sidley-advises-lux-capital-on-new-vc-fund-lux-ix
- **lux.json** `aum_usd`: null → 7000000000 ("over US$7 billion"). Same source.
- **nventures.json** `leadership`: [] → ["Mohamed \"Sid\" Siddeek — Corporate Vice President, NVIDIA; Head of NVentures"]. Source: https://globalventuring.com/people/powerlist-2026-mohamed-siddeek-nventures/

### Labs
- **berkeley.json** Patrick Hsu `lab`: "Hsu Lab, Bioengineering (Arc Institute co-founder)" → "…; moved to Stanford (Pathology) in 2026". `known_for` gets "; moved to Stanford in 2026". Sources: https://profiles.stanford.edu/patrick-hsu, https://arcinstitute.org/labs/hsulab
- **berkeley.json** Carolyn Bertozzi `lab`: "Chemistry" → "Chemistry; moved to Stanford in 2015". `known_for` gets the same note. Source: https://chemh.stanford.edu/news/carolyn-bertozzi-join-chem-h-department-chemistry
- **broad.json** Stuart Schreiber `lab`: "Chemical Biology Program" → "…; now Founding Core Institute Member Emeritus (led Arena BioWorks, which closed Nov 2025)". Sources: https://www.broadinstitute.org/bios/stuart-l-schreiber, https://www.statnews.com/2025/11/04/arena-bioworks-research-institute-shuts-down/
- **broad.json** Meyerson / Garraway `lab`: "Cancer Genomics (Broad / Dana-Farber)" → "…; Garraway left for industry (Lilly, then Roche CMO from 2019)". Source: https://www.biospace.com/roche-s-sandra-horning-to-retire-eli-lilly-s-levi-garraway-tapped-to-fill-her-shoes
- **broad.json** Sekar Kathiresan `lab`: "Cardiovascular Disease Initiative" → "…; left for Verve Therapeutics in 2019". Source: https://en.wikipedia.org/wiki/Sekar_Kathiresan (Wikipedia only)
- **caltech.json** David Baltimore `lab`: "Biology (Baltimore Lab)" → "…; died September 2025". `known_for` gets "; died 2025". Source: https://www.bbe.caltech.edu/news/caltech-mourns-the-passing-of-president-emeritus-and-nobel-laureate-david-baltimore
- **caltech.json** Mark E. Davis `lab`: "Chemical Engineering (Davis Lab)" → "…; emeritus since 2023". Source: https://directory.caltech.edu/personnel/mdavis
- **cambridge.json** Greg Winter `lab`: "MRC Laboratory of Molecular Biology; Trinity College" → "…; LMB emeritus, Master of Trinity until 2019". Source: https://mrclmb.ac.uk/research-leaders/
- **cambridge.json** Steve Jackson `lab`: "Gurdon Institute (CRUK Laboratories)" → "…; moved to CRUK Cambridge Institute in 2022". Source: https://www.stevejacksonlab.org/edit-news/2022/9/1/its-the-end-of-an-era-the-jackson-lab-is-moving
- **cambridge.json** Blundell & Abell `lab`: "Department of Biochemistry / Department of Chemistry" → "…; Abell died 2020, Blundell emeritus". Sources: https://www.cam.ac.uk/research/news/professor-chris-abell-frs-fmedsci-1957-2020, https://royalsociety.org/people/tom-blundell-11101
- **cambridge.json** Henderson & Tate `lab`: "MRC Laboratory of Molecular Biology, Structural Studies" → "…; Henderson emeritus". Tate is still a group leader. Source: https://mrclmb.ac.uk/research-leaders/
- **cambridge.json** Jason Chin `lab`: "MRC Laboratory of Molecular Biology" → "…; moved to Ellison Institute of Technology, Oxford in 2025". `known_for` gets "; moved to Oxford (EIT) in 2025". Source: https://mrclmb.ac.uk/research-leaders/jason-chin/
- **dana-farber.json** Nathanael Gray `lab`: "Department of Cancer Biology" → "…; moved to Stanford in 2020". Source: https://en.wikipedia.org/wiki/Nathanael_Gray (Wikipedia only; already in sources)
- **harvard.json** Douglas Melton `lab`: "Harvard Stem Cell Institute" → "…; left for Vertex Pharmaceuticals in 2022". `known_for` gets "; joined Vertex in 2022". Source: https://en.wikipedia.org/wiki/Douglas_Melton (Wikipedia only, because the HSCI page returned 403; already in sources)
- **mit.json** Phillip Sharp `lab`: "Sharp Lab, Koch Institute" → "…; lab closed (Sharp now Institute Professor & Professor of Biology Emeritus)". Source: https://biology.mit.edu/profile/phillip-a-sharp/
- **oxford.json** Graham Richards `lab`: "Department of Chemistry" → "…; died February 2025". Source: https://www.chem.ox.ac.uk/node/4306861
- **penn.json** Jean Bennett `lab`: "Department of Ophthalmology" → "…; emerita (F.M. Kirby Emeritus Professor), still co-directs CAROT". Source: https://www.nasonline.org/directory-entry/jean-bennett-2net24/
- **stanford.json** James Spudich `lab`: "Department of Biochemistry" → "…; emeritus since 2022". Source: https://profiles.stanford.edu/james-spudich
- **stanford.json** Stephen Quake `lab`: "Bioengineering / Applied Physics" → "…; on leave Oct 2026–Jun 2027". Source: https://profiles.stanford.edu/stephen-quake
- **stanford.json** Isabella Graef `lab`: "School of Medicine (SPARK)" → "…; former faculty, now CEO of Shenandoah Therapeutics". Source: https://sparkmed.stanford.edu/fda-approves-drug-developed-through-spark/ (already in sources)
- **ucsf.json** William J. Rutter `lab`: "Biochemistry & Biophysics" → "…; died July 2025". Source: https://www.ucsf.edu/news/2025/07/430346/ucsf-mourns-loss-of-william-j-rutter
- **ucsf.json** Hani Goodarzi `lab`: "Goodarzi Lab, Biochemistry & Biophysics" → "…; lab relocated to Arc Institute in 2023 (keeps UCSF appointment)". Source: https://www.ucsf.edu/news/2023/09/426191/ai-cancer-arc-institute-supports-curiosity-driven-science-ucsf
- **uw-ipd.json** Lance Stewart `lab`: "IPD Translational Investigator Program" → "…; retiring from IPD (announced Nov 2025)". Source: https://rosettacommons.org/2025/11/24/neil-king-named-deputy-director-of-uws-institute-for-protein-design/
- **uw-ipd.json** `profile.tech_transfer_url`: "" → "https://comotion.uw.edu/". Source: https://comotion.uw.edu/

Many lab changes record moves from before 2025, such as Bertozzi (2015), Gray (2020) and Melton (2022). The original research never captured them, so the files said these PIs were still in place.

## Disagreements between sources (current value kept unless noted)

- **takeda.json `employees`** (kept 49095 / 2023):
  - FY2025 20-F: "approximately 47,000".
  - Takeda's June 2026 factsheet: "approx. 50,000".
  - Yahoo: 47,455.
  - Two Takeda sources conflict, so I left the value. It should still be updated, since 2023 is stale.
- **astrazeneca.json `employees`:** some aggregators still show 89,900, which is the 2023 year-end figure. I used the 20-F's 96,100.
  - The 20-F figure came from search snippets; the filing was too large to fetch.
- **sanofi.json `employees`:** one aggregator shows 74,193. I used 74,846, which two sources attribute to the 2025 Universal Registration Document.
- **foresite.json:** Wikipedia (Vik Bajaj) still calls Bajaj CEO of Foresite Labs. The firm's own team pages and BioCentury (Aug 2026) disagree, and I applied the firm's version.
- **mit.json (Sharp):** the lab website is still written in the present tense. The MIT Biology profile says the lab is closed, and the lab site lists members only for 1974–2025. I applied the closure.
- **penn.json (Bennett):** sources give her emerita start as 2021 (NAS), 2024 (a third-party profile) or 2025 (Penn's FY2025 retiree list). I kept the date out of the text.
- **uw-ipd.json (Stewart):** his IPD page still says "Interim Executive Director". Rosetta Commons says he is retiring, and he no longer appears on the IPD faculty and staff list.
- **merck.json:** Lynparza alliance revenue ($1,450M) and Winrevair ($1,443M) are effectively tied for 6th. Lynparza is a profit share, not product sales.
- **pfizer.json:** profiles give Pfizer Ventures about $900M in total commitments; $1.0B is stored. Kept.
- **dana-farber.json:** Dana-Farber calls Meyerson "Director" of the Center for Cancer Genomics; the Broad calls him "Co-director". No change.

## Couldn't check / left open

**General.** The web-search quota ran out for three of the five research batches (pharma ×2, labs A). Items not reached are listed here.

**Pharma**
- **Venture arms not checked this month:** AbbVie, Amgen, AstraZeneca (MedImmune Ventures still operating?), BMS, Gilead, GSK (SR One new fund), J&J (JJDC), Lilly, Merck (GHI Fund), Novartis, Novo Holdings, Roche, Takeda.
- **takeda.json `top_products`:** the ranking is probably stale. Eohilia sold only ¥8.8B, and Velcade isn't broken out in the 20-F. Immunoglobulins (¥790.6B), Gattex, Takecab and Trintellix all outsell Eohilia. No FY2025 Vyvanse or albumin figures were found, so the true top 6 couldn't be set. Only the Entyvio and Takhzyro values were filled in.
- **lilly.json:** FY2025 figures for Trulicity, Taltz and Jardiance weren't confirmed from a primary source; the Q4 release returned 403. Membership of the top 6 is confirmed by the 10-K.
- **gsk.json `employees`:** 65000 / "2026" has no source. The 20-F gives a 2025 *average* headcount of 68,307 and no year-end figure. Left as is.
- **roche.json `employees`:** the 2025 annual report says only "more than 100,000". The stored 103,249 may be the 2024 figure. Left as is.
- **novo.json:** NovoRapid, Tresiba and NovoSeven are reported only inside product groups, so their FY2025 values weren't confirmed.
- **gilead.json `revenue_usd`:** the exact figure in millions wasn't confirmed because the PDF was unreadable. The reported $29.4B is consistent with the stored value.
- **pfizer.json:** employees (~75,000) came from a search snippet only.
- **jnj.json:** the status of the DePuy Synthes / orthopaedics separation wasn't checked. "Orthopaedics" remains in `therapeutic_areas`.
- **Therapeutic areas:** not re-checked for Merck, Novartis, Novo, Pfizer, Roche, Sanofi or Takeda.

**2026 year-to-date shifts (not applied; top_products are FY2025 figures)**
- AstraZeneca: Tagrisso has passed Farxiga after Farxiga lost US exclusivity.
- J&J: Tremfya has passed Stelara.
- BMS: Reblozyl is likely past Revlimid.
- Amgen: Repatha may pass Prolia.
- Re-rank after FY2026 results in early 2027.

**Builders and investors**
- **flagship.json:** the site returned 403. A Sep 2025 press-release snippet names Paul Biondi as Managing Partner; that wasn't confirmed, so he wasn't added.
- **atlas.json:** AUM ($2.7B) isn't stated on the firm's site.
- **khosla.json:**
  - Nessan Bermingham is no longer on the team page and his profile URL returns 404. No departure announcement was found, so he wasn't removed.
  - `latest_fund` (VIII, $1.6B, 2023) may be stale. July 2026 reports mention a ~$4B fund set closed around early 2025 (not verified) and a new $5.5B raise in talks.
- **thrive.json:**
  - `aum_usd` of ~$50B appears only on Wikipedia, citing Bloomberg (Feb 2026). It was not applied.
  - Nworah Ayogu's exact title wasn't confirmed.
- **general-catalyst.json:** `aum_usd` (700000000) looks like the life-sciences amount deployed, not AUM. Firm-wide AUM is reported as more than $40B. Flagged for a decision on what the field should mean.
- **Funds not yet closed:**
  - ARCH Fund XIV: Form D shows a $3B target, nothing sold.
  - Third Rock VII: Form D from Jun 2026 shows $750M, $0 sold.
  - General Catalyst XIII.
  - NEA 19.
- **hq values:** a16z's is blank and no source was found. GV fund and AUM aren't disclosed.
- **thirdrock.json:** retirement dates for Levin and Starr weren't found. Robert Tepper's page says "Partner"; the stored "Founding Partner / Partner" was kept.

**Labs**
- **caltech.json:**
  - Deshaies: emeritus, at Amgen 2017–2025, joined Xencor's board in Jul 2025. Search snippets only (the Xencor page returned 403), so not applied.
  - Quake: Wikipedia and a BRCCH snippet report an ETH Zurich (D-BSSE) appointment in 2026. Only the Stanford "on leave" status was applied.
  - "Caltech Seed fund (with Wilson Hill Ventures)" no longer appears on innovation.caltech.edu. Not proof it closed, so it was left.
- **cambridge.json:**
  - "Cambridge Enterprise Ventures" and "Technology Investment Fund" aren't on the current funds page. Left.
  - Kouzarides's Gurdon group, Knowles's Cavendish affiliation, Cambridge Innovation Capital and the Milner incubator weren't checked.
- **berkeley.json:**
  - IGI–Bakar Labs building: groundbreaking was reportedly in July 2026, but the page returned 403. `programs[4]` was left as "planned".
  - Not checked: whether Schaffer still directs Bakar Labs (bakarlabs.berkeley.edu doesn't resolve), SkyDeck and BEVC.
- **broad.json:** the Cancer Dependency Map and Stanley Center programs weren't checked.
- **dana-farber.json:**
  - LAUNCHPAD may now be named "Lab for Antibody and Nanobody Phage Display and Discovery" (snippet only). Not applied.
  - Eric Fischer's title wasn't confirmed, and cpd.dana-farber.org doesn't resolve.
- **harvard.json:** Sinclair was confirmed only from Wikipedia and his lab site.
- **mit.json:**
  - Tom Knight: Wikipedia (tagged as outdated) says he is a former CSAIL scientist, now at Ginkgo, with no date. Not applied.
  - The MIT Synthetic Biology Center (synbio.mit.edu) doesn't resolve, and no current page was found.
- **oxford.json:**
  - Luke Alphey: a July 2026 job ad (snippet) names him a professor at the University of York. Not applied.
  - "OUI Incubator" may be officially "OUI Startup Incubator" (snippet). Not applied.
  - Sarah Gilbert's page (403) and the Jenner Institute site (403) couldn't be checked.
- **penn.json:** the note that James Wilson left Penn in Oct 2024 for GEMMA Biotherapeutics was a snippet only and wasn't added. The entry already says "(former director)".
- **stanford.json:** Karl Deisseroth won the 2026 Nobel Prize (Simons Foundation, 5 Oct 2026). He is still at Stanford, so no status change; the prize belongs in the daily sweep's events, not here.
