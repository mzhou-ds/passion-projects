"""Generate figures for philosophy-in-data."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

ERA_COLORS = {"Ancient": "#2a7f62", "Early Modern": "#b25c1e", "Modern": "#3b5bdb"}

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150,
    "font.family": "DejaVu Sans", "axes.spines.top": False,
    "axes.spines.right": False,
})


def fmt_year(x, _):
    x = int(round(x))
    return f"{abs(x)} BCE" if x < 0 else f"{x} CE"


def base(ax, title, xlabel="Year of original publication"):
    ax.set_title(title, fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_year))
    ax.grid(axis="y", alpha=0.25)


def scatter_metric(df, col, ylabel, title, fname, annotate=(), ylim=None, invert=False):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for era, g in df.groupby("era"):
        ax.scatter(g["year"], g[col], s=110, color=ERA_COLORS[era],
                   label=era, alpha=0.9, edgecolors="white", zorder=3)
    for slug in annotate:
        r = df.loc[df["slug"] == slug].iloc[0]
        ax.annotate(r["short"], (r["year"], r[col]),
                    xytext=(8, 6), textcoords="offset points", fontsize=9)
    base(ax, title)
    ax.set_ylabel(ylabel, fontsize=10)
    if ylim:
        ax.set_ylim(ylim)
    if invert:
        ax.invert_yaxis()
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / fname, bbox_inches="tight")
    plt.close(fig)


def main():
    df = pd.read_csv(DATA / "metrics.csv").sort_values("year")
    SHORT = {
        "plato-apology": "Plato", "aristotle-ethics": "Aristotle",
        "aurelius-meditations": "Aurelius", "augustine-confessions": "Augustine",
        "descartes-discourse": "Descartes", "spinoza-ethics": "Spinoza",
        "hume-enquiry": "Hume", "kant-critique": "Kant",
        "mill-utilitarianism": "Mill", "nietzsche-bge": "Nietzsche",
        "james-pragmatism": "James", "russell-problems": "Russell",
    }
    df["short"] = df["slug"].map(SHORT)

    scatter_metric(df, "flesch_ease", "Flesch Reading Ease (higher = easier)",
                   "Philosophy got harder to read",
                   "fig1_readability.png",
                   annotate=["descartes-discourse", "augustine-confessions",
                             "aurelius-meditations", "kant-critique"])

    scatter_metric(df, "avg_sentence_len", "Mean words per sentence",
                   "The 90-word sentence: early moderns never stopped",
                   "fig2_sentence_length.png",
                   annotate=["descartes-discourse", "aristotle-ethics",
                             "james-pragmatism", "spinoza-ethics"])

    scatter_metric(df, "concreteness", "Mean concreteness (1 = abstract, 5 = concrete)",
                   "Philosophy lives at 2.5: the abstract floor",
                   "fig3_concreteness.png", ylim=(2.2, 2.8),
                   annotate=["kant-critique", "augustine-confessions",
                             "aurelius-meditations"])

    # Voice: first-person rates over time
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for col, label, ls in [("i_per_1k", '"I" (I/me/my)', "-"),
                           ("we_per_1k", '"we" (we/us/our)', "--"),
                           ("you_per_1k", '"you"', ":")]:
        ax.plot(df["year"], df[col], marker="o", label=label, linestyle=ls,
                linewidth=2, markersize=6)
    for _, r in df.iterrows():
        if r["short"] in ("Plato", "Augustine", "Aurelius", "Descartes"):
            ax.annotate(r["short"], (r["year"], r["i_per_1k"]),
                        xytext=(0, 8), textcoords="offset points",
                        fontsize=8, ha="center", alpha=0.85)
    base(ax, 'The disappearing "I": philosophy stops talking about itself')
    ax.set_ylabel("Occurrences per 1,000 words", fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig4_voice.png", bbox_inches="tight")
    plt.close(fig)

    scatter_metric(df, "vader_mean", "Mean paragraph sentiment (VADER compound)",
                   "How philosophy feels: emotional valence of word choice",
                   "fig5_sentiment.png",
                   annotate=["descartes-discourse", "augustine-confessions",
                             "russell-problems", "aurelius-meditations"])

    # Era comparison panel
    era = df.groupby("era").agg(
        flesch_ease=("flesch_ease", "mean"), avg_sentence_len=("avg_sentence_len", "mean"),
        concreteness=("concreteness", "mean"), i_per_1k=("i_per_1k", "mean"),
        abstract_per_1k=("abstract_per_1k", "mean"),
        polysyllabic_share=("polysyllabic_share", "mean")).reindex(
        ["Ancient", "Early Modern", "Modern"])
    print(era.round(2).to_string())

    specs = [("flesch_ease", "Flesch Reading Ease\n(higher = easier)", None),
             ("avg_sentence_len", "Mean sentence length\n(words)", None),
             ("concreteness", "Mean concreteness\n(1-5)", (2.3, 2.7)),
             ("i_per_1k", '"I" per 1,000 words', None)]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (col, label, ylim) in zip(axes.flat, specs):
        vals = [era.loc[e, col] for e in era.index]
        ax.bar(era.index, vals, color=[ERA_COLORS[e] for e in era.index],
               edgecolor="white")
        ax.set_title(label, fontsize=10)
        if ylim:
            ax.set_ylim(ylim)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Three eras of philosophy, compared", fontsize=14,
                 fontweight="bold", y=1.01)
    fig.tight_layout(); fig.savefig(FIG / "fig6_eras.png", bbox_inches="tight")
    plt.close(fig)
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
