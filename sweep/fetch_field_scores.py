#!/usr/bin/env python3
"""Score each silo on research activity -> data/field_scores.json (Frontiers tab and silo pages).

Four signals per silo, each ranked across silos (0-100) and averaged into one score:
  - preprints:  bioRxiv + medRxiv momentum, last 30 days vs the 30 before (from data/frontiers.json,
                so run sweep/fetch_frontiers.py first)
  - growth:     journal articles, last 90 days vs the 90 before, relative to all biomedical journal
                articles over the same windows (OpenAlex indexes recent papers late, so raw counts dip)
  - quality:    the average journal's 2-year mean citedness (an impact-factor stand-in), log-scaled,
                plus the share of articles in journals at or above TOP_CITEDNESS
  - uptake:     share of articles 6-18 months old already cited at least CITED_MIN times
Articles are OpenAlex journal works in biomedical fields whose title or abstract matches the silo's
search. Windows end LAG_DAYS ago because OpenAlex indexes the newest papers late.

  python3 sweep/fetch_field_scores.py
"""
import json
import math
import os
import sys
import time
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_universe import get, warn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "field_scores.json"
SOURCES_CACHE = ROOT / "sweep" / "cache" / "openalex_sources.json"
API = "https://api.openalex.org/"
# without a key OpenAlex shares $0.10/day across everyone on this IP, too little for a run (~300
# requests); a free key from https://openalex.org/settings/api gets $1/day. Set it in sweep/.env.
API_KEY = os.environ.get("OPENALEX_API_KEY", "")
REQUESTS = [0]
LAG_DAYS, WINDOW, TOP_CITEDNESS, CITED_MIN = 14, 90, 10.0, 5
# OpenAlex fields: biochemistry & genetics, chemistry, computer science, immunology & microbiology,
# medicine, neuroscience, pharmacology. Leaves out agriculture, so plant CRISPR work doesn't count.
FIELDS = "13|16|17|24|27|28|30"
# OpenAlex title/abstract search per silo (same silo ids as taxonomy/silos.md and fetch_frontiers.py)
SILO_SEARCH = {
    "ai-discovery": '("drug discovery" AND ("deep learning" OR "machine learning" OR "generative model")) OR "protein design" OR "de novo protein" OR alphafold',
    "foundation-models": '"foundation model" OR "virtual cell" OR "single-cell foundation" OR "protein language model"',
    "gene-editing": 'crispr OR "base editing" OR "base editor" OR "prime editing" OR "gene editing" OR "epigenome editing"',
    "gene-therapy": '"gene therapy" OR "adeno-associated virus" OR "AAV vector" OR "lentiviral vector" OR "AAV capsid"',
    "rna": '"mRNA vaccine" OR "mRNA therapeutic" OR siRNA OR "antisense oligonucleotide" OR "RNA editing" OR "lipid nanoparticle"',
    "cell-therapy": '"CAR-T" OR "CAR T cell" OR "chimeric antigen receptor" OR "CAR-NK" OR "tumor-infiltrating lymphocyte" OR "cell therapy"',
    "antibody": '"monoclonal antibody" OR "bispecific antibody" OR nanobody OR "therapeutic antibody"',
    "adc": '"antibody-drug conjugate" OR "antibody drug conjugate"',
    "radiopharma": '"radioligand therapy" OR radiopharmaceutical OR "lutetium-177" OR "actinium-225" OR radiotheranostic OR "PSMA PET"',
    "protein-degradation": 'PROTAC OR "molecular glue" OR "targeted protein degradation" OR "protein degrader"',
    "small-molecule": '"small molecule inhibitor" OR "kinase inhibitor" OR "covalent inhibitor" OR "fragment-based drug"',
    "microbiome": '"gut microbiome" OR "microbiome therapeutic" OR "fecal microbiota transplantation" OR "live biotherapeutic"',
    "synbio": '"synthetic biology" OR "genetic circuit" OR "metabolic engineering" OR biomanufacturing',
    "tools-omics": '"spatial transcriptomics" OR "single-cell RNA sequencing" OR "single-cell sequencing" OR "long-read sequencing" OR "spatial proteomics"',
    "diagnostics": '"liquid biopsy" OR "cell-free DNA" OR "multi-cancer early detection" OR "circulating tumor DNA"',
    "lab-automation": '"self-driving laboratory" OR "autonomous laboratory" OR "laboratory automation" OR "robotic experimentation"',
    "longevity": '"partial reprogramming" OR "cellular senescence" OR senolytic OR "epigenetic clock" OR "biological age" OR healthspan',
}


def oa(path, **params):
    if API_KEY:
        params["api_key"] = API_KEY
    REQUESTS[0] += 1
    d = json.loads(get(API + path + "?" + urllib.parse.urlencode(params), timeout=60, tries=6))
    time.sleep(0.15)  # stays well under OpenAlex's 10 requests/second
    return d


def works_filter(search, start, end, extra=""):
    """search=None counts every biomedical journal article (the baseline growth is measured against)."""
    f = (f"title_and_abstract.search:{search}," if search else "") + (
         f"from_publication_date:{start},to_publication_date:{end},"
         f"primary_location.source.type:journal,primary_topic.field.id:{FIELDS}")
    return f + ("," + extra if extra else "")


def count(search, start, end, extra=""):
    return oa("works", filter=works_filter(search, start, end, extra), per_page=1, select="id")["meta"]["count"]


def by_journal(search, start, end):
    """{source id: article count}, paging through every journal (the tail is long)."""
    out, cursor = {}, "*"
    for _ in range(50):
        d = oa("works", filter=works_filter(search, start, end), group_by="primary_location.source.id", per_page=200, cursor=cursor)
        for g in d.get("group_by", []):
            if g.get("key"):
                out[g["key"].rsplit("/", 1)[-1]] = g["count"]
        cursor = d.get("meta", {}).get("next_cursor")
        if not cursor or not d.get("group_by"):
            return out
    warn(f"journal list cut at 50 pages ({len(out)} journals)")
    return out


def citedness(ids):
    """2-year mean citedness per source id, cached for 30 days (journal metrics change yearly)."""
    cache = json.loads(SOURCES_CACHE.read_text()) if SOURCES_CACHE.exists() else {}
    stale = (date.today() - timedelta(days=30)).isoformat()
    need = [i for i in ids if i not in cache or cache[i]["at"] < stale]
    for k in range(0, len(need), 100):
        batch = need[k:k + 100]
        d = oa("sources", filter="openalex_id:" + "|".join(batch), per_page=100, select="id,display_name,summary_stats")
        got = {s["id"].rsplit("/", 1)[-1]: s for s in d.get("results", [])}
        for i in batch:
            s = got.get(i, {})
            cache[i] = {"name": s.get("display_name", ""), "c": (s.get("summary_stats") or {}).get("2yr_mean_citedness") or 0, "at": date.today().isoformat()}
    if need:
        SOURCES_CACHE.parent.mkdir(parents=True, exist_ok=True)
        SOURCES_CACHE.write_text(json.dumps(cache))
    return cache


def pct_ranks(vals):
    """{key: 0-100} by rank among the keys that have a value; ties share the average rank."""
    have = sorted((v, k) for k, v in vals.items() if v is not None)
    out = {}
    for i, (v, k) in enumerate(have):
        same = [j for j, (w, _) in enumerate(have) if w == v]
        out[k] = round(100 * (sum(same) / len(same)) / max(len(have) - 1, 1))
    return out


def main():
    if not API_KEY:
        warn("OPENALEX_API_KEY is not set (see sweep/.env.example); the shared no-key budget usually runs out mid-run")
    today = date.today()
    end = today - timedelta(days=LAG_DAYS)
    cur = ((end - timedelta(days=WINDOW - 1)).isoformat(), end.isoformat())
    prev_end = end - timedelta(days=WINDOW)
    prev = ((prev_end - timedelta(days=WINDOW - 1)).isoformat(), prev_end.isoformat())
    old = ((today - timedelta(days=548)).isoformat(), (today - timedelta(days=183)).isoformat())  # 6-18 months
    fr = ROOT / "data" / "frontiers.json"
    momentum = json.loads(fr.read_text()).get("momentum", {}) if fr.exists() else {}

    raw, journals = {}, {}
    try:
        base_cur, base_prev = count(None, *cur), count(None, *prev)
    except Exception as e:  # noqa: BLE001
        warn(f"baseline: {e}; keeping the existing file")
        sys.exit(1)
    base = base_cur / base_prev
    for sid, q in SILO_SEARCH.items():
        try:
            n_cur, n_prev = count(q, *cur), count(q, *prev)
            n_old, n_old_cited = count(q, *old), count(q, *old, f"cited_by_count:>{CITED_MIN - 1}")
            journals[sid] = by_journal(q, *cur)
        except Exception as e:  # noqa: BLE001
            # a partial set would rank silos against each other unfairly, so keep the last full file
            warn(f"{sid}: {e}; keeping the existing file")
            sys.exit(1)
        m = momentum.get(sid)
        raw[sid] = {"articles": n_cur, "articles_prev": n_prev, "old": n_old, "old_cited": n_old_cited,
                    "preprints": m[1] if m else None, "preprints_prev": m[0] if m else None}
        print(f"  {sid}: {n_cur} articles ({n_prev} before), {len(journals[sid])} journals")

    meta = citedness(sorted({j for js in journals.values() for j in js}))
    for sid, r in raw.items():
        js = journals[sid]
        n = sum(js.values())
        r["mean_log_citedness"] = round(sum(c * math.log1p(meta.get(j, {}).get("c", 0)) for j, c in js.items()) / n, 3) if n else None
        r["top_share"] = round(sum(c for j, c in js.items() if meta.get(j, {}).get("c", 0) >= TOP_CITEDNESS) / n, 3) if n else None
        r["top_journals"] = [[meta.get(j, {}).get("name", j), c, round(meta.get(j, {}).get("c", 0), 1)]
                             for j, c in sorted(js.items(), key=lambda x: -x[1]) if meta.get(j, {}).get("c", 0) >= TOP_CITEDNESS][:5]
        r["growth"] = round(r["articles"] / r["articles_prev"] / base - 1, 3) if r["articles_prev"] >= 20 else None
        r["preprint_growth"] = round(r["preprints"] / r["preprints_prev"] - 1, 3) if (r["preprints_prev"] or 0) >= 10 else None
        r["uptake"] = round(r["old_cited"] / r["old"], 3) if r["old"] >= 20 else None

    # quality = average of the two journal measures' ranks; each signal is 0-100, the score their mean
    ranks = {k: pct_ranks({s: r[k] for s, r in raw.items()}) for k in ("preprint_growth", "growth", "mean_log_citedness", "top_share", "uptake")}
    for sid, r in raw.items():
        q = [ranks[k][sid] for k in ("mean_log_citedness", "top_share") if sid in ranks[k]]
        parts = {"preprints": ranks["preprint_growth"].get(sid), "growth": ranks["growth"].get(sid),
                 "quality": round(sum(q) / len(q)) if q else None, "uptake": ranks["uptake"].get(sid)}
        r["parts"] = parts
        have = [v for v in parts.values() if v is not None]
        r["score"] = round(sum(have) / len(have)) if len(have) >= 3 else None

    out = {"fetched": today.isoformat(), "windows": {"current": cur, "previous": prev, "uptake": old},
           "baseline": {"articles": base_cur, "articles_prev": base_prev},
           "top_citedness": TOP_CITEDNESS, "cited_min": CITED_MIN, "silos": raw}
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT}: {len(raw)} silos, {len(meta)} journals known, {REQUESTS[0]} OpenAlex requests")


if __name__ == "__main__":
    main()
