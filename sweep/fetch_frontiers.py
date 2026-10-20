#!/usr/bin/env python3
"""Recent papers and preprints for the Frontiers tab -> data/frontiers.json.

  - PubMed: the latest papers by each PI on the Labs pages (author + institution query), with author
    affiliations so papers with industry co-authors can be flagged.
  - bioRxiv / medRxiv: every preprint in the window (cached per day in sweep/cache/preprints/, so later
    runs only fetch new days). Kept: preprints from tracked institutions or PIs, preprints whose
    corresponding author is at a company, and all silo-tagged preprints for the momentum counts.
Silos come from keyword matching on title + abstract.

  python3 sweep/fetch_frontiers.py              # 60-day window (30 days vs the 30 before, for momentum)
  python3 sweep/fetch_frontiers.py --days 90
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_universe import get, warn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "frontiers.json"
CACHE = ROOT / "sweep" / "cache" / "preprints"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# PubMed affiliation terms per Labs page, to keep author-name matches to the right person
LAB_AFFIL = {
    "broad": ["Broad Institute", "Massachusetts Institute of Technology", "Harvard"], "mit": ["Massachusetts Institute of Technology", "Whitehead", "Koch Institute"],
    "harvard": ["Harvard", "Wyss", "Massachusetts General", "Brigham", "Boston Children"], "dana-farber": ["Dana-Farber", "Harvard"],
    "penn": ["University of Pennsylvania", "Perelman", "Children's Hospital of Philadelphia"], "oxford": ["University of Oxford"],
    "stanford": ["Stanford"], "ucsf": ["University of California, San Francisco", "UCSF"], "berkeley": ["University of California, Berkeley", "Innovative Genomics"],
    "uw-ipd": ["University of Washington", "Institute for Protein Design"], "caltech": ["California Institute of Technology", "Caltech"],
    "cambridge": ["University of Cambridge", "MRC Laboratory of Molecular Biology", "Wellcome Sanger"],
}
INST_RX = {
    "broad": r"broad institute", "mit": r"massachusetts institute of technology|\bmit\b|whitehead", "harvard": r"harvard|wyss|massachusetts general|brigham|boston children",
    "dana-farber": r"dana[- ]farber", "penn": r"university of pennsylvania|perelman|children's hospital of philadelphia", "oxford": r"university of oxford",
    "stanford": r"stanford", "ucsf": r"university of california,? san francisco|\bucsf\b", "berkeley": r"university of california,? berkeley|innovative genomics",
    "uw-ipd": r"institute for protein design", "caltech": r"california institute of technology|caltech", "cambridge": r"university of cambridge|mrc laboratory of molecular biology",
}
COMPANY = re.compile(r"\b(Inc|Ltd|LLC|GmbH|AG|S\.A\.|Corp|Corporation|Therapeutics|Pharmaceuticals?|Biosciences|Biotherapeutics|Pharma|Biotech|Genomics Inc|Laborator(?:y|ies) Inc)\b\.?", re.I)
NOT_COMPANY = re.compile(r"universit|institut|hospital|college|school|center for|centre|foundation|council|ministry|academy|clinic\b|national|NIH|HHMI|Howard Hughes", re.I)
SILO_KW = [
    ("ai-discovery", r"deep learning|machine learning|protein design|de novo design|generative model|diffusion model|language model|alphafold|neural network|artificial intelligence"),
    ("foundation-models", r"foundation model|virtual cell|cell atlas|single-cell foundation|large-scale pretrain"),
    ("gene-editing", r"crispr|base edit|prime edit|gene edit|cas9|cas12|cas13|epigenome edit|recombinase|bridge rna"),
    ("gene-therapy", r"gene therapy|\baav\b|adeno-associated|lentivir|capsid"),
    ("rna", r"\bmrna\b|sirna|antisense oligo|\baso\b|rna editing|lipid nanoparticle|\blnp\b|circular rna"),
    ("cell-therapy", r"car[- ]?t\b|chimeric antigen receptor|car[- ]?nk|cell therapy|\btil\b|engineered t cell"),
    ("antibody", r"antibod|nanobod|bispecific|monoclonal"),
    ("adc", r"antibody[- ]drug conjugate|\badc\b"),
    ("radiopharma", r"radioligand|radiopharm|177lu|225ac|theranostic"),
    ("protein-degradation", r"degrader|protac|molecular glue|targeted protein degradation"),
    ("small-molecule", r"small[- ]molecule|kinase inhibitor|covalent inhibitor|fragment-based"),
    ("microbiome", r"microbiom|gut bacteri|commensal"),
    ("synbio", r"synthetic biology|genetic circuit|metabolic engineering|biomanufactur"),
    ("tools-omics", r"spatial transcriptom|single-cell sequencing|proteomic|long-read sequencing|multiome"),
    ("diagnostics", r"liquid biopsy|cell-free dna|cfdna|early detection|diagnostic assay"),
    ("lab-automation", r"self-driving lab|autonomous lab|lab automation|robotic"),
    ("longevity", r"aging|ageing|rejuvenat|senescen|partial reprogramming"),
]


def silos_of(text):
    t = (text or "").lower()
    return [sid for sid, rx in SILO_KW if re.search(rx, t)][:3]


def pi_key(name):
    """'David R. Liu' -> ('Liu', 'D')."""
    parts = [p for p in re.sub(r"[^A-Za-z\- ]", " ", name).split() if p.lower() not in ("prof", "dr")]
    return (parts[-1], parts[0][0]) if len(parts) >= 2 else (None, None)


def pubmed(labs, since):
    out = []
    for lab in labs:
        affil = LAB_AFFIL.get(lab["slug"], [lab["name"]])
        for l in lab.get("labs", []):
            for pi in re.split(r"\s*/\s*|\s+and\s+", l.get("pi", "")):
                last, ini = pi_key(pi)
                if not last:
                    continue
                term = f'"{last} {ini}"[au] AND ({" OR ".join(f"{a}[ad]" for a in affil)}) AND {since.replace("-", "/")}:3000[dp]'
                try:
                    ids = json.loads(get(EUTILS + "esearch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "retmode": "json", "retmax": 6, "sort": "pub_date", "term": term})))["esearchresult"]["idlist"]
                    time.sleep(0.4)
                    if not ids:
                        continue
                    root = ET.fromstring(get(EUTILS + "efetch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "retmode": "xml", "id": ",".join(ids)})))
                    time.sleep(0.4)
                except Exception as e:  # noqa: BLE001
                    warn(f"pubmed {pi}: {e}")
                    continue
                for art in root.iter("PubmedArticle"):
                    title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
                    ab = " ".join("".join(x.itertext()) for x in art.iter("AbstractText"))
                    doi = next((x.text for x in art.iter("ArticleId") if x.get("IdType") == "doi"), "")
                    pmid = next((x.text for x in art.iter("PMID")), "")
                    pd = art.find(".//ArticleDate") or art.find(".//PubDate")
                    y = pd.findtext("Year") if pd is not None else ""
                    m = pd.findtext("Month") if pd is not None else ""
                    dd = pd.findtext("Day") if pd is not None else ""
                    mm = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}.get(m, m)
                    when = "-".join(x for x in [y, (mm or "").zfill(2) if mm else "", (dd or "").zfill(2) if dd else ""] if x)
                    affs = [x.text or "" for x in art.iter("Affiliation")]
                    companies = sorted({a.split(",")[0].strip() for a in affs if COMPANY.search(a) and not NOT_COMPANY.search(a.split(",")[0])})[:4]
                    authors = [f'{a.findtext("LastName") or ""} {a.findtext("Initials") or ""}'.strip() for a in art.iter("Author")]
                    out.append({"src": "pubmed", "title": title, "date": when, "venue": art.findtext(".//Journal/ISOAbbreviation") or art.findtext(".//Journal/Title") or "",
                                "doi": doi, "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "pi": pi.strip(), "lab": lab["slug"],
                                "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""), "industry": companies,
                                "silo": silos_of(f"{title} {ab}"), "snip": ab[:280]})
        print(f"  pubmed: {lab['slug']} done, {len(out)} papers so far")
    seen, uniq = set(), []
    for p in sorted(out, key=lambda p: p["date"], reverse=True):  # a paper can match two co-authoring PIs
        if p["url"] not in seen:
            seen.add(p["url"]); uniq.append(p)
    return uniq


def preprint_day(server, d):
    f = CACHE / f"{server}-{d}.json"
    if f.exists() and d < (date.today() - timedelta(days=2)).isoformat():
        return json.loads(f.read_text())
    rows, cursor = [], 0
    while True:
        try:
            j = json.loads(get(f"https://api.biorxiv.org/details/{server}/{d}/{d}/{cursor}", timeout=60))
        except Exception as e:  # noqa: BLE001
            warn(f"{server} {d}: {e}")
            break
        coll = j.get("collection", [])
        for c in coll:
            rows.append({k: c.get(k, "") for k in ("title", "authors", "author_corresponding", "author_corresponding_institution", "doi", "date", "category", "version")}
                        | {"snip": (c.get("abstract") or "")[:280]})
        total = int((j.get("messages") or [{}])[0].get("total", 0) or 0)
        cursor += len(coll)
        if not coll or cursor >= total:
            break
        time.sleep(0.25)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rows))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    args = ap.parse_args()
    today = date.today()
    labs = []
    for f in sorted((ROOT / "data" / "labs").glob("*.json")):
        d = json.loads(f.read_text()); d["slug"] = f.stem; labs.append(d)
    papers = pubmed(labs, (today - timedelta(days=180)).isoformat())
    # PI name patterns as bioRxiv writes them: 'Liu, D. R.' -> surname + first initial
    pis = []
    for lab in labs:
        for l in lab.get("labs", []):
            for pi in re.split(r"\s*/\s*|\s+and\s+", l.get("pi", "")):
                last, ini = pi_key(pi)
                if last:
                    pis.append((re.compile(rf"\b{re.escape(last)}, {ini}\.", re.I), pi.strip(), lab["slug"]))
    inst = {k: re.compile(v, re.I) for k, v in INST_RX.items()}
    keep, momentum, n_all = [], {}, 0
    half = (today - timedelta(days=args.days // 2)).isoformat()
    for server in ("biorxiv", "medrxiv"):
        for k in range(args.days, -1, -1):
            d = (today - timedelta(days=k)).isoformat()
            for c in preprint_day(server, d):
                if c.get("version") not in ("1", 1):  # count each preprint once, at first posting
                    continue
                n_all += 1
                text = f'{c["title"]} {c["snip"]}'
                sl = silos_of(text)
                for s in sl:
                    m = momentum.setdefault(s, [0, 0])
                    m[1 if c["date"] >= half else 0] += 1
                ci = c["author_corresponding_institution"] or ""
                lab = next((sl_ for sl_, rx in inst.items() if rx.search(ci)), None)
                pi = next(((name, slug) for rx, name, slug in pis if rx.search(c["authors"])), None)
                company = ci if COMPANY.search(ci) and not NOT_COMPANY.search(ci) else ""
                if lab or pi or company:
                    auth = [a.strip() for a in c["authors"].split(";") if a.strip()]
                    keep.append({"src": server, "title": c["title"].strip(), "date": c["date"], "venue": f'{"bioRxiv" if server == "biorxiv" else "medRxiv"} · {c["category"]}',
                                 "doi": c["doi"], "url": f"https://www.{server}.org/content/{c['doi']}v{c['version']}", "pi": pi[0] if pi else "",
                                 "lab": (pi[1] if pi else lab) or "", "inst": ci, "authors": "; ".join(auth[:3]) + (" et al." if len(auth) > 3 else ""),
                                 "industry": [company] if company else [], "silo": sl, "snip": c["snip"]})
        print(f"  {server}: done ({n_all} first versions so far)")
    out = {"fetched": today.isoformat(), "days": args.days, "half": half, "preprints_scanned": n_all,
           "momentum": momentum, "items": papers + sorted(keep, key=lambda p: p["date"], reverse=True)}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT}: {len(papers)} lab papers, {len(keep)} preprints kept of {n_all} scanned, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
