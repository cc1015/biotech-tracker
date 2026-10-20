#!/usr/bin/env python3
"""Collect candidate announcements ("leads") into data/leads.csv.

Leads are unconfirmed. The weekly sweep checks each one against a primary source
and the free trackers, then promotes it to news.csv or marks it rejected.

Sources (configured in sweep/lead_sources.json):
  - newswire RSS feeds (GlobeNewswire, PR Newswire, Business Wire)
  - Google News RSS searches
  - SEC EDGAR Form D filings (private raises; biotech/pharma industry groups)
  - Bluesky: account feeds (no login) and post search (needs BSKY_HANDLE +
    BSKY_APP_PASSWORD env vars; create an app password in Bluesky settings)

Env:
  SEC_USER_AGENT  SEC asks for "name email" in the User-Agent; set it to yours.

Usage: python3 sweep/collect_leads.py [--days N]
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "sweep" / "lead_sources.json").read_text())
LEADS = ROOT / "data" / "leads.csv"
FIELDS = ["found", "published", "platform", "source_name", "title", "url",
          "signals", "known_company", "amount_usd", "status", "notes"]
UA = "biotech-tracker/0.1 (personal research script)"
SEC_UA = os.environ.get("SEC_USER_AGENT", UA)


def get(url, headers=None, data=None, timeout=25):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def warn(msg):
    print(f"  ! {msg}", file=sys.stderr)


def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def terms_in(text, terms):
    t = " " + text.lower() + " "
    return [w for w in terms if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t)]


# ---------- sources ----------

def from_rss(name, url, since, require_biotech):
    out = []
    try:
        root = ET.fromstring(get(url))
    except Exception as e:  # noqa: BLE001 - one bad feed shouldn't stop the run
        warn(f"{name}: {e}")
        return out
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = re.sub("<[^>]+>", " ", item.findtext("description") or "")
        pub = parse_date(item.findtext("pubDate"))
        if pub and pub < since:
            continue
        text = f"{title} {desc}"
        sig = terms_in(text, CONFIG["signal_terms"])
        if not sig or (require_biotech and not terms_in(text, CONFIG["biotech_terms"])):
            continue
        src = item.findtext("source") or name
        out.append(dict(published=pub.date().isoformat() if pub else "", platform="newswire" if "news.google" not in url else "google-news",
                        source_name=src, title=title, url=(item.findtext("link") or "").strip(), signals=";".join(sig)))
    return out


def google_news(since, days):
    out = []
    for q in CONFIG["google_news_queries"]:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": f"{q} when:{days}d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        out += from_rss(f"Google News: {q}", url, since, require_biotech=True)
        time.sleep(0.5)
    return out


def sec_form_d(since):
    cfg = CONFIG["sec_form_d"]
    out = []
    end = datetime.now(timezone.utc).date()
    for group in cfg["industry_groups"]:
        url = "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode({
            "q": f'"{group}"', "forms": "D", "dateRange": "custom",
            "startdt": since.date().isoformat(), "enddt": end.isoformat()})
        try:
            hits = json.loads(get(url, {"User-Agent": SEC_UA}))["hits"]["hits"]
        except Exception as e:  # noqa: BLE001
            warn(f"SEC search {group}: {e}")
            continue
        for h in hits[: cfg["max_filings"]]:
            s = h["_source"]
            cik = s["ciks"][0].lstrip("0")
            adsh = s["adsh"]
            doc = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/primary_doc.xml"
            time.sleep(0.15)  # SEC fair-access: stay well under 10 req/s
            try:
                x = ET.fromstring(get(doc, {"User-Agent": SEC_UA}))
            except Exception as e:  # noqa: BLE001
                warn(f"SEC doc {adsh}: {e}")
                continue
            industry = x.findtext(".//industryGroup/industryGroupType") or ""
            if industry not in cfg["industry_groups"]:
                continue
            amt_txt = x.findtext(".//offeringSalesAmounts/totalAmountSold") or ""
            amt = int(float(amt_txt)) if re.fullmatch(r"[\d.]+", amt_txt) else 0
            if amt < cfg["min_amount_usd"]:
                continue
            name = x.findtext(".//primaryIssuer/entityName") or s["display_names"][0]
            loc = ", ".join(s.get("biz_locations") or [])
            amend = " (amendment)" if s.get("form", "").endswith("/A") or s.get("file_type") == "D/A" else ""
            out.append(dict(published=s["file_date"], platform="sec-form-d", source_name="SEC EDGAR",
                            title=f"{name} files Form D{amend}: ${amt:,} sold ({industry}; {loc})",
                            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=D",
                            signals="form d", amount_usd=str(amt)))
    return out


def bluesky(since):
    out = []
    def post_row(p, src):
        rec = p.get("record", {})
        text = rec.get("text", "")
        pub = parse_date(rec.get("createdAt"))
        if (pub and pub < since) or not terms_in(text, CONFIG["signal_terms"]) or not terms_in(text, CONFIG["biotech_terms"]):
            return None
        handle = p["author"]["handle"]
        rkey = p["uri"].rsplit("/", 1)[-1]
        ext = (p.get("embed") or {}).get("external") or {}
        return dict(published=pub.date().isoformat() if pub else "", platform="bluesky", source_name=f"@{handle} ({src})",
                    title=re.sub(r"\s+", " ", text)[:280], url=f"https://bsky.app/profile/{handle}/post/{rkey}",
                    signals=";".join(terms_in(text, CONFIG["signal_terms"])), notes=ext.get("uri", ""))

    for actor in CONFIG["bluesky_accounts"]:
        try:
            feed = json.loads(get("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?" +
                                  urllib.parse.urlencode({"actor": actor, "limit": 50})))["feed"]
        except Exception as e:  # noqa: BLE001
            warn(f"Bluesky @{actor}: {e}")
            continue
        out += [r for r in (post_row(f["post"], "account") for f in feed) if r]

    handle, pw = os.environ.get("BSKY_HANDLE"), os.environ.get("BSKY_APP_PASSWORD")
    if not CONFIG["bluesky_search_queries"]:
        return out
    if not (handle and pw):
        warn("Bluesky search skipped: set BSKY_HANDLE and BSKY_APP_PASSWORD to enable it")
        return out
    try:
        sess = json.loads(get("https://bsky.social/xrpc/com.atproto.server.createSession",
                              {"Content-Type": "application/json"},
                              json.dumps({"identifier": handle, "password": pw}).encode()))
    except Exception as e:  # noqa: BLE001
        warn(f"Bluesky login failed: {e}")
        return out
    auth = {"Authorization": f"Bearer {sess['accessJwt']}"}
    for q in CONFIG["bluesky_search_queries"]:
        try:
            posts = json.loads(get("https://bsky.social/xrpc/app.bsky.feed.searchPosts?" + urllib.parse.urlencode(
                {"q": q, "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": 50, "sort": "latest"}), auth))["posts"]
        except Exception as e:  # noqa: BLE001
            warn(f"Bluesky search '{q}': {e}")
            continue
        out += [r for r in (post_row(p, f"search: {q}") for p in posts) if r]
    return out


# ---------- main ----------

def known_names():
    names = set()
    for f, col in (("companies.csv", "name"), ("news.csv", "companies")):
        with open(ROOT / "data" / f, newline="") as fh:
            for r in csv.DictReader(fh):
                names.update(n.strip() for n in (r.get(col) or "").split(";") if len(n.strip()) > 3)
    return names


GENERIC = {"the", "bio", "biotech", "therapeutics", "pharma", "pharmaceuticals", "medical", "health", "labs",
           "precision", "new", "first", "global", "life", "sciences", "genomics", "clinical", "research"}


def short_name(name):
    """'Iambic Therapeutics' -> 'iambic'; keep the full name when the first word is generic."""
    first = name.split()[0].lower().strip(",.")
    return first if len(first) >= 4 and first not in GENERIC else name.lower()


def norm(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()[:90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=CONFIG["lookback_days"])
    args = ap.parse_args()
    since = datetime.now(timezone.utc) - timedelta(days=args.days)

    existing = []
    if LEADS.exists():
        with open(LEADS, newline="") as fh:
            existing = list(csv.DictReader(fh))
    seen_urls = {r["url"] for r in existing}
    seen_titles = {norm(r["title"]) for r in existing}
    names = known_names()

    found = []
    for label, fn in [
        ("newswires", lambda: sum((from_rss(n, u, since, require_biotech="Biotech" not in n)
                                    for n, u in CONFIG["rss"].items()), [])),
        ("google news", lambda: google_news(since, args.days)),
        ("sec form d", lambda: sec_form_d(since)),
        ("bluesky", lambda: bluesky(since)),
    ]:
        rows = fn()
        print(f"{label}: {len(rows)} candidates")
        found += rows

    today = datetime.now().date().isoformat()
    new = []
    for r in found:
        key = norm(r["title"])
        if not r["url"] or r["url"] in seen_urls or key in seen_titles:
            continue
        seen_urls.add(r["url"]); seen_titles.add(key)
        known = sorted(n for n in names if short_name(n) in terms_in(r["title"], [short_name(n)]))
        new.append({f: "" for f in FIELDS} | r | {"found": today, "known_company": ";".join(known), "status": "new"})

    # untriaged leads first (newest first), then triaged ones in their existing order
    pending = sorted((r for r in new + existing if r["status"] == "new"), key=lambda r: r["published"], reverse=True)
    rows = pending + [r for r in existing if r["status"] != "new"]
    with open(LEADS, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(f"added {len(new)} new leads -> {LEADS} ({sum(r['status'] == 'new' for r in rows)} awaiting triage)")


if __name__ == "__main__":
    main()
