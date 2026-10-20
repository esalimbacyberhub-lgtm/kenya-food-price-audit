"""Diagnostic charts for the World Bank RTFP market-level file for Kenya.

Read-only on the raw data: loads the CSV and writes PNGs to outputs/figures/.

    1. check_medians.png       monthly cross-market medians of c_goat, observed goat,
                               c_maize, c_beans, c_food_price_index (Feb 2023-Dec 2025 shaded)
    2. check_obs_vs_close.png  observed vs c_ scatter for maize and beans, +/-25% band
    3. check_obs_counts.png    markets with an observed price per month, per item

Usage:
    python scripts/plot_checks.py [path/to/KEN_RTFP_mkt_*.csv]
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv"
OUT_DIR = ROOT / "outputs/figures"

# No observed goat or maize prices Feb 2023 - Dec 2025; the span ends at the start of
# Jan 2026 so that December 2025 is fully shaded.
GAP_START, GAP_END = pd.Timestamp("2023-02-01"), pd.Timestamp("2026-01-01")
GAP_LABEL = "No observed goat\nor maize prices"
BAND = 0.25  # relative disagreement band for the scatter: |c - obs| / obs <= 25%

# Palette: first three categorical slots of the reference palette (validated all-pairs,
# light surface). Aqua is < 3:1 against the surface, so its panel is titled by name.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE = "#fcfcfb"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
SHADE = "#f0efec"

ITEMS = {"maize_fao": "Maize", "beans": "Beans", "livestock_goat_s_fao": "Goat"}
ITEM_COLOR = {"maize_fao": BLUE, "beans": ORANGE, "livestock_goat_s_fao": AQUA}

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "grid.linestyle": "-",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK_2,
    "ytick.labelcolor": INK_2,
    "legend.frameon": False,
    "legend.labelcolor": INK_2,
    "lines.linewidth": 2,
})


def load(path):
    df = pd.read_csv(path, parse_dates=["price_date"])
    # The national aggregate is not a market; keep only real markets
    return df[df.mkt_name != "Market Average"]


def shade_gap(ax, label=False):
    ax.axvspan(GAP_START, GAP_END, color=SHADE, zorder=0, lw=0)
    if label:
        ax.text(GAP_START + (GAP_END - GAP_START) / 2, 1.0, GAP_LABEL,
                transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=8, color=INK_2)


# --------------------------------------------------------------------------- 1
def plot_medians(df, out):
    g = df.groupby("price_date")
    med = pd.DataFrame({
        "c_goat": g.c_livestock_goat_s_fao.median(),
        "obs_goat": g.livestock_goat_s_fao.median(),  # median over markets that reported
        "c_maize": g.c_maize_fao.median(),
        "c_beans": g.c_beans.median(),
        "c_fpi": g.c_food_price_index.median(),
    })
    obs_max = df.livestock_goat_s_fao.max()

    # One panel per unit; shared x, independent y. Never a dual axis.
    panels = [
        ("Goat price (KES per head)", [("c_goat", "c_ (modelled)", BLUE),
                                       ("obs_goat", "Observed", ORANGE)]),
        ("Maize price (KES per kg)", [("c_maize", "c_ (modelled)", BLUE)]),
        ("Beans price (KES per kg)", [("c_beans", "c_ (modelled)", BLUE)]),
        ("Food price index (Jan 2018 = 1)", [("c_fpi", "c_ (modelled)", BLUE)]),
    ]
    fig, axes = plt.subplots(len(panels), 1, figsize=(11, 11), sharex=True)
    for i, (ax, (title, series)) in enumerate(zip(axes, panels)):
        shade_gap(ax, label=(i == 0))
        for col, label, color in series:
            s = med[col]
            # Observed goat is sparse: draw points so gaps stay visible
            if col == "obs_goat":
                ax.plot(s.index, s, "o", ms=3, color=color, label=label, zorder=3)
            else:
                ax.plot(s.index, s, color=color, label=label, zorder=3)
        ax.set_title(title, pad=18 if i == 0 else 8)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"
                                     if i < 3 else "{x:,.1f}"))
    axes[0].axhline(obs_max, color=MUTED, lw=1, zorder=2)
    axes[0].annotate(f"Highest observed goat price anywhere: {obs_max:,.0f}",
                     (med.index[0], obs_max), xytext=(0, 4), textcoords="offset points",
                     fontsize=8, color=INK_2)
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, 0.88), fontsize=9)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Monthly median across 233 markets", x=0.06, ha="left",
                 fontsize=13, fontweight="bold")
    fig.text(0.06, 0.945, "Observed goat = median over markets reporting that month. "
             "Goat has Index Weight = 0, yet the index follows its 2023–24 spike.",
             fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- 2
def plot_obs_vs_close(df, out):
    items = ["maize_fao", "beans"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
    for ax, item in zip(axes, items):
        d = df[["mkt_name", "price_date", item, f"c_{item}"]].dropna()
        x, y = d[item], d[f"c_{item}"]
        rel = (y - x) / x
        inside = rel.abs() <= BAND
        hi = max(x.max(), y.max()) * 1.05

        line = pd.Series([0, hi])
        ax.fill_between(line, line * (1 - BAND), line * (1 + BAND), color=SHADE, lw=0, zorder=0)
        ax.plot(line, line, color=MUTED, lw=1, zorder=1)
        ax.scatter(x[inside], y[inside], s=14, color=BLUE, alpha=0.35, lw=0, zorder=2,
                   label=f"Within ±{BAND:.0%}  (n = {inside.sum():,})")
        ax.scatter(x[~inside], y[~inside], s=22, color=ORANGE, edgecolor=SURFACE, lw=0.8,
                   zorder=3, label=f"Outside ±{BAND:.0%}  (n = {(~inside).sum():,})")

        # Label the worst disagreement in each of the three worst markets
        worst = (d.assign(abs_rel=rel.abs()).sort_values("abs_rel", ascending=False)
                 .drop_duplicates("mkt_name").head(3))
        # Staggered offsets so labels on nearby points don't collide
        for (_, r), offset in zip(worst.iterrows(), [(6, -2), (6, -11), (6, 8)]):
            ax.annotate(f"{r.mkt_name} {r.price_date:%b %Y}", (r[item], r[f'c_{item}']),
                        xytext=offset, textcoords="offset points", fontsize=8, color=INK_2)

        ax.set_xlim(0, hi)
        ax.set_ylim(0, hi)
        ax.set_aspect("equal")
        ax.set_xlabel("Observed price (KES per kg)")
        ax.set_ylabel(f"c_{item} (KES per kg)")
        exact = (rel == 0).mean()
        ax.set_title(f"{ITEMS[item]}: {len(d):,} observed rows, {exact:.0%} exactly equal")
        ax.legend(loc="upper left", fontsize=9, markerscale=1.3)
    fig.suptitle(f"Observed price vs modelled c_ (grey band = ±{BAND:.0%} of observed, "
                 "line = equal)", x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


# --------------------------------------------------------------------------- 3
def plot_obs_counts(df, out):
    all_months = pd.date_range(df.price_date.min(), df.price_date.max(), freq="MS")
    counts = (df.groupby("price_date")[list(ITEMS)].count()
              .reindex(all_months, fill_value=0))

    # Maize and goat counts coincide for long stretches, so one panel per item
    # (shared x and y) rather than overlapping lines on one plot.
    fig, axes = plt.subplots(len(ITEMS), 1, figsize=(11, 7.5), sharex=True, sharey=True)
    for i, (ax, (item, name)) in enumerate(zip(axes, ITEMS.items())):
        shade_gap(ax, label=(i == 0))
        s = counts[item]
        ax.step(s.index, s, where="post", color=ITEM_COLOR[item], zorder=3)
        ax.fill_between(s.index, s, step="post", color=ITEM_COLOR[item], alpha=0.12, lw=0)
        ax.set_title(f"{name}: {s.sum():,} observed market-months, "
                     f"{df.loc[df[item].notna(), 'mkt_name'].nunique()} markets",
                     fontsize=10, pad=18 if i == 0 else 6)
        ax.set_ylim(0, counts.values.max() * 1.1)
    axes[1].set_ylabel("Markets with an observed price")
    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Markets with an observed (non-empty) price per month, out of 233",
                 x=0.06, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    df = load(path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "check_medians.png": plot_medians,
        "check_obs_vs_close.png": plot_obs_vs_close,
        "check_obs_counts.png": plot_obs_counts,
    }
    for name, fn in outputs.items():
        fn(df, OUT_DIR / name)
        print(f"wrote {OUT_DIR / name}")


if __name__ == "__main__":
    main()
