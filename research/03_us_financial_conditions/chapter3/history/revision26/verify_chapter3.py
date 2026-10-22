"""Check chapter 3's quantitative claims against saved experiment outputs.

Run from any directory. No estimation, network requests, or data changes.
"""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CHAPTER = ROOT / "chapter3/Chapter_3_Recommendations.md"


def rows(path):
    with (ROOT / path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def one(data, **criteria):
    selected = [r for r in data if all(r[k] == str(v) for k, v in criteria.items())]
    assert len(selected) == 1, (criteria, len(selected))
    return selected[0]


def main():
    text = CHAPTER.read_text(encoding="utf-8")
    body = text.split("## Источники и примечания")[0]
    scores = rows("revision25/results/scores.csv")
    forecasts = rows("revision25/results/forecasts.csv")
    inference = rows("revision25/results/rolling52_inference.csv")
    episodes = rows("revision19/results/ANFCI_episode_scores.csv")
    revisions = rows("revision19/results/ANFCI_revision_effect.csv")
    checks = {}

    def loss(config, h, model, variant="expanding"):
        return float(one(scores, variant=variant, config=config, h=h, model=model)["mean_loss"])

    for h, expected in [(1, 26.3), (4, 51.5)]:
        change = 100 * (1 - loss("Q_clip_g", h, "AR_ESI") / loss("Q_raw", h, "AR_ESI"))
        assert round(change, 1) == expected
        checks[f"base_loss_reduction_h{h}_percent"] = change
    for model, expected in [("AR_ESI_NFCI", 23.2), ("AR_ESI_ANFCI", 42.5)]:
        change = 100 * (1 - loss("Q_raw", 4, model) / loss("Q_raw", 4, "AR_ESI"))
        assert round(change, 1) == expected
        checks[f"original_h4_gain_{model}_percent"] = change

    for variant in ["expanding", "rolling52"]:
        for config in ["Q_clip_g", "M2_clip_g"]:
            for h in [1, 4]:
                for model in ["AR_ESI_NFCI", "AR_ESI_ANFCI"]:
                    assert loss(config, h, model, variant) > loss(config, h, "AR_ESI", variant)
    checks["us_expansions_lose_to_guarded_base_all_guarded_designs"] = True

    for h, model, expected in [(1,"AR_ESI_NFCI",25.9),(4,"AR_ESI_NFCI",43.6),
                               (1,"AR_ESI_ANFCI",12.1),(4,"AR_ESI_ANFCI",16.4)]:
        row = one(scores, variant="expanding", config="M2_clip_g", h=h, model=model)
        value = 100 * float(row["hit_rate"])
        assert round(value, 1) == expected
        checks[f"hit_rate_M2_clip_{model}_h{h}_percent"] = value

    for h, n in [(1,16),(4,13)]:
        selected = [r for r in episodes if r["variant"] == "expanding" and
                    r["episode"] == "2022_2025" and r["h"] == str(h)]
        assert len(selected) == 5
        assert all(int(r["n"]) == n and float(r["hit_rate"]) == 0 for r in selected)
        checks[f"recent_h{h}_n_and_zero_hits"] = {"n":n,"zero_hits_all_five":True}

    diag = json.loads((ROOT / "chapter2/evidence/forecast_2021_01_15_diagnostic.json").read_text())
    assert round(diag["predictors"]["gx"], 2) == 47.01
    h1 = next(r for r in diag["horizons"] if r["h"] == 1)
    assert round(h1["training_gx_max"], 2) == 4.93
    for config, expected in [("Q_raw",28.05),("Q_clip_g",0.61)]:
        row = one(forecasts, variant="expanding", config=config, h=1,
                  model="AR_ESI", forecast_date="2021-01-15")
        assert round(float(row["forecast"]),2) == expected
        assert round(float(row["actual"]),2) == -1.15
        checks[f"case_2021_01_15_{config}"] = {"forecast":float(row["forecast"]),"actual":float(row["actual"])}

    nfci = one(revisions, variant="expanding", h=4, model="AR_ESI_NFCI")
    anfci = one(revisions, variant="expanding", h=4, model="AR_ESI_ANFCI")
    assert float(anfci["loss_historical"]) < float(nfci["loss_historical"])
    assert float(anfci["loss_revised"]) > float(nfci["loss_revised"])
    checks["historical_vs_revised_h4_ranking_reversal"] = True

    assert all(float(r["p_holm20"]) >= .05 for r in inference if r["h"] == "1")
    assert all(float(r["p_holm20"]) >= .05 for r in inference if r["h"] == "4" and r["L"] == "4")
    rejected = [r for r in inference if r["h"] == "4" and r["L"] == "8" and float(r["p_holm20"]) < .05]
    assert len(rejected) == 2
    assert all(r["benchmark"] == "HIST" and r["model"] == "AR_ESI_ANFCI" and float(r["difference"]) > 0 for r in rejected)
    checks["inference_matches_limited_claims"] = True

    used = set(re.findall(r"\[\^(3-\d+)\](?!:)", text))
    defined = re.findall(r"^\[\^(3-\d+)\]:", text, re.M)
    assert used == set(defined) and len(defined) == len(set(defined)) == 15
    paths = sorted(set(p for p in re.findall(r"`([^`\n]+)`", text)
                       if re.search(r"\.(csv|json|pdf|md)$", p)))
    assert all((ROOT / p).is_file() for p in paths)
    assert len(re.findall(r"^## 3\.[123]\.", text, re.M)) == 3
    assert len(re.findall(r"^Таблица 3\.", text, re.M)) == 2
    assert text.count("```mermaid") == 1 and text.count("```") == 2
    assert not re.search(r"TODO|TBD|FIXME|ЗАГЛУШКА", text)

    result = {"status":"passed", "date":"2026-10-19",
              "scope":"Text structure, reference availability and selected numerical claims; no model refits or new statistical tests.",
              "body_whitespace_words":len(body.split()), "footnotes":len(defined),
              "tables":2, "mermaid_diagrams":1,
              "chapter_sha256":hashlib.sha256(CHAPTER.read_bytes()).hexdigest(),
              "referenced_archive_files":paths, "quantitative_checks":checks}
    dest = ROOT / "chapter3/VERIFICATION.json"
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:result[k] for k in ["status","body_whitespace_words","footnotes","tables","mermaid_diagrams","chapter_sha256"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
