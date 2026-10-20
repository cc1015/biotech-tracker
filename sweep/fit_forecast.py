#!/usr/bin/env python3
"""Fit the Forecast tab's acquisition-target model from the tracker's own history -> data/forecast.json.

Time-split, so the test is honest:
  train: features as of 2026-01-01, label = acquired 2026-01-01 .. 2026-05-31
  test:  features as of 2026-06-01, label = acquired 2026-06-01 .. today   (never seen while fitting)
News-based features only use events before each cutoff. Registry, product and backer features are
current-day snapshots (no history is stored for them), which leaks a little; see the notes in the output.
The model is a regularised logistic regression on standardised features. It is compared with the
hand-set weights and with a "most news coverage" baseline on the test period, then refit on both
periods to rank today's candidates.

  python3 sweep/fit_forecast.py
"""
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))
import build  # noqa: E402

TRAIN_CUT, TEST_CUT, TODAY = "2026-01-01", "2026-06-01", date.today().isoformat()
FEATURES = [  # (key, label shown on the page)
    ("approved", "sells an approved product"),
    ("late_stage", "late-stage program (product line)"),
    ("log_trials", "size of trial portfolio"),
    ("pharma_partner", "partnered with a top-15 pharma"),
    ("any_partner", "has a partnership"),
    ("raised_12m", "money raised in the prior year"),
    ("news_12m", "news coverage in the prior year"),
    ("backed", "backed by a tracked builder or investor"),
    ("public", "publicly listed"),
    ("silo_heat", "works in an active M&A silo"),
    ("log_emp", "headcount"),
]


def day(s):
    try:
        y, m, *d = [int(x) for x in s.split("-")]
        return date(y, m, d[0] if d else 15).isoformat()
    except Exception:
        return ""


def main():
    data = build.load_data()
    U, N = data["universe"], data["news"]
    for n in N:
        n["_d"] = day(n["date"])
        n["_amt"] = float(n["amount_usd"] or 0)
        n["_ids"] = [e["id"] for e in n["_cos"] if e["id"] is not None]
        n["_listed"] = [e["id"] for e in n["_cos"][:len([x for x in (n["companies"] or "").split(";") if x.strip()])]]
    pharma = {p["uid"] for p in data["pharma"] if p["uid"] is not None}
    backed = {c["uid"] for g in (data["builders"], data["investors"]) for b in g for c in b.get("created", []) if c.get("uid") is not None}
    trial_n = {}
    for t in data["trials"]["trials"]:
        if t.get("uid") is not None:
            trial_n[t["uid"]] = trial_n.get(t["uid"], 0) + 1
    # M&A: the first listed company buys, the others are bought
    acq = [(n["_d"], tid) for n in N if n["category"] == "m&a" and n["_listed"] for tid in n["_listed"][1:] if tid is not None]
    buyers = {n["_listed"][0] for n in N if n["category"] == "m&a" and n["_listed"] and n["_listed"][0] is not None}
    owned = {c["cid"] for p in data["pharma"] for c in p["events"] if c.get("cid") is not None and c["type"] in ("acquisition", "merger") and c.get("status", "completed") == "completed"}
    sub = re.compile(r"\b(GK|K\.K\.|Japan|China|Korea|Taiwan|Europe|UK|USA|Deutschland|France|Italia)\b")

    def big(u):
        return (u["id"] in pharma or u["id"] in buyers or float(u["employees"] or 0) > 3000 or float(u["ct_trials"] or 0) > 120
                or trial_n.get(u["id"], 0) >= 8 or u["parent"] or sub.search(u["name"]))

    pool = [u for u in U if not big(u) and u["id"] not in owned and u["status"] != "defunct"
            and (u.get("prod") or u["_news"] or float(u["ct_trials"] or 0) > 0)]
    by_co = {}
    for n in N:
        for i in n["_ids"]:
            by_co.setdefault(i, []).append(n)

    def feats(u, cut, drop=()):
        x = _feats(u, cut)
        return [0.0 if j in drop else v for j, v in enumerate(x)]

    def _feats(u, cut):
        start = (date.fromisoformat(cut) - timedelta(days=365)).isoformat()
        past = [n for n in by_co.get(u["id"], []) if start <= n["_d"] < cut]
        recent_deals = [n for n in N if start <= n["_d"] < cut and n["category"] in ("m&a", "partnership")]
        heat = {}
        for n in recent_deals:
            for s in (n["silo"] or "").split(";"):
                if s:
                    heat[s] = heat.get(s, 0) + 1
        hmax = max(heat.values() or [1])
        silos = {s for n in past for s in (n["silo"] or "").split(";") if s}
        if u.get("cur", -1) >= 0:
            silos |= {s for s in (data["companies"][u["cur"]]["silo"] or "").split(";") if s and s != "TODO"}
        prod = u.get("prod") or {}
        txt = f'{prod.get("stage", "")} {prod.get("product", "")}'.lower()
        partners = [i for n in past if n["category"] == "partnership" for i in n["_ids"] if i != u["id"]]
        raised = sum(n["_amt"] for n in past if n["category"] in ("financing", "ipo"))
        return [
            1.0 if re.search(r"approved|commercial|marketed|\bmarkets?\b", txt) else 0.0,
            1.0 if re.search(r"phase 3|phase iii|pivotal", txt) else 0.0,
            math.log1p(float(u["ct_trials"] or 0)),
            1.0 if any(i in pharma for i in partners) else 0.0,
            1.0 if partners else 0.0,
            math.log10(1 + raised / 1e6),
            math.log1p(len(past)),
            1.0 if u["id"] in backed else 0.0,
            1.0 if u["status"] == "public" else 0.0,
            max([heat.get(s, 0) / hmax for s in silos] or [0.0]),
            math.log1p(float(u["employees"] or 0)),
        ]

    def hand(x):  # the original hand-set weights, applied to the same as-of features
        return 18 * x[0] + 25 * x[1] + 20 * x[3] + 8 * (x[4] and not x[3]) + 10 * (x[5] >= 2) + 5 * x[7] + 6 * x[8] + 12 * x[9]

    def dataset(cut, end, drop=()):
        bought = {tid for d, tid in acq if cut <= d < end}
        before = {tid for d, tid in acq if d < cut}
        rows = [u for u in pool if u["id"] not in before]
        X = np.array([feats(u, cut, drop) for u in rows])
        y = np.array([1 if u["id"] in bought else 0 for u in rows])
        return rows, X, y

    def report(scores, y):
        order = np.argsort(-scores)
        hits = y[order]
        n = len(y)
        return {"auc": round(float(roc_auc_score(y, scores)), 3) if 0 < y.sum() < n else None,
                "positives": int(y.sum()), "candidates": n,
                "hits_top25": int(hits[:25].sum()), "hits_top100": int(hits[:100].sum()),
                "hits_top10pct": int(hits[: max(1, n // 10)].sum())}

    _, Xtr, ytr = dataset(TRAIN_CUT, TEST_CUT)
    rows_te, Xte, yte = dataset(TEST_CUT, "9999")
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    model = LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000).fit((Xtr - mu) / sd, ytr)
    test = {
        "fitted model": report(model.decision_function((Xte - mu) / sd), yte),
        "hand-set weights": report(np.array([hand(x) for x in Xte]), yte),
        "most news coverage": report(Xte[:, 6] + 1e-6 * Xte[:, 5], yte),
        "random": {"auc": 0.5, "hits_top10pct": round(yte.sum() / 10, 1)},
    }
    # leakage check: product lines were often researched *because* a company was in the news (including for
    # being acquired), so refit without them and with only properly time-stamped features
    def fit_eval(drop):
        _, a, b = dataset(TRAIN_CUT, TEST_CUT, drop)
        _, c, d = dataset(TEST_CUT, "9999", drop)
        m_, s_ = a.mean(0), a.std(0) + 1e-9
        mdl = LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000).fit((a - m_) / s_, b)
        return report(mdl.decision_function((c - m_) / s_), d)
    leakage = {"without product-line features": fit_eval({0, 1}),
               "only features timed to the cutoff (news-based)": fit_eval({0, 1, 2, 7, 8, 10})}
    # refit on both periods, rank today's candidates
    Xall, yall = np.vstack([Xtr, Xte]), np.concatenate([ytr, yte])
    mu2, sd2 = Xall.mean(0), Xall.std(0) + 1e-9
    final = LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000).fit((Xall - mu2) / sd2, yall)
    acquired_all = {tid for _, tid in acq}
    now_rows = [u for u in pool if u["id"] not in acquired_all]
    Xnow = np.array([feats(u, TODAY) for u in now_rows])
    Z = (Xnow - mu2) / sd2
    p = final.predict_proba(Z)[:, 1]
    contrib = Z * final.coef_[0]
    top = np.argsort(-p)[:40]
    targets = [{"uid": now_rows[i]["id"], "p": round(float(p[i]), 3),
                "why": [FEATURES[j][1] for j in np.argsort(-contrib[i])[:4] if contrib[i][j] > 0.05]} for i in top]
    out = {
        "fitted": TODAY, "train": f"features {TRAIN_CUT}, acquired {TRAIN_CUT}..{TEST_CUT}", "test": f"features {TEST_CUT}, acquired {TEST_CUT}..{TODAY}",
        "train_positives": int(ytr.sum()), "test": test, "leakage_check": leakage,
        "verdict": "no demonstrated skill: the apparent signal comes from product-line features that leak the outcome",
        "coefficients": sorted([{"feature": FEATURES[j][1], "train_coef": round(float(model.coef_[0][j]), 2), "final_coef": round(float(final.coef_[0][j]), 2)}
                                for j in range(len(FEATURES))], key=lambda r: -abs(r["final_coef"])),
        "targets": targets,
        "notes": "News features use only events before each cutoff. Trial-portfolio size, product line, backers, listing and headcount are today's values, "
                 "so they can leak a little. Acquisitions are from the news log (first listed company is the buyer).",
    }
    (ROOT / "data" / "forecast.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("train_positives", "test", "leakage_check")}, indent=1))


if __name__ == "__main__":
    main()
