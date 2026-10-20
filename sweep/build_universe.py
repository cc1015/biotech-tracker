#!/usr/bin/env python3
"""Build data/universe.csv: every biotech/pharma company we can find in free bulk sources.

Sources (each one is optional; a failing source is skipped with a warning):
  - ClinicalTrials.gov   industry lead sponsors of drug / biological / genetic trials (worldwide)
  - Wikidata             companies whose industry is biotechnology or pharmaceuticals
  - SEC EDGAR            US-listed companies with SIC 2834 / 2835 / 2836 / 8731 that have a ticker
  - SEC Form D           private raises with industry group Biotechnology / Pharmaceuticals
plus every company in data/companies.csv (curated) and data/news.csv (news).

The SEC sources need SEC_USER_AGENT ("Your Name your@email") in the environment or sweep/.env;
without it they are skipped.

universe.csv is a raw, machine-built list. companies.csv stays the hand-checked core;
`curated=yes` marks universe rows that also appear there.

  python3 sweep/build_universe.py                # all sources
  python3 sweep/build_universe.py --only ctgov   # rebuild from just one source (for testing)
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "universe.csv"
ALIASES = ROOT / "data" / "aliases.csv"   # hand-kept: alias,canonical,note
CACHE = ROOT / "sweep" / "cache"          # raw per-source results, reused with --cached
FIELDS = ["name", "aka", "other_names", "description", "country", "hq", "founded", "employees", "parent", "ticker", "status", "sources",
          "ct_trials", "ct_latest_start", "ct_last_started", "ct_names",
          "formd_latest", "formd_sold_usd", "sec_cik", "wikidata", "website", "curated", "source", "last_verified"]
TODAY = date.today().isoformat()
UA = "BiotechTracker/0.1 (personal research script; Python urllib)"


def load_env():
    env = ROOT / "sweep" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() and not k.startswith("#") and v.strip():
                os.environ.setdefault(k.strip(), v.strip())


def get(url, headers=None, data=None, timeout=60, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry any network error, then give up
            if i == tries - 1 or getattr(e, "code", 500) in (400, 403, 404):
                raise
            time.sleep(2 * (i + 1))


def warn(msg):
    print(f"  ! {msg}", file=sys.stderr)


# ---------- name matching ----------

SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited", "llc", "plc", "ag",
            "sa", "spa", "gmbh", "bv", "nv", "ab", "as", "asa", "oy", "oyj", "kk", "pty", "sas", "srl", "lp",
            "se", "sl", "sarl", "pte", "bhd", "sdn", "holdings", "holding", "group", "the"}


def key(name):
    """'Pfizer Inc.' and 'PFIZER INC' -> 'pfizer'. Keeps descriptive words like 'therapeutics'."""
    s = name.lower().replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b([a-z])[./](?=[a-z]\b)", r"\1", s)  # 'a/s', 's.a.', 'n.v.', 'l.l.c.' -> 'as', 'sa', ...
    words = re.sub(r"[^a-z0-9]+", " ", s).split()
    while words and (words[-1] in SUFFIXES or words[-1] == "and"):  # 'Eli Lilly and Company'
        words.pop()
    while words and words[0] == "the":
        words.pop(0)
    return " ".join(words)


# trailing words that only name a division: 'Novartis Pharmaceuticals' is Novartis
DIVISION_TAIL = re.compile(r"( (pharmaceuticals?|pharma|research and development|r and d|us|usa|"
                           r"international|global|china|japan|europe|uk))+$")


def base(k):
    return DIVISION_TAIL.sub("", k)


# ClinicalTrials.gov sometimes files individual investigators as "industry" sponsors
PERSON = re.compile(r"\b(m\.?d\b|ph\.?d|pharm\.?d|irb\b|investigator|professor|dr\.)", re.I)


def tidy(name):
    """Turn 'MODERNATX, INC.' style all-caps names into title case; leave mixed case alone."""
    name = re.sub(r"\s+", " ", name).strip().strip(",")
    return name.title() if name.isupper() and len(name) > 4 else name


SUBSIDIARY = re.compile(r"[,\s-]*\(?\s*(?:an? (?:wholly[- ]owned |indirect |)subsidiary of|a member of|an affiliate of|"
                        r"an? (?:healthcare |pharmaceutical |)company of|part of)\s+(?:the )?(.+?)"
                        r"(?: group of companies| group)?\)?\s*$|[,\s-]+an? ([A-Z][\w&. -]{1,40}?) company\s*$", re.I)


def split_parent(name):
    """'DICE Therapeutics, Inc., a wholly owned subsidiary of Eli Lilly and Company' -> (DICE..., Eli Lilly...)"""
    m = SUBSIDIARY.search(name)
    return (name[:m.start()].strip(" ,-"), (m.group(1) or m.group(2)).strip()) if m else (name, "")


# ---------- sources ----------

def ctgov():
    """Industry lead sponsors of interventional drug/biologic/genetic studies."""
    base = "https://clinicaltrials.gov/api/v2/studies?"
    params = {
        "filter.advanced": "AREA[LeadSponsorClass]INDUSTRY AND (AREA[InterventionType]DRUG OR "
                           "AREA[InterventionType]BIOLOGICAL OR AREA[InterventionType]GENETIC)",
        "fields": "LeadSponsorName,StartDate",
        "pageSize": "1000",
        "countTotal": "true",
    }
    out, token, page = {}, None, 0
    while True:
        q = dict(params, **({"pageToken": token} if token else {}))
        d = json.loads(get(base + urllib.parse.urlencode(q)))
        if page == 0:
            print(f"  ctgov: {d.get('totalCount')} industry studies")
        for s in d.get("studies", []):
            p = s.get("protocolSection", {})
            name = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "").strip()
            start = p.get("statusModule", {}).get("startDateStruct", {}).get("date", "")
            if not name or PERSON.search(name):
                continue
            raw = name
            name, parent = split_parent(name)
            r = out.setdefault(key(name), {"name": "", "parent": parent, "ct_trials": 0, "ct_latest_start": "",
                                           "ct_names": {}})
            r["ct_names"][raw] = r["ct_names"].get(raw, 0) + 1  # exact sponsor spellings, for registry queries
            r["ct_trials"] += 1
            r["ct_latest_start"] = max(r["ct_latest_start"], start)
            if start <= TODAY:
                r["ct_last_started"] = max(r.get("ct_last_started", ""), start)
        token, page = d.get("nextPageToken"), page + 1
        if page % 20 == 0:
            print(f"  ctgov: {page} pages, {len(out)} sponsors so far")
        if not token:
            break
    for r in out.values():
        r["name"] = tidy(split_parent(max(r["ct_names"], key=r["ct_names"].get))[0])
        r["ct_names"] = ";".join(sorted(r["ct_names"]))
        r["source"] = "https://clinicaltrials.gov/search?" + urllib.parse.urlencode({"lead": r["name"]})
    return out


WIKIDATA_QUERY = """
SELECT ?c ?cLabel ?cDescription ?countryLabel ?hqLabel ?inception ?website ?ticker ?dissolved ?employees ?parentLabel WHERE {
  VALUES ?ind { wd:Q7108 wd:Q507443 }
  ?c wdt:P452 ?ind .
  OPTIONAL { ?c wdt:P17 ?country }
  OPTIONAL { ?c wdt:P159 ?hq }
  OPTIONAL { ?c wdt:P571 ?inception }
  OPTIONAL { ?c wdt:P856 ?website }
  OPTIONAL { ?c p:P414 ?st . ?st pq:P249 ?ticker }
  OPTIONAL { ?c wdt:P576 ?dissolved }
  OPTIONAL { ?c wdt:P1128 ?employees }
  OPTIONAL { ?c wdt:P749 ?parent }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""


WIKIDATA_ALIASES = """
SELECT ?c ?alias WHERE {
  VALUES ?ind { wd:Q7108 wd:Q507443 }
  ?c wdt:P452 ?ind ; skos:altLabel ?alias .
  FILTER(LANG(?alias) = "en")
}"""


def sparql(query):
    return json.loads(get("https://query.wikidata.org/sparql",
                          {"Accept": "application/sparql-results+json",
                           "Content-Type": "application/x-www-form-urlencoded"},
                          data=urllib.parse.urlencode({"query": query}).encode(), timeout=120))["results"]["bindings"]


def wikidata():
    aliases = {}
    for b in sparql(WIKIDATA_ALIASES):
        aliases.setdefault(b["c"]["value"].rsplit("/", 1)[-1], []).append(b["alias"]["value"])
    out = {}
    for b in sparql(WIKIDATA_QUERY):
        v = {k: x["value"] for k, x in b.items() if not re.fullmatch(r"Q\d+", x["value"]) or k == "c"}
        qid = v["c"].rsplit("/", 1)[-1]
        name = v.get("cLabel", "")
        if not name or name == qid:  # no English label
            continue
        r = out.setdefault(key(name), {"name": name, "wikidata": qid, "aliases": aliases.get(qid, []),
                                       "source": f"https://www.wikidata.org/wiki/{qid}"})
        if v.get("parentLabel") and not re.fullmatch(r"Q\d+", v["parentLabel"]):
            r.setdefault("parent", v["parentLabel"])
        r.setdefault("country", v.get("countryLabel", ""))
        r.setdefault("hq", v.get("hqLabel", ""))
        if v.get("inception"):
            r.setdefault("founded", v["inception"][:4])
        if v.get("website"):
            r.setdefault("website", v["website"])
        if v.get("ticker"):
            r.setdefault("ticker", v["ticker"])
        if v.get("cDescription"):
            r.setdefault("description", v["cDescription"])
        if v.get("employees"):  # several dated values are common; keep the largest
            n = int(float(v["employees"]))
            r["employees"] = max(r.get("employees", 0), n)
        if v.get("dissolved"):
            r["status"] = "defunct"
    return out


SEC_SICS = {"2834": "pharmaceutical preparations", "2835": "in vitro diagnostics",
            "2836": "biological products", "8731": "commercial physical & biological research"}


def sec_headers():
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise RuntimeError("SEC_USER_AGENT not set (sweep/.env); SEC refuses anonymous clients")
    return {"User-Agent": ua}


def sec_edgar():
    """Companies currently listed (have a ticker) whose SIC is a biotech/pharma code."""
    h = sec_headers()
    tick = json.loads(get("https://www.sec.gov/files/company_tickers_exchange.json", h))
    listed = {}
    for cik, name, ticker, exch in tick["data"]:
        listed.setdefault(int(cik), (name, ticker, exch))
    out = {}
    for sic in SEC_SICS:
        start = 0
        while True:
            url = ("https://www.sec.gov/cgi-bin/browse-edgar?" + urllib.parse.urlencode(
                {"action": "getcompany", "SIC": sic, "owner": "include", "count": 100, "start": start,
                 "output": "atom"}))
            xml = get(url, h).decode("utf-8", "replace")
            entries = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
            for e in entries:
                cik = re.search(r"<cik>(\d+)</cik>", e)
                if not cik or int(cik.group(1)) not in listed:
                    continue
                name, ticker, exch = listed[int(cik.group(1))]
                state = re.search(r"<state>([^<]*)</state>", e)
                c = int(cik.group(1))
                out.setdefault(key(name), {
                    "name": tidy(name), "ticker": f"{exch}:{ticker}" if exch else ticker, "sec_cik": str(c),
                    "hq": state.group(1) if state else "", "status": "public",
                    "source": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={c}"})
            time.sleep(0.15)  # SEC allows 10 req/s
            if len(entries) < 100:
                break
            start += 100
        print(f"  sec: SIC {sic} done, {len(out)} listed companies so far")
    return out


def sec_form_d(quarters=12):
    """Issuers in SEC's quarterly Form D data sets with a biotech/pharma industry group."""
    h = sec_headers()
    today = date.today()
    y, q = today.year, (today.month - 1) // 3 + 1
    out = {}
    for _ in range(quarters):
        q -= 1
        if q == 0:
            y, q = y - 1, 4
        url = f"https://www.sec.gov/files/structureddata/data/form-d-data-sets/{y}q{q}_d.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(get(url, h, timeout=180)))
        except Exception as e:  # noqa: BLE001
            warn(f"form d {y}q{q}: {e}")
            continue

        def tsv(stem):
            n = next(n for n in z.namelist() if n.upper().endswith(stem + ".TSV"))
            return csv.DictReader(io.TextIOWrapper(z.open(n), "utf-8", errors="replace"), delimiter="\t")

        subs = {r["ACCESSIONNUMBER"]: r.get("FILING_DATE", "") for r in tsv("FORMDSUBMISSION")}
        offers = {r["ACCESSIONNUMBER"]: r for r in tsv("OFFERING")
                  if r.get("INDUSTRYGROUPTYPE", "") in ("Biotechnology", "Pharmaceuticals")}
        for r in tsv("ISSUERS"):
            acc = r["ACCESSIONNUMBER"]
            if acc not in offers or r.get("IS_PRIMARYISSUER_FLAG", "YES").upper() != "YES":
                continue
            name, cik = r.get("ENTITYNAME", "").strip(), r.get("CIK", "").lstrip("0")
            if not name:
                continue
            filed = subs.get(acc, "")
            sold = offers[acc].get("TOTALAMOUNTSOLD", "")
            rec = out.setdefault(key(name), {
                "name": tidy(name), "sec_cik": cik, "formd_latest": "", "formd_sold_usd": "",
                "country": r.get("STATEORCOUNTRYDESCRIPTION", ""), "hq": r.get("CITY", "").title(),
                "founded": r.get("YEAROFINC_VALUE_ENTERED", ""),
                "source": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=D"})
            if _iso(filed) >= rec["formd_latest"]:
                rec["formd_latest"] = _iso(filed)
                rec["formd_sold_usd"] = sold if sold.isdigit() else ""
        print(f"  form d: {y}q{q} done, {len(out)} issuers so far")
        time.sleep(0.2)
    return out


def _iso(d):
    """Form D dates look like '15-JAN-2026'; return '2026-01-15' (or the input if unparseable)."""
    m = re.match(r"(\d{1,2})-([A-Z]{3})-(\d{4})", d or "")
    if not m:
        return d or ""
    mon = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split().index(m.group(2)) + 1
    return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"


SOURCES = {"wikidata": wikidata, "sec": sec_edgar, "formd": sec_form_d, "ctgov": ctgov}
# when sources disagree, the earlier one in this list wins the display name and source URL
PRIORITY = ["sec", "wikidata", "formd", "ctgov"]


# ---------- merge ----------

# main name = the formal/registered one; common name = what people call it
MAIN_FROM = ["sec", "ctgov", "formd", "wikidata", "curated", "alias", "news"]
COMMON_FROM = ["alias", "curated", "wikidata", "news", "sec", "ctgov", "formd"]


def pick_names(names):
    """names: [(source, name, ct_trials)] -> (main, common). Among registry spellings, most trials wins."""
    def first(order):
        for src in order:
            cands = [(t, n) for s, n, t in names if s == src]
            if cands:
                return max(cands, key=lambda c: c[0])[1]
        return names[0][1]
    return first(MAIN_FROM), first(COMMON_FROM)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(SOURCES), action="append", help="run just these sources")
    ap.add_argument("--cached", action="store_true", help="reuse sweep/cache/ instead of downloading (fast re-merge)")
    args = ap.parse_args()
    load_env()

    results = {}
    CACHE.mkdir(exist_ok=True)
    for label in args.only or list(SOURCES):
        cache = CACHE / f"{label}.json"
        if args.cached and cache.exists():
            results[label] = json.loads(cache.read_text())
            print(f"{label}: {len(results[label])} companies (cached)")
            continue
        print(f"{label}…")
        try:
            results[label] = SOURCES[label]()
            cache.write_text(json.dumps(results[label]))
            print(f"{label}: {len(results[label])} companies")
        except Exception as e:  # noqa: BLE001 - one dead source shouldn't sink the rest
            warn(f"{label} skipped: {e}")

    # hand-checked companies are always in the universe, and their names win
    with open(ROOT / "data" / "companies.csv", newline="") as fh:
        results["curated"] = {key(r["name"]): {"name": r["name"], "hq": r["hq"], "founded": r["founded"],
                                               "source": r["source"]} for r in csv.DictReader(fh)}
    # companies named in the news log (tech companies live in tech_entrants.csv, not here)
    with open(ROOT / "data" / "tech_entrants.csv", newline="") as fh:
        tech = {key(r["company"]) for r in csv.DictReader(fh)}
    results["news"] = {}
    with open(ROOT / "data" / "news.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            for n in (r["companies"] or "").split(";"):
                if n.strip() and key(n) not in tech:
                    results["news"].setdefault(key(n), {"name": n.strip(), "source": r["source"]})

    # other names for the same company: hand-kept file first, then Wikidata's aliases
    manual = {}
    if ALIASES.exists():
        with open(ALIASES, newline="") as fh:
            manual = {key(r["alias"]): r["canonical"] for r in csv.DictReader(fh) if r["alias"].strip()}
    # keys are recomputed from names (not taken from the cache), so matching-rule changes apply to cached data
    alias, clash = {}, set()
    wd = {key(r["name"]): r for r in results.get("wikidata", {}).values()}
    for wk, r in wd.items():
        for a in r.get("aliases", []):
            ak = key(a)
            if len(ak) < 3 or ak == wk or ak in wd:  # an alias never captures a different listed entity
                continue
            if alias.get(ak, wk) != wk:
                clash.add(ak)  # 'Merck' is an alias of two companies: use neither
            alias[ak] = wk
    for ak in clash:
        del alias[ak]

    merged, by_base = {}, {}  # by_base: 'regeneron' -> 'regeneron pharmaceuticals'
    for label in ["curated"] + PRIORITY + ["news"]:
        for r in results.get(label, {}).values():
            k = key(r["name"])
            if not k:
                continue
            canon = manual.get(k) or manual.get(base(k))
            k = key(canon) if canon else alias.get(k) or alias.get(base(k)) or k
            if k not in merged:
                k = base(k) if base(k) in merged else by_base.get(k, k)
            by_base.setdefault(base(k), k)
            m = merged.setdefault(k, {f: "" for f in FIELDS} | {"_src": [], "_names": []})
            if label not in m["_src"]:
                m["_src"].append(label)
            m["_names"].append((label, r["name"], r.get("ct_trials", 0)))
            if canon:
                m["_names"].append(("alias", canon, 0))
            if label == "curated":
                m["curated"] = "yes"
            for f, v in r.items():
                if f in ("name", "aliases"):
                    continue
                if f == "ct_trials":
                    m[f] = (m[f] or 0) + v
                elif f in ("ct_latest_start", "ct_last_started"):
                    m[f] = max(m[f], v)
                elif f == "ct_names":
                    m[f] = ";".join(filter(None, [m[f], v]))
                elif v not in ("", None, "TODO") and m.get(f) in ("", None):
                    m[f] = v

    today = date.today().isoformat()
    rows = []
    for k, m in merged.items():
        m["sources"] = ";".join(m.pop("_src"))
        names = m.pop("_names")
        main_name, common = pick_names(names)
        m["name"], m["aka"] = (main_name, common) if key(main_name) != key(common) else (common, "")
        shown = {key(m["name"]), key(m["aka"])}
        m["other_names"] = ";".join(sorted({n for _, n, _ in names if key(n) not in shown}))
        if base(key(m["parent"])) in {base(k) for k in shown}:  # 'Pfizer, part of Pfizer'
            m["parent"] = ""
        m["status"] = m["status"] or ("public" if m["ticker"] else "")
        m["last_verified"] = today
        rows.append(m)
    rows.sort(key=lambda r: r["name"].lower())

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    multi = sum(";" in r["sources"] for r in rows)
    print(f"wrote {OUT}: {len(rows)} companies ({multi} in 2+ sources, "
          f"{sum(r['curated'] == 'yes' for r in rows)} also in companies.csv); "
          f"sources run: {', '.join(results) or 'none'}")


if __name__ == "__main__":
    main()
