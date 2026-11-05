"""Export aggregated numbers for a dashboard to outputs/dashboard_data.json.

Read-only on data/raw: the CSVs are only opened for reading. The output holds
aggregates only (no market-level rows).

Rules:
    - The "Market Average" row group is dropped; the 233 real markets remain.
    - Monthly records run 2007-01 to 2026-09 (2026-10 is dropped).
    - "c_" columns are the modelled/close prices; "observed" means the raw
      column (livestock_goat_s_fao, maize_fao, beans) is non-null.

Usage:
    python3 -I scripts/export_dashboard_data.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CURRENT = ROOT / "data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv"
PREVIOUS = ROOT / "data/raw/versions/2026-09-28/KEN_RTFP_mkt_2007_2026-09-28.csv"
OUT = ROOT / "outputs/dashboard_data.json"

FIRST_MONTH, LAST_MONTH = "2007-01", "2026-09"
GOAT, MAIZE, BEANS, FPI = "livestock_goat_s_fao", "maize_fao", "beans", "food_price_index"
REVISION_MONTHS = ["2022-10", "2023-01", "2023-02", "2023-03", "2023-04",
                   "2023-06", "2023-12", "2024-01", "2024-06", "2025-12"]

CITATION = (
    "Andrée, B. P. J. (2021). Monthly food price estimates by product and market "
    "(Version 2026-10-05). KEN_2021_RTFP_v02_M. Washington, DC: World Bank "
    "Microdata Library. https://doi.org/10.48529/2ZH0-JF55 (accessed 20 October 2026)"
)
DISCLAIMER = "This analysis is my own and is not endorsed by the World Bank."


def load(path):
    df = pd.read_csv(path, parse_dates=["price_date"], low_memory=False)
    df = df[df.mkt_name != "Market Average"].copy()
    df["ym"] = df.price_date.dt.strftime("%Y-%m")
    return df


def num(v, nd=2):
    """Round to nd places; NaN -> None so the JSON has real nulls."""
    return None if pd.isna(v) else round(float(v), nd)


def monthly_records(df):
    df = df[df.ym.between(FIRST_MONTH, LAST_MONTH)]
    g = df.groupby("ym")
    t = pd.DataFrame({
        "goat_c_median": g[f"c_{GOAT}"].median(),
        "maize_c_median": g[f"c_{MAIZE}"].median(),
        "beans_c_median": g[f"c_{BEANS}"].median(),
        "food_price_index_c_median": g[f"c_{FPI}"].median(),
    })
    for name, item in [("goat", GOAT), ("maize", MAIZE)]:
        rep = df[df[item].notna()]
        gr = rep.groupby("ym")
        t[f"{name}_observed_median"] = gr[item].median()
        t[f"{name}_n_reporting"] = g[item].count()
        # modelled median over the same reporting markets only
        t[f"{name}_c_median_reporting_markets"] = gr[f"c_{item}"].median()
    t["beans_n_observed"] = g[BEANS].count()

    months = pd.period_range(FIRST_MONTH, LAST_MONTH, freq="M").strftime("%Y-%m")
    assert list(t.index) == list(months), "unexpected months in monthly table"
    records = []
    for ym, r in t.iterrows():
        rec = {"month": ym}
        for col, v in r.items():
            rec[col] = int(v) if col.endswith(("n_reporting", "n_observed")) else num(v)
        records.append(rec)
    return records


def gap(df, item):
    """Longest run of months with no observed price for item that has an
    observed month on both sides (leading/trailing empty months don't count).
    Returns (first_month, last_month)."""
    d = df[df.ym.between(FIRST_MONTH, LAST_MONTH)]
    n = d.groupby("ym")[item].count()
    months = list(n.index)
    seen = [i for i, m in enumerate(months) if n[m] > 0]
    inner = months[seen[0]:seen[-1] + 1]
    best, run = [], []
    for m in inner:
        run = run + [m] if n[m] == 0 else []
        if len(run) > len(best):
            best = run
    return best[0], best[-1]


def pct_no_observed_all_rows():
    """Percent of rows with no observed price, over every row in the raw file
    (Market Average and 2026-10 included), as in docs/audit_findings.md."""
    raw = pd.read_csv(CURRENT, usecols=[BEANS, MAIZE, GOAT])
    return int(len(raw)), {
        "beans": num(100 * raw[BEANS].isna().mean()),
        "maize": num(100 * raw[MAIZE].isna().mean()),
        "goat": num(100 * raw[GOAT].isna().mean()),
    }


def summary(df):
    n_all, pct_all = pct_no_observed_all_rows()
    full = df  # includes 2026-10 only for "ever observed"; it has no observations
    cut = df[df.ym.between(FIRST_MONTH, LAST_MONTH)]
    items = [BEANS, MAIZE, GOAT]
    observed_any = cut[items].notna().any(axis=1)
    goat_gap, maize_gap = gap(df, GOAT), gap(df, MAIZE)
    assert goat_gap == maize_gap, f"goat and maize gaps differ: {goat_gap} vs {maize_gap}"
    return {
        "markets": int(cut.mkt_name.nunique()),
        "markets_ever_observed": int(cut.loc[observed_any, "mkt_name"].nunique()),
        "markets_ever_observed_incl_2026_10": int(
            full[full[items].notna().any(axis=1)].mkt_name.nunique()),
        "rows": int(len(cut)),
        "pct_rows_no_observed_price": pct_all,
        "pct_rows_no_observed_price_basis": (
            f"Calculated over every row in the file ({n_all:,}), including "
            "Market Average and 2026-10"),
        "highest_observed_goat_price": num(cut[GOAT].max()),
        "observation_gap_goat_and_maize": {"start": goat_gap[0], "end": goat_gap[1]},
    }


def revision_table(cur, prev):
    medians = {
        "2026-09-28": prev.groupby("ym")[f"c_{GOAT}"].median(),
        "2026-10-05": cur.groupby("ym")[f"c_{GOAT}"].median(),
    }
    rows = []
    for m in REVISION_MONTHS:
        a, b = medians["2026-09-28"][m], medians["2026-10-05"][m]
        rows.append({
            "month": m,
            "release_2026_09_28": num(a),
            "release_2026_10_05": num(b),
            "pct_change": num(100 * (b / a - 1)),
        })
    return rows


def main():
    cur, prev = load(CURRENT), load(PREVIOUS)
    out = {
        "meta": {
            "citation": CITATION,
            "version": "2026-10-05",
            "accessed": "20 October 2026",
            "disclaimer": DISCLAIMER,
        },
        "summary": summary(cur),
        "monthly": monthly_records(cur),
        "goat_revision_table": {
            "item": f"median c_{GOAT} across 233 markets",
            "pct_change": "(2026-10-05 / 2026-09-28 - 1) * 100",
            "rows": revision_table(cur, prev),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, allow_nan=False) + "\n",
                   encoding="utf-8")

    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size:,} bytes, "
          f"{len(out['monthly'])} monthly records")
    for rec in out["monthly"][:3]:
        print(json.dumps(rec))


if __name__ == "__main__":
    main()
