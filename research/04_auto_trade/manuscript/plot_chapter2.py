"""Publication-size monochrome figures from frozen results; no model refits."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "chapter2_figures"
CATS = ["BEV", "PHEV", "HEV"]
STYLES = ["-", "--", ":"]
GREYS = ["0.25", "0.65", "0.92"]
HATCH = ["", "///", "..."]
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.axisbelow": True, "axes.linewidth": .65, "grid.linewidth": .45,
    "grid.color": ".85", "legend.frameon": False, "legend.fontsize": 9,
    "svg.fonttype": "none", "svg.hashsalt": "chapter2-auto-trade", "savefig.facecolor": "white"})
MANIFEST = []


def j(path):
    return json.loads((ROOT / path).read_text())


def num(x, decimals=1):
    return f"{x:.{decimals}f}".replace(".", ",")


def save(fig, name, source, data):
    fig.canvas.draw()
    # Tight bbox retains all artists, including legends outside the axes.
    for suffix in ["svg", "png"]:
        fig.savefig(OUT / f"{name}.{suffix}", dpi=220, bbox_inches="tight", pad_inches=.12, metadata={"Date": None} if suffix == "svg" else None)
    MANIFEST.append({"id": name, "source_files": source, "plotted_data": data,
                     "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source},
                     "svg_sha256": hashlib.sha256((OUT / f"{name}.svg").read_bytes()).hexdigest()})
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    annual = pd.read_csv(ROOT / "results/full/annual_eu_flows.csv")
    member = pd.read_csv(ROOT / "results/full/annual_member_flows.csv")
    panel = pd.read_csv(ROOT / "results/full/panel.csv")
    cn = annual[annual.origin == "CN"]
    ext = annual[annual.origin == "EXT_EU27_2020"]
    monthly = panel[(panel.origin == "CN") & (panel.reporter != "EU27_2020")].groupby(["month", "category"]).quantity.sum().unstack()
    dates = pd.to_datetime(monthly.index)
    fig, axes = plt.subplots(3, 1, figsize=(6.7, 6), sharex=True, layout="constrained")
    for ax, cat in zip(axes, CATS):
        ax.plot(dates, monthly[cat] / 1000, color="black", lw=1.25)
        for date in ["2023-09-01", "2024-07-01", "2024-11-01"]:
            ax.axvline(pd.Timestamp(date), color=".6", ls="--", lw=.65)
        ax.text(.015, .83, cat, transform=ax.transAxes)
        ax.set_ylim(bottom=0); ax.set_ylabel("Тыс. машин"); ax.grid(axis="y")
    axes[-1].set_xticks(pd.date_range("2021-01-01", "2025-01-01", freq="YS"), [str(y) for y in range(2021, 2026)])
    save(fig, "G02_monthly", ["results/full/panel.csv"], monthly.reset_index().to_dict("records"))

    totals = cn.groupby("year")[["quantity", "value_eur"]].sum()
    shares = totals / ext.groupby("year")[["quantity", "value_eur"]].sum() * 100
    fig, ax = plt.subplots(figsize=(6.7, 3.3), layout="constrained")
    for col, ls, marker, label in [("quantity", "-", "o", "По количеству"), ("value_eur", "--", "s", "По стоимости")]:
        ax.plot(shares.index, shares[col], color="black", ls=ls, marker=marker, ms=4, label=label)
        ax.annotate(num(shares.loc[2025, col], 2), (2025, shares.loc[2025, col]), xytext=(4, 4), textcoords="offset points", fontsize=9)
    ax.set_ylabel("Доля Китая, %"); ax.set_ylim(0, 45); ax.set_xlim(2020.8, 2025.5)
    ax.set_xticks(range(2021, 2026)); ax.grid(axis="y"); ax.legend(loc="upper left")
    save(fig, "G03_shares", ["results/full/annual_eu_flows.csv"], shares.reset_index().to_dict("records"))

    mix = cn.pivot(index="year", columns="category", values="quantity")[CATS].div(totals.quantity, axis=0) * 100
    fig, ax = plt.subplots(figsize=(6.7, 3.5), layout="constrained"); bottom = np.zeros(5)
    for cat, grey, hatch in zip(CATS, GREYS, HATCH):
        ax.bar(mix.index, mix[cat], bottom=bottom, color=grey, hatch=hatch, edgecolor="black", lw=.5, width=.62, label=cat)
        for y, v, b in zip(mix.index, mix[cat], bottom):
            if v > 5: ax.text(y, b + v / 2, num(v), ha="center", va="center", color="white" if grey == "0.25" else "black", fontsize=9, bbox=dict(facecolor=grey, edgecolor="none", pad=1.3))
        bottom += mix[cat].to_numpy()
    ax.set_ylim(0, 100); ax.set_ylabel("Состав китайских поставок, %"); ax.set_xticks(range(2021, 2026))
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(.5, 1.0))
    save(fig, "G04_mix", ["results/full/annual_eu_flows.csv"], mix.reset_index().to_dict("records"))

    a = j("results/full/accounting_decompositions.json")
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.8), layout="constrained")
    for ax, outcome, lab in zip(axes, ["quantity", "value_eur"], ["а) Количество", "б) Стоимость"]):
        d = [x for x in a if x["outcome"] == outcome]
        y = np.arange(2)
        for offset, key, label, grey in [(-.16, "within_category_pp", "Доли внутри категорий", ".3"), (.16, "category_mix_pp", "Товарные веса", ".8")]:
            ax.barh(y + offset, [x["two_factor"][key] for x in d], height=.28, color=grey, edgecolor="black", lw=.5, label=label)
        ax.axvline(0, color="black", lw=.7); ax.set_yticks(y, [f"{x['start']}–{x['end']}" for x in d]); ax.invert_yaxis()
        ax.set_xlabel("Процентные пункты"); ax.text(0, 1.05, lab, transform=ax.transAxes); ax.grid(axis="x")
    handles, labels = axes[0].get_legend_handles_labels(); fig.legend(handles, labels, loc="outside lower center", ncol=2)
    save(fig, "G05_share_components", ["results/full/accounting_decompositions.json"], a)

    v = j("results/full/china_value_change_accounting.json")
    fig, ax = plt.subplots(figsize=(6.7, 3.4), layout="constrained"); x = np.arange(2)
    for offset, key, label, grey in [(-.18, "quantity_component_eur", "Количество", ".3"), (.18, "within_CN8_customs_unit_value_component_eur", "Удельная стоимость", ".8")]:
        ax.bar(x + offset, [d[key] / 1e9 for d in v], width=.32, color=grey, edgecolor="black", lw=.6, label=label)
    ax.scatter(x, [d["value_change_eur"] / 1e9 for d in v], marker="D", color="black", s=28, label="Итог")
    ax.set_xticks(x, [f"{d['start']}–{d['end']}" for d in v]); ax.set_ylabel("Млрд евро"); ax.axhline(0, color="black", lw=.6); ax.grid(axis="y")
    handles, labels = ax.get_legend_handles_labels(); fig.legend(handles, labels, loc="outside upper center", ncol=3)
    save(fig, "G06_value_components", ["results/full/china_value_change_accounting.json"], v)

    country_names = dict(AT="Австрия", BE="Бельгия", BG="Болгария", CY="Кипр", CZ="Чехия", DE="Германия", DK="Дания", EE="Эстония", ES="Испания", FI="Финляндия", FR="Франция", GR="Греция", HR="Хорватия", HU="Венгрия", IE="Ирландия", IT="Италия", LT="Литва", LU="Люксембург", LV="Латвия", MT="Мальта", NL="Нидерланды", PL="Польша", PT="Португалия", RO="Румыния", SE="Швеция", SI="Словения", SK="Словакия")
    countries = sorted(country_names, key=country_names.get)
    matrix = []
    for cat in CATS:
        for year in [2023, 2025]:
            s = member[(member.origin == "CN") & (member.category == cat) & (member.year == year)].set_index("reporter").quantity.reindex(countries)
            matrix.append((s / s.sum() * 100).to_numpy())
    matrix = np.array(matrix).T
    fig, ax = plt.subplots(figsize=(6.8, 8.0), layout="constrained")
    image = ax.imshow(matrix, cmap="Greys", vmin=0, vmax=100, aspect="auto")
    ax.set_yticks(range(27), [country_names[c] for c in countries], fontsize=9)
    ax.set_xticks(range(6), [f"{c}\n{y}" for c in CATS for y in [2023, 2025]], fontsize=9)
    for i in range(27):
        for k in range(6):
            value = matrix[i, k]; ax.text(k, i, num(value) if value >= .1 else ("0" if value == 0 else "<0,1"), va="center", ha="center", fontsize=8, color="white" if value > 55 else "black")
    for k in [1.5, 3.5]: ax.axvline(k, color=".55", lw=.8)
    cb = fig.colorbar(image, ax=ax, fraction=.03, pad=.03); cb.set_label("Доля страны внутри технологии, %")
    save(fig, "G07_geography", ["results/full/annual_member_flows.csv"], {"countries": countries, "columns": [f"{c}_{y}" for c in CATS for y in [2023, 2025]], "shares_pct": matrix.tolist()})

    c = pd.read_csv(ROOT / "results/full/entry_concentration.csv")
    pooled = []
    for year, d in member[member.origin == "CN"].groupby("year"):
        for outcome in ["quantity", "value_eur"]:
            z = d.groupby("reporter")[outcome].sum(); pooled.append({"year": int(year), "outcome": outcome, "HHI": float(((z / z.sum()) ** 2).sum())})
    pooled_df = pd.DataFrame(pooled)
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.5), sharey=True, layout="constrained")
    for ax, outcome, label in zip(axes, ["quantity", "value_eur"], ["а) Количество", "б) Стоимость"]):
        for cat, style in zip(CATS, STYLES):
            d = c[(c.category == cat) & (c.outcome == outcome)].sort_values("year"); ax.plot(d.year, d.entry_HHI, color=".3", ls=style, lw=1.2, marker="o", ms=3, label=cat)
        d = pooled_df[pooled_df.outcome == outcome]; ax.plot(d.year, d.HHI, color="black", lw=2.3, marker="s", ms=3, label="Вся корзина")
        ax.set_xticks(range(2021, 2026), [str(y)[2:] for y in range(2021, 2026)]); ax.set_ylim(0, 1); ax.grid(axis="y"); ax.text(0, 1.04, label, transform=ax.transAxes)
    axes[0].set_ylabel("HHI, шкала 0–1"); handles, labels = axes[0].get_legend_handles_labels(); fig.legend(handles, labels, ncol=4, loc="outside lower center")
    save(fig, "G08_hhi", ["results/full/entry_concentration.csv", "results/full/annual_member_flows.csv"], {"pooled": pooled, "categories": c.to_dict("records")})

    h = pd.read_csv(ROOT / "results/geography_focus/pooled_HHI_product_geography.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.6), sharex=True, layout="constrained")
    for ax, outcome, label in zip(axes, ["quantity", "value_eur"], ["а) Количество", "б) Стоимость"]):
        d = h[h.outcome == outcome]; y = np.arange(2)
        for offset, key, legend, grey in [(-.17, "product_mix_component", "Товарные веса", ".75"), (.17, "within_product_geography_component", "География", ".25")]:
            ax.barh(y + offset, d[key], height=.29, color=grey, edgecolor="black", lw=.5, label=legend)
        ax.scatter(d.HHI_change, y, marker="D", s=28, color="black", label="Итог", zorder=4)
        ax.set_yticks(y, [f"{z.start}–{z.end}" for z in d.itertuples()]); ax.invert_yaxis(); ax.axvline(0, color="black", lw=.6); ax.set_xlabel("Изменение HHI"); ax.grid(axis="x"); ax.text(0, 1.05, label, transform=ax.transAxes)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: num(x, 2)))
    handles, labels = axes[0].get_legend_handles_labels(); fig.legend(handles, labels, ncol=3, loc="outside lower center")
    save(fig, "G09_hhi_components", ["results/geography_focus/pooled_HHI_product_geography.csv"], h.to_dict("records"))

    entry = pd.read_csv(ROOT / "results/geography_focus/entry_margin_summary.csv")
    d = entry[(entry.start == 2023) & (entry.outcome == "quantity")].set_index("category").loc[CATS]
    fig, ax = plt.subplots(figsize=(6.7, 3.3), layout="constrained")
    y = np.arange(3); base = np.zeros(3)
    for key, label, grey, hatch in [("continuing_country_change", "Продолжающие", ".3", ""), ("new_positive_country_component", "Новые положительные", ".85", "///")]:
        vals = d[key].to_numpy() / 1000; ax.barh(y, vals, left=base, color=grey, hatch=hatch, edgecolor="black", lw=.5, label=label); base += vals
    ax.axvline(0, color="black", lw=.7); ax.set_yticks(y, CATS); ax.invert_yaxis(); ax.grid(axis="x"); ax.set_xlabel("Изменение количества, тыс. машин"); ax.set_xlim(-85, 150)
    for i, row in enumerate(d.itertuples()):
        ax.annotate(num(row.change / 1000), (row.change / 1000, i), xytext=(4 if row.change > 0 else -4, 0), textcoords="offset points", ha="left" if row.change > 0 else "right", va="center", fontsize=9)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    save(fig, "G10_entry", ["results/geography_focus/entry_margin_summary.csv"], d.reset_index().to_dict("records"))

    block = j("results/augmented/paired_block_summary.json"); preferred = {}
    fig, ax = plt.subplots(figsize=(6.7, 3.8), layout="constrained"); forest = []
    for idx, (outcome, suffix, cat) in enumerate([(o, s, c) for c in ["PHEV", "HEV"] for o, s in [("quantity", "quantity"), ("value_eur", "value")]]):
        model = j(f"results/augmented/rest_preferred_{suffix}.json"); c = next(x for x in model["coefficients"] if x["term"] == cat + "__definitive")
        b = next(x for x in block["outcomes"][outcome]["coefficients"] if x["term"] == cat + "__definitive")
        point = c["multiplier"]
        for offset, ci, style in [(-.10, c["hac12"]["multiplier_ci95"], "-"), (.10, b["multiplier_ci95"], "--")]:
            ax.plot(ci, [idx + offset] * 2, color="black", ls=style, lw=1.3); ax.plot(point, idx + offset, marker="o" if style == "-" else "s", color="black", ms=4)
        forest.append({"category": cat, "outcome": outcome, "point": point, "hac12": c["hac12"]["multiplier_ci95"], "block": b["multiplier_ci95"]})
    ax.set_yticks(range(4), ["PHEV: количество", "PHEV: стоимость", "HEV: количество", "HEV: стоимость"]); ax.invert_yaxis(); ax.set_xscale("log"); ax.axvline(1, color=".5", lw=.8); ax.grid(axis="x"); ax.set_xlabel("Фазовый множитель, логарифмическая шкала")
    ax.plot([], [], color="black", marker="o", label="HAC(12)"); ax.plot([], [], color="black", ls="--", marker="s", label="Блочный интервал"); ax.legend(loc="lower left", bbox_to_anchor=(0, 1), ncol=2)
    save(fig, "G11_intervals", ["results/augmented/rest_preferred_quantity.json", "results/augmented/rest_preferred_value.json", "results/augmented/paired_block_summary.json"], forest)

    co = pd.read_csv(ROOT / "results/augmented/coefficients.csv")
    variants = ["rest_preferred", "rest_no_trend", "rest_no_season", "four_origin_augmented", "rest_since2022", "rest_exclude_BE_NL", "rest_observed_only"]
    labels = ["Основная", "Без тренда", "Без сезонности", "Четыре происхождения", "С 2022 года", "Без BE/NL", "Опубликованные пары"]
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.3), layout="constrained")
    allrows = []
    for ax, cat, suffix, label in [(axes[0, 0], "PHEV", "quantity", "а) PHEV, количество"), (axes[0, 1], "PHEV", "value", "б) PHEV, стоимость"), (axes[1, 0], "HEV", "quantity", "в) HEV, количество"), (axes[1, 1], "HEV", "value", "г) HEV, стоимость")]:
        d = co[(co.term == cat + "__definitive") & co.model.isin([v + "_" + suffix for v in variants])].set_index("model").loc[[v + "_" + suffix for v in variants]]
        for i, row in enumerate(d.itertuples()):
            ax.plot([row.hac12_lo, row.hac12_hi], [i, i], color="black", lw=1); ax.plot(row.multiplier, i, marker="s" if i == 0 else "o", ms=5 if i == 0 else 3, color="black")
        ax.set_yticks(range(7), labels, fontsize=8); ax.invert_yaxis(); ax.set_xscale("log"); ax.axvline(1, color=".5", lw=.7); ax.grid(axis="x"); ax.text(0, 1.07, label, transform=ax.transAxes, fontsize=9); ax.set_xlabel("Множитель; интервал HAC(12)", fontsize=9)
        allrows.extend(d.reset_index().to_dict("records"))
    save(fig, "G12_sensitivity", ["results/augmented/coefficients.csv"], allrows)

    fig, axes = plt.subplots(2, 2, figsize=(7.5, 5.6), layout="constrained"); halfdata = []
    for ax, cat, suffix, label in [(axes[0, 0], "PHEV", "quantity", "а) PHEV, количество"), (axes[0, 1], "PHEV", "value", "б) PHEV, стоимость"), (axes[1, 0], "HEV", "quantity", "в) HEV, количество"), (axes[1, 1], "HEV", "value", "г) HEV, стоимость")]:
        d = j(f"results/augmented/rest_halfyear_{suffix}.json"); rows = {x["term"].split("__")[1]: x for x in d["coefficients"] if x["term"].startswith(cat + "__")}
        periods = [f"{y}H{h}" for y in range(2021, 2026) for h in [1, 2]]
        for i, period in enumerate(periods):
            if period not in rows: ax.plot(i, 1, marker="s", markerfacecolor="white", markeredgecolor="black", ms=4); continue
            row = rows[period]; ci = row["hac12"]["multiplier_ci95"]; ax.plot([i, i], ci, color="black", lw=.8); ax.plot(i, row["multiplier"], marker="o", color="black", ms=3)
            halfdata.append({"category": cat, "outcome": suffix, "period": period, "point": row["multiplier"], "interval": ci})
        ax.set_xscale("linear"); ax.set_yscale("log"); ax.axhline(1, color=".5", lw=.7); ax.axvline(4.5, color=".6", ls="--", lw=.7)
        ax.set_xticks(range(0, 10, 2), [str(y) for y in range(2021, 2026)], fontsize=8); ax.text(0, 1.07, label, transform=ax.transAxes, fontsize=9); ax.grid(axis="y"); ax.set_ylabel("Множитель; HAC(12)", fontsize=9)
    save(fig, "G13_halfyear", ["results/augmented/rest_halfyear_quantity.json", "results/augmented/rest_halfyear_value.json"], halfdata)
    (OUT / "figure_manifest.json").write_text(json.dumps({"date": "2026-10-27", "style": "monochrome, no internal titles; serif; captions outside plots", "figures": MANIFEST}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"figures": len(MANIFEST), "formats": ["svg", "png"], "no_model_refits": True}))


if __name__ == "__main__":
    main()
