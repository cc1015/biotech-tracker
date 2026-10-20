#!/usr/bin/env python3
"""Build web/index.html from data/*.csv and taxonomy/silos.md.

Embeds the data as JSON so the page opens from disk (file://) with no server.
Run from anywhere:  python3 web/build.py
"""
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "sweep"))
from build_universe import base, key  # noqa: E402  same name matching as the universe builder
from fetch_logos import TECH_QIDS  # noqa: E402

# single words too common to count as a company mention in free text
GENERIC = {"bio", "biotech", "therapeutics", "pharma", "pharmaceuticals", "medical", "health", "labs", "precision",
           "global", "life", "sciences", "genomics", "clinical", "research", "biosciences", "genetics", "medicine",
           "biologics", "oncology", "vaccines", "diagnostics", "biotherapeutics", "alpha", "nova", "apex", "summit",
           "atlas", "pioneer", "frontier", "insight", "vision", "focus", "matrix", "vector", "origin", "first",
           "biomedicines", "biopharma", "biopharmaceuticals", "therapeutics", "immunotherapeutics", "pharmaceutical"}


def read_csv(name):
    if not (ROOT / "data" / name).exists():
        return []
    with open(ROOT / "data" / name, newline="") as f:
        return list(csv.DictReader(f))


def read_silos(full=False):
    """Parse the markdown tables in taxonomy/silos.md: id -> name, or with full=True id -> every column."""
    silos, group, header = {}, "", []
    for line in (ROOT / "taxonomy" / "silos.md").read_text().splitlines():
        if line.startswith("## "):
            group = line[3:].strip()
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if cells and cells[0] == "id":
            header = [h.lower() for h in cells]
            continue
        m = re.match(r"`([a-z0-9-]+)`", cells[0]) if cells else None
        if m:
            row = dict(zip(header, cells))
            silos[m.group(1)] = ({"name": cells[1], "group": group, **{k: v for k, v in row.items() if k not in ("id", "silo")}}
                                 if full else cells[1])
    return silos


def link_universe(data):
    """Give each universe row an id and the indices of every news/tech/lead/builder row that mentions it."""
    U = data["universe"]
    exact, by_base = {}, {}
    for i, u in enumerate(U):
        u["id"] = i
        for n in [u["name"], u["aka"]] + (u["other_names"] or "").split(";"):
            if n.strip():
                exact.setdefault(key(n), i)
                by_base.setdefault(base(key(n)), i)
        for f in ("news", "tech", "leads", "builders"):
            u["_" + f] = []
        u["cur"] = -1

    def find(name):
        k = key(name)
        return exact.get(k, by_base.get(k, by_base.get(base(k))))

    # free text is only matched against main and common names; registry alias spellings are too loose
    scannable = {}
    for i, u in enumerate(U):
        for n in (u["name"], u["aka"]):
            k = key(n) if n else ""
            if len(k) >= 5 and k not in GENERIC:
                scannable.setdefault(k, i)

    def scan(text):
        """Company ids named anywhere in free text (whole-word n-gram match)."""
        words = re.sub(r"[^a-z0-9]+", " ", text.lower().replace("&", " and ")).split()
        hits = set()
        for n in range(1, 6):
            for j in range(len(words) - n + 1):
                i = scannable.get(" ".join(words[j:j + n]))
                if i is not None:
                    hits.add(i)
        return hits

    def attach(field, idx, ids):
        for i in ids:
            if i is not None and idx not in U[i][field]:
                U[i][field].append(idx)

    # logos are web/logos/<wikidata id>.svg (sweep/fetch_logos.py); tech companies are looked up by name
    have = {p.stem for p in (WEB / "logos").glob("Q*.svg")} if (WEB / "logos").exists() else set()
    logos = {q: f"logos/{q}.svg" for q in have}
    logos |= {"name:" + key(n): f"logos/{q}.svg" for n, q in TECH_QIDS.items() if q in have}
    for u in U:
        u["logo"] = logos.get(u["wikidata"], "")

    def entity(name):
        """A company as the news/tech tabs show it: profile id if it's in the universe, and a logo if we have one."""
        i = find(name)
        if i is not None:
            u = U[i]
            return {"n": u["aka"] or u["name"], "id": i, "logo": u["logo"]}
        return {"n": name.strip(), "id": None, "logo": logos.get("name:" + key(name), "")}

    def entities(names, extra_ids=()):
        out, seen = [], set()
        for e in [entity(n) for n in names if n.strip()] + [entity(U[i]["name"]) for i in sorted(extra_ids)]:
            tag = e["id"] if e["id"] is not None else e["n"].lower()
            if tag not in seen:
                seen.add(tag)
                out.append(e)
        return out

    for n in data["news"]:
        n["_cos"] = entities((n["companies"] or "").split(";"), scan(n["headline"]))

    # what each company makes (data/products.csv, researched by hand or by the sweep)
    for p in data["products"]:
        i = find(p["name"])
        if i is not None:
            U[i]["prod"] = {k: p[k] for k in ("product", "lead_asset", "modality", "stage", "source", "last_verified")
                            if (p.get(k) or "").strip() and p[k].strip().upper() != "TODO"}

    # articles reporting each event (data/coverage.csv), matched on date + headline
    cov = {}
    for c in data["coverage"]:
        cov.setdefault((c["event_date"], c["event_headline"]), []).append(c)
    for n in data["news"]:
        n["_cov"] = cov.get((n["date"], n["headline"]), [])

    # unconfirmed leads that name one of the event's companies within 10 days of it: "possibly related"
    def day(d):
        try:
            return date.fromisoformat(d[:10])
        except ValueError:
            return None
    lead_ids = [({find(x) for x in (l["known_company"] or "").split(";") if x.strip()} | scan(l["title"])) - {None}
                for l in data["leads"]]
    for n in data["news"]:
        ids, d = {e["id"] for e in n["_cos"] if e["id"] is not None}, day(n["date"])
        n["_rel"] = [j for j, l in enumerate(data["leads"])
                     if l["status"] != "rejected" and ids & lead_ids[j] and d and day(l["published"] or "")
                     and abs((day(l["published"]) - d).days) <= 10][:8]
    for t in data["tech"]:
        t["_co"] = entity(t["company"])
        ids = scan(t["initiative"] + " " + t["description"]) | {find(t["initiative"])}
        t["_cos"] = entities([], {i for i in ids if i is not None})

    # big-pharma family histories (data/pharma/<slug>.json): link the company and every counterparty
    for ph in data["pharma"]:
        ph["uid"] = find(ph["company"])
        for e in ph["events"]:
            e["cid"] = find(e.get("counterparty") or "") if e.get("counterparty") else None
            e["rid"] = find(e.get("result") or "") if e.get("result") else None
            e["clogo"] = logos.get("name:" + key(e.get("counterparty") or ""), "")

    # trials: industry sponsors -> company profile, academic sponsors -> Labs page
    lab_rx = {slug: re.compile(rx, re.I) for slug, rx in LAB_SPONSORS.items()}
    for t in data["trials"]["trials"]:
        if t["sector"] == "industry":
            t["uid"] = find(t["sponsor"])
        else:
            t["lab"] = next((sl for sl, rx in lab_rx.items() if rx.search(t["sponsor"])), None)

    for j, c in enumerate(data["companies"]):
        i = find(c["name"])
        if i is not None:
            U[i]["cur"] = j
    for j, n in enumerate(data["news"]):
        attach("_news", j, {find(x) for x in (n["companies"] or "").split(";") if x.strip()} | scan(n["headline"]))
    for j, t in enumerate(data["tech"]):
        attach("_tech", j, {find(t["company"]), find(t["initiative"])} | scan(t["initiative"] + " " + t["description"]))
    for j, l in enumerate(data["leads"]):
        attach("_leads", j, {find(x) for x in (l["known_company"] or "").split(";") if x.strip()} | scan(l["title"]))
    # builder profiles: merge onto the builders.csv rows by name, link each created company to the universe
    profiles = data.pop("builder_profiles")
    for b in data["builders"]:
        pr = profiles.pop(key(b["name"]), None)
        if pr:
            b.update(slug=pr["slug"], profile=pr.get("profile", {}), created=pr.get("companies", []))
    for pr in profiles.values():  # a profile with no csv row still gets listed
        data["builders"].append({"name": pr["name"], "type": pr.get("profile", {}).get("type", ""), "hq": pr.get("profile", {}).get("hq", ""),
                                 "silos_focus": "", "model": "", "notable_companies": "", "source": "", "last_verified": "",
                                 "slug": pr["slug"], "profile": pr.get("profile", {}), "created": pr.get("companies", [])})
    for b in data["builders"]:
        for c in b.get("created", []):
            c["uid"] = find(c.get("name") or "")
    # investors' life-science portfolios and academic spinouts: same shape as builders ("created")
    builder_slug = {key(b["name"]): b.get("slug") for b in data["builders"] if b.get("slug")}
    for iv in data["investors"]:
        iv["created"] = iv.pop("companies", [])
        for c in iv["created"]:
            c["uid"] = find(c.get("name") or "")
    for lab in data["labs"]:
        lab["created"] = lab.pop("spinouts", [])
        for c in lab["created"]:
            c["uid"] = find(c.get("name") or "")
            c.setdefault("launched", c.get("year", ""))
            # link the co-founding studio/VC to its builder page when we have one
            c["builder_slug"] = next((sl for k, sl in builder_slug.items() if c.get("builder") and (k in key(c["builder"]) or key(c["builder"]).split(" ")[0] == k.split(" ")[0])), None)
    for j, b in enumerate(data["builders"]):
        names = [x for x in re.split(r"[;,]", b["notable_companies"] or "") if x.strip()] + [c["name"] for c in b.get("created", [])]
        attach("_builders", j, {find(x) for x in names})
    for u in U:
        u["news_count"] = len(u["_news"]) + len(u["_tech"]) + len(u["_leads"])
        dates = [data["news"][j]["date"] for j in u["_news"]] + [data["leads"][j]["published"][:10] for j in u["_leads"]]
        u["last_news"] = max(dates, default="")


def read_builder_profiles():
    """data/builders/<slug>.json: researched profile + the companies each builder created."""
    out = {}
    for f in sorted((ROOT / "data" / "builders").glob("*.json")) if (ROOT / "data" / "builders").exists() else []:
        d = json.loads(f.read_text())
        d["slug"] = f.stem
        out[key(d["name"])] = d
    return out


def read_json_dir(name):
    """data/<name>/<slug>.json files (labs, investors), each tagged with its slug."""
    d = ROOT / "data" / name
    out = []
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        x = json.loads(f.read_text())
        x["slug"] = f.stem
        out.append(x)
    return out


# academic trial sponsors -> the Labs page they belong to (affiliated hospitals included)
LAB_SPONSORS = {
    "broad": r"broad institute", "mit": r"massachusetts institute of technology|\bmit\b",
    "harvard": r"harvard|massachusetts general|brigham|beth israel|boston children|mass general",
    "dana-farber": r"dana[- ]farber", "penn": r"university of pennsylvania|abramson|children's hospital of philadelphia|penn medicine",
    "oxford": r"university of oxford|oxford university", "stanford": r"stanford",
    "ucsf": r"university of california,? san francisco|\bucsf\b", "berkeley": r"university of california,? berkeley|innovative genomics",
"caltech": r"california institute of technology|caltech",
    "cambridge": r"university of cambridge|cambridge university hospitals",
}


def read_trials():
    f = ROOT / "data" / "trials.json"
    return json.loads(f.read_text()) if f.exists() else {"trials": []}


def read_pharma():
    """One JSON per big pharma: profile + lineage events (see README "Pharma families")."""
    out = []
    for f in sorted((ROOT / "data" / "pharma").glob("*.json")):
        d = json.loads(f.read_text())
        d["slug"] = f.stem
        d["events"] = sorted(d.get("events", []), key=lambda e: str(e.get("year", "")))
        out.append(d)
    return sorted(out, key=lambda d: -(d.get("profile", {}).get("revenue_usd") or 0))


def logo_token():
    """Logo.dev publishable key (pk_…, safe to embed in a page) from the environment or sweep/.env."""
    import os
    tok = os.environ.get("LOGO_DEV_TOKEN", "")
    env = ROOT / "sweep" / ".env"
    if not tok and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("LOGO_DEV_TOKEN="):
                tok = line.split("=", 1)[1].strip()
    if tok and not tok.startswith("pk_"):
        print("warning: LOGO_DEV_TOKEN should be the publishable key (pk_…), never the secret sk_ key; ignoring it")
        return ""
    return tok


def load_data():
    """Everything the page embeds, linked together (also used by sweep/fit_forecast.py)."""
    data = {
        "logoToken": logo_token(),
        "built": date.today().isoformat(),
        "silos": read_silos(),
        "siloInfo": read_silos(full=True),
        "news": read_csv("news.csv"),
        "companies": read_csv("companies.csv"),
        "tech": read_csv("tech_entrants.csv"),
        "builders": read_csv("builders.csv"),
        "universe": read_csv("universe.csv"),
        "leads": read_csv("leads.csv"),
        "products": read_csv("products.csv"),
        "coverage": read_csv("coverage.csv"),
        "pharma": read_pharma(),
        "builder_profiles": read_builder_profiles(),
        "investors": read_json_dir("investors"),
        "labs": read_json_dir("labs"),
        "trials": read_trials(),
        "frontiers": json.loads((ROOT / "data" / "frontiers.json").read_text()) if (ROOT / "data" / "frontiers.json").exists() else None,
    }
    link_universe(data)
    del data["products"], data["coverage"]  # merged into the universe / news rows
    f = ROOT / "data" / "forecast.json"  # fitted target model + rankings (sweep/fit_forecast.py)
    data["forecast"] = json.loads(f.read_text()) if f.exists() else None
    return data


def main():
    data = load_data()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (WEB / "template.html").read_text().replace("/*__DATA__*/null", blob)
    (WEB / "index.html").write_text(html)
    print(f"wrote {WEB / 'index.html'}: "
          + ", ".join(f"{k}={len(v)}" for k, v in data.items() if isinstance(v, list)))


if __name__ == "__main__":
    main()
