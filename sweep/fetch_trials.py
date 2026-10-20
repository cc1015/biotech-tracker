#!/usr/bin/env python3
"""Snapshot recent clinical-trial activity from ClinicalTrials.gov into data/trials.json.

Covers interventional drug / biological / genetic studies in phase 1-3 with a milestone in the last
--days (default 90): newly registered, results posted, primary completion reached, or stopped
(terminated / suspended / withdrawn). Each trial is tagged industry vs academic from the registry's
lead-sponsor class and given silos from its interventions and conditions.

  python3 sweep/fetch_trials.py            # last 90 days
  python3 sweep/fetch_trials.py --days 30
"""
import argparse
import json
import re
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_universe import get, warn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "trials.json"
API = "https://clinicaltrials.gov/api/v2/studies?"
BASE = ("AREA[StudyType]INTERVENTIONAL AND (AREA[InterventionType]DRUG OR AREA[InterventionType]BIOLOGICAL "
        "OR AREA[InterventionType]GENETIC) AND (AREA[Phase]PHASE1 OR AREA[Phase]PHASE2 OR AREA[Phase]PHASE3)")
FIELDS = ("NCTId,BriefTitle,Acronym,OverallStatus,Phase,StartDate,PrimaryCompletionDate,StudyFirstPostDate,"
          "ResultsFirstPostDate,LastUpdatePostDate,LeadSponsorName,LeadSponsorClass,CollaboratorName,Condition,"
          "InterventionName,InterventionType,EnrollmentCount,WhyStopped")
# intervention / condition wording -> silo ids (first matches win; a trial can carry two)
SILO_RULES = [
    ("cell-therapy", r"\bcar[- ]?t\b|\bcar[- ]?nk\b|chimeric antigen|\btil\b|tumou?r[- ]infiltrating|cell therapy|t[- ]cell therapy|\bnk cell"),
    ("gene-editing", r"crispr|base edit|prime edit|gene edit|cas9|\bzfn\b|talen"),
    ("gene-therapy", r"gene therapy|\baav\d*\b|adeno-associated|lentivir|vector genomes|\bvg/kg"),
    ("rna", r"\bmrna\b|sirna|antisense|oligonucleotide|\baso\b|-siran\b|-rsen\b|lnp"),
    ("adc", r"antibody[- ]drug conjugate|vedotin|deruxtecan|govitecan|emtansine|\badc\b"),
    ("radiopharma", r"177lu|lu-177|lutetium|225ac|actinium|radioligand|radiopharm|\b68ga\b|psma-617"),
    ("protein-degradation", r"degrader|protac|molecular glue"),
    ("antibody", r"mab\b|antibod|bispecific|-cept\b"),
    ("microbiome", r"microbio|fecal microbiota|live biotherapeutic"),
    ("small-molecule", r"(tinib|ciclib|parib|lisib|rafenib|zomib|gliptin|gliflozin|prazole|statin|tegravir|buvir|asvir|olol|sartan|semide)\b"),
]


def silos_of(text):
    t = text.lower()
    out = [sid for sid, rx in SILO_RULES if re.search(rx, t)]
    return out[:2]


def first(d, *path, default=""):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p, {})
    return d if d not in ({}, None) else default


def fetch(cond, label, cap=2500):
    params = {"filter.advanced": f"{BASE} AND {cond}", "fields": FIELDS, "pageSize": "1000", "countTotal": "true"}
    out, token = [], None
    while True:
        q = dict(params, **({"pageToken": token} if token else {}))
        # tries=6 waits ~30s in all, long enough for a network still coming up after wake
        d = json.loads(get(API + urllib.parse.urlencode(q), timeout=90, tries=6))
        out += d.get("studies", [])
        token = d.get("nextPageToken")
        if not token or len(out) >= cap:
            break
    print(f"  {label}: {len(out)} of {d.get('totalCount', '?')}")
    return out


def compact(s, milestone):
    p = s.get("protocolSection", {})
    idm, st, sp, cond, arms, des = (p.get(k, {}) for k in ("identificationModule", "statusModule", "sponsorCollaboratorsModule",
                                                           "conditionsModule", "armsInterventionsModule", "designModule"))
    ivs = [i for i in arms.get("interventions", []) if i.get("type") in ("DRUG", "BIOLOGICAL", "GENETIC")]
    names = [i.get("name", "") for i in ivs]
    conds = cond.get("conditions", [])
    cls = first(sp, "leadSponsor", "class")
    return {
        "id": idm.get("nctId"), "title": idm.get("briefTitle", ""), "acronym": idm.get("acronym", ""),
        "status": st.get("overallStatus", ""), "phase": "/".join(x.replace("PHASE", "") for x in des.get("phases", [])),
        "start": first(st, "startDateStruct", "date"), "pcd": first(st, "primaryCompletionDateStruct", "date"),
        "posted": first(st, "studyFirstPostDateStruct", "date"), "results": first(st, "resultsFirstPostDateStruct", "date"),
        "updated": first(st, "lastUpdatePostDateStruct", "date"), "why": st.get("whyStopped", ""),
        "sponsor": first(sp, "leadSponsor", "name"), "cls": cls, "sector": "industry" if cls == "INDUSTRY" else "academic",
        "collab": [c.get("name", "") for c in sp.get("collaborators", [])][:4],
        "conditions": conds[:4], "interventions": names[:4], "n": first(des, "enrollmentInfo", "count", default=None),
        "silo": silos_of(" ".join(names + conds + [idm.get("briefTitle", "")])), "milestones": [milestone],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    today = date.today()
    since = (today - timedelta(days=args.days)).isoformat()
    queries = [
        ("registered", f"AREA[StudyFirstPostDate]RANGE[{since},MAX]"),
        ("results", f"AREA[ResultsFirstPostDate]RANGE[{since},MAX]"),
        ("completed", f"AREA[PrimaryCompletionDate]RANGE[{since},{today.isoformat()}] AND AREA[OverallStatus]COMPLETED"),
        ("stopped", f"AREA[LastUpdatePostDate]RANGE[{since},MAX] AND (AREA[OverallStatus]TERMINATED OR "
                    "AREA[OverallStatus]SUSPENDED OR AREA[OverallStatus]WITHDRAWN)"),
    ]
    trials, failed = {}, []
    for label, cond in queries:
        try:
            for s in fetch(cond, label):
                t = compact(s, label)
                if t["id"] in trials:
                    trials[t["id"]]["milestones"].append(label)
                else:
                    trials[t["id"]] = t
        except Exception as e:  # noqa: BLE001
            warn(f"{label}: {e}")
            failed.append(label)
    if failed or not trials:
        # a partial snapshot would silently drop most trials from the page, so keep the last full one
        warn(f"{', '.join(failed) or 'all queries'} failed; keeping the existing file")
        sys.exit(1)
    OUT.write_text(json.dumps({"fetched": today.isoformat(), "since": since, "days": args.days,
                               "trials": list(trials.values())}, separators=(",", ":")))
    ind = sum(t["sector"] == "industry" for t in trials.values())
    print(f"wrote {OUT}: {len(trials)} trials ({ind} industry, {len(trials) - ind} academic), "
          f"{OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
