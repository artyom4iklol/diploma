"""Exact monochrome diagrams and scenario charts for the recommendation chapter."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.path import Path as MPath
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "chapter3_figures"
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "axes.linewidth": .65, "grid.linewidth": .45, "grid.color": ".85",
    "legend.frameon": False, "legend.fontsize": 9, "svg.fonttype": "none",
    "svg.hashsalt": "chapter3-auto-trade", "savefig.facecolor": "white"})
MANIFEST = []


def fmt(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def save(fig, name, source_files, data):
    fig.canvas.draw()
    for suffix in ["svg", "png"]:
        fig.savefig(OUT / f"{name}.{suffix}", dpi=220, bbox_inches="tight", pad_inches=.12,
                    metadata={"Date": None} if suffix == "svg" else None)
    MANIFEST.append({"id": name, "source_files": source_files,
                     "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files},
                     "svg_sha256": hashlib.sha256((OUT / f"{name}.svg").read_bytes()).hexdigest(), "plotted_data": data})
    plt.close(fig)


def box(ax, x, y, width, height, text, grey=".97", size=10):
    rect = FancyBboxPatch((x - width / 2, y - height / 2), width, height,
                         boxstyle="round,pad=0,rounding_size=0.008", facecolor=grey, edgecolor="black", lw=.8)
    ax.add_patch(rect); ax.text(x, y, text, va="center", ha="center", fontsize=size, linespacing=1.4)
    return {"top": (x, y + height / 2), "bottom": (x, y - height / 2)}


def arrow(ax, points):
    # Coordinates end exactly on the box border; all bends remain orthogonal.
    path = MPath(points, [MPath.MOVETO] + [MPath.LINETO] * (len(points) - 1))
    ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=11, lw=.85, color="black"))


def main():
    OUT.mkdir(exist_ok=True)
    source = "results/chapter3_application/scenario_transfer.csv"
    d = pd.read_csv(ROOT / source)
    fig, ax = plt.subplots(figsize=(6.8, 6.2)); ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    top = box(ax, .5, .93, .80, .09, "Проверенная выгрузка и единый охват", grey=".90")
    left1 = box(ax, .25, .74, .43, .11, "Количество, стоимость\nи доли Китая")
    right1 = box(ax, .75, .74, .43, .11, "Общий HHI\nи индексы технологий")
    left2 = box(ax, .25, .51, .43, .12, "Различие физической\nи денежной динамики")
    right2 = box(ax, .75, .51, .43, .12, "Разнонаправленное\nизменение концентрации")
    left3 = box(ax, .25, .29, .43, .12, "Проверка оценки,\nсостава товара и географии")
    right3 = box(ax, .75, .29, .43, .12, "Разложение товарных\nвесов и географии")
    bottom = box(ax, .5, .08, .86, .10, "Проверенный вывод и адресная последующая проверка", grey=".90", size=9.5)
    for node in [left1, right1]: arrow(ax, [top["bottom"], (.5, .84), (node["top"][0], .84), node["top"]])
    for a, b in [(left1, left2), (right1, right2), (left2, left3), (right2, right3)]: arrow(ax, [a["bottom"], b["top"]])
    for node in [left3, right3]: arrow(ax, [node["bottom"], (node["bottom"][0], .18), (.5, .18), bottom["top"]])
    save(fig, "G01_monitoring", ["manuscript/chapter3_evidence.json"], {"type": "author_proposed_workflow", "scope": "data review, not automated causal diagnosis"})

    fig, ax = plt.subplots(figsize=(6.7, 3.6), layout="constrained")
    cats = ["BEV", "PHEV", "HEV"]; x = np.arange(3)
    plotdata = []
    for alpha, offset, grey, hatch in [(.1, -.18, ".8", "///"), (.25, .18, ".3", "")]:
        z = d[(d.alpha == alpha) & (d.rho == 0)].set_index("category").loc[cats]
        bars = ax.bar(x + offset, z.remaining_share_pct, width=.32, color=grey, edgecolor="black", lw=.6, hatch=hatch, label=f"{int(alpha*100)}% потока BE/NL")
        for bar, value in zip(bars, z.remaining_share_pct): ax.text(bar.get_x() + bar.get_width()/2, value + .25, fmt(value), ha="center", va="bottom", fontsize=9)
        plotdata.extend(z.reset_index().to_dict("records"))
    ax.set_xticks(x, cats); ax.set_ylim(0, 16); ax.set_ylabel("Условная экспозиция, % категории"); ax.grid(axis="y")
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(.5, 1.0))
    save(fig, "G02_exposure", [source], plotdata)

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.8), sharey=True, layout="constrained")
    for ax, alpha, label in zip(axes, [.1, .25], ["а) α = 10%", "б) α = 25%"]):
        for cat, ls, marker in zip(cats, ["-", "--", ":"], ["o", "s", "^"]):
            z = d[(d.alpha == alpha) & (d.category == cat)].sort_values("rho")
            ax.plot(z.rho * 100, z.remaining_share_pct, color="black", ls=ls, marker=marker, ms=4, lw=1.3, label=cat)
        ax.set_xticks([0, 50, 100]); ax.set_ylim(-.3, 15); ax.grid(axis="y"); ax.set_xlabel("Условный перенос ρ, %"); ax.text(0, 1.05, label, transform=ax.transAxes)
    axes[0].set_ylabel("Неперенесённая часть, % категории")
    handles, labels = axes[0].get_legend_handles_labels(); fig.legend(handles, labels, ncol=3, loc="outside lower center")
    save(fig, "G03_transfer", [source], d.to_dict("records"))

    fig, ax = plt.subplots(figsize=(7, 4.8)); ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    headers = ["1. Эталонная\nоснова", "2. Исторический\nпилот", "3. Регулярное\nобновление"]
    roles = ["Аналитическое\nподразделение", "Подразделение\nпоставок", "Оценка торговой\nполитики"]
    values = [["Паспорт и\nформулы", "Разбор\nрасхождений", "Обновление,\nжурнал версий"],
              ["Сверка своих\nпоставок", "Проверка\nальтернатив", "Каналы и\nзапасы"],
              ["Цель и охват\nинструмента", "Модели, рынок\nи выпуск", "Обновление\nоценки меры"]]
    centres = [.38, .625, .87]
    for x, text in zip(centres, headers): box(ax, x, .87, .23, .14, text, grey=".9", size=9.5)
    for i, (role, row) in enumerate(zip(roles, values)):
        y = .65 - .225 * i
        ax.text(.015, y, role, ha="left", va="center", fontsize=9.1, linespacing=1.4)
        for x, text in zip(centres, row): box(ax, x, y, .23, .185, text, grey=".98", size=9)
    save(fig, "G04_implementation", ["manuscript/chapter3_evidence.json"], {"type": "author_proposed_responsibility_matrix", "columns": headers, "rows": roles, "cells": values})
    (OUT / "figure_manifest.json").write_text(json.dumps({"date": "2026-10-28", "style": "monochrome serif, no internal titles, external captions", "figures": MANIFEST}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"figures": len(MANIFEST), "formats": ["svg", "png"]}))


if __name__ == "__main__":
    main()
