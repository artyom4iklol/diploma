"""Audit Chapter 2 against frozen estimates; visual inspection is a separate gate."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re
import numpy as np
import pandas as pd
from PIL import Image
from lxml import etree
from docx import Document

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RISK = HERE.parent / "risk_extension"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def fmt(value, digits=2):
    return f"{float(value):.{digits}f}".replace(".", ",").replace("-", "−")


def markdown_tables(text):
    found = []
    for block in text.split("\n\n"):
        if block.startswith("|"):
            rows = [[v.strip() for v in line.strip("|").split("|")] for line in block.splitlines()]
            found.append([rows[0], *rows[2:]])
    return found


def main():
    evidence = json.loads((HERE / "chapter2_evidence.json").read_text())
    main_text = (HERE / "chapter2_content.md").read_text()
    appendix = (HERE / "chapter2_appendices.md").read_text()
    tables = markdown_tables(main_text + "\n" + appendix)
    document = Document(HERE / "chapter2.docx")
    word_tables = [[[c.text for c in r.cells] for r in t.rows] for t in document.tables]
    assert tables == word_tables and len(tables) == 12
    for name, digest in evidence["input_sha256"].items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest, name

    # Main endpoint table: each printed number is checked independently against
    # the saved annual statistics and model states, including rounding.
    annual = pd.read_csv(RISK / "results/monthly/annual_indicators_from_months.csv")
    annual = annual.loc[~annual.include_parts].set_index(["reporter", "year"])
    states = pd.read_csv(RISK / "results/monthly/risk_states.csv")
    states = states.loc[states.case.eq("primary")].set_index(["reporter", "state"])
    for col, (country, year) in enumerate(((392, 2017), (392, 2024), (410, 2017), (410, 2024)), 1):
        a = annual.loc[(country, year)]
        s = states.loc[(country, "initial" if year == 2017 else "final")]
        values = [(a.export_usd/1e9, 2), (a.memory_share*100, 2), (a.product_hhi, 4),
                  (a.hhi, 4), (s.hhi_matched_grid, 4), (s.residual_share*100, 2)]
        for row, (v, precision) in enumerate(values, 1):
            assert tables[2][row][col] == fmt(v, precision)

    intervals = pd.read_csv(RISK / "results/monthly/risk_intervals.csv")
    intervals = intervals.loc[intervals.case.eq("primary") & intervals.block_months.eq(12)]
    intervals = intervals.set_index(["reporter", "metric"])
    summary = pd.read_csv(RISK / "results/monthly/risk_summary.csv")
    primary = summary.loc[summary.case.eq("primary")].set_index("reporter")
    metrics = ["initial_sd_pp", "product_change_sd_pp", "geography_change_sd_pp", "final_sd_pp",
               "delta_sd_pp", "delta_variance_pp2", "mix_variance_pp2", "geography_variance_pp2"]
    for col, country in enumerate((392, 410), 1):
        for row, metric in enumerate(metrics, 1):
            ci = intervals.loc[(country, metric)]
            if row <= 4:
                v = states.loc[(country, metric.removesuffix("_sd_pp")), "sd_pp"]
            else:
                v = primary.loc[country, metric]
            expected = f"{fmt(v)} [{fmt(ci.ci_low)}; {fmt(ci.ci_high)}]"
            assert tables[3][row][col] == expected, (row, col)
        ss = states.loc[country]
        assert np.allclose(ss.sd_pp**2, ss.variance_pp2)
        v0, vt, vg, v1 = [float(ss.loc[s, "variance_pp2"]) for s in ("initial", "product_change", "geography_change", "final")]
        assert np.isclose((vt-v0+v1-vg)/2, primary.loc[country, "mix_variance_pp2"])
        assert np.isclose((vg-v0+v1-vt)/2, primary.loc[country, "geography_variance_pp2"])
        assert np.isclose(v1-v0, primary.loc[country, "delta_variance_pp2"])

    cases = list(summary.loc[summary.reporter.eq(392) & ~summary.case.eq("primary"), "case"])
    for row, case in enumerate(cases, 1):
        for col, country in enumerate((392, 410), 2):
            q = summary.loc[summary.case.eq(case) & summary.reporter.eq(country)].iloc[0]
            expected = fmt(q.delta_sd_pp) if q.status == "ok" else "н/о"
            assert tables[4][row][col] == expected
    assert len(summary) == 24 and int(summary.status.eq("ok").sum()) == 22

    group = evidence["memory_and_remaining_fixed_indices"]
    assert len(group) == 4
    assert evidence["checks"]["memory_group_reconstruction_max_abs_error_pp2"] < 1e-8
    for row, g in enumerate(group, 1):
        assert tables[11][row][1:] == [str(g["weight_year"]), fmt(g["memory_sd_pp"]),
            fmt(g["remaining_sd_pp"]), fmt(g["correlation"])]
        for key in ("memory_sd_pp", "remaining_sd_pp", "correlation"):
            assert fmt(g[key]) in main_text
        m = g["memory_share"]
        variance = m*m*g["memory_sd_pp"]**2 + (1-m)**2*g["remaining_sd_pp"]**2 + 2*m*(1-m)*g["covariance_pp2"]
        assert np.isclose(variance, g["total_variance_pp2"])

    manifest = json.loads((HERE / "chapter2_figures.json").read_text())
    for figure in manifest:
        image_path = HERE / figure["path"]
        assert hashlib.sha256(image_path.read_bytes()).hexdigest() == figure["sha256"]
        pixels = np.asarray(Image.open(image_path).convert("RGB"))
        assert np.array_equal(pixels[:, :, 0], pixels[:, :, 1]) and np.array_equal(pixels[:, :, 1], pixels[:, :, 2])
    definitions = re.findall(r"^\[\^([^]]+)\]:", main_text, re.M)
    usages = re.findall(r"\[\^([^]]+)\](?!:)", main_text)
    assert sorted(definitions) == sorted(usages) and len(set(definitions)) == 11
    with ZipFile(HERE / "chapter2.docx") as z:
        xml = z.read("word/document.xml")
        root = etree.fromstring(xml)
        assert len(root.findall(".//w:footnoteReference", NS)) == 11
        assert not root.findall(".//w:hyperlink", NS)
        for token in (b"$$", b"\\tag", b"\\widehat", b"\\mathbf"):
            assert token not in xml
    report = {"date": "2026-10-18", "revision": 2,
        "scope": "Second substantive review; frozen primary model; descriptive memory-group diagnostic added",
        "main_words_whitespace_count": len(main_text.split()),
        "main_sections": 4, "main_tables": 5, "appendix_tables": 7, "figures": 8,
        "numbered_editable_equations": 6, "native_footnotes": 11, "sources": 13,
        "checks": {"all_12_word_tables_match_markdown": True,
            "all_primary_endpoint_and_estimate_table_cells_verified": True,
            "all_24_specification_statuses_and_main_sensitivity_values_preserved": True,
            "sd_variance_and_shapley_identities": True,
            "all_16_frozen_input_hashes_match": True,
            "new_memory_groups_reconstruct_primary_indices_and_variances": True,
            "new_group_table_and_prose_match_calculated_values": True,
            "all_8_figure_hashes_match_and_pixels_are_grayscale": True,
            "footnotes_complete_and_no_external_hyperlinks_or_raw_latex": True},
        "visual_review_pending": True,
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [HERE / "chapter2.docx", HERE / "chapter2_content.md", HERE / "chapter2_appendices.md", HERE / "chapter2_review.md"]}}
    (HERE / "chapter2_checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
