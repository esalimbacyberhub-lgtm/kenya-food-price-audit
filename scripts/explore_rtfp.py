"""Exploratory look at the World Bank RTFP market-level file for Kenya.

Read-only: loads the raw CSV, prints summaries to stdout, writes nothing.

Usage:
    python scripts/explore_rtfp.py [path/to/KEN_RTFP_mkt_*.csv]
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv"
)
ITEMS = ["beans", "maize_fao", "livestock_goat_s_fao"]
OHLC = ["o", "h", "l", "c"]

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)
pd.set_option("display.max_rows", 200)


def section(title):
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def load(path):
    df = pd.read_csv(path, parse_dates=["price_date"])
    return df


# --------------------------------------------------------------------------- 1
def overview(df):
    section("1. SHAPE, DTYPES, DATE RANGE, GEOGRAPHY")
    print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns\n")
    print(df.dtypes.to_string())

    print(f"\nDate range: {df.price_date.min():%Y-%m-%d} to {df.price_date.max():%Y-%m-%d}")
    print(f"Unique dates: {df.price_date.nunique()}")
    print(f"All dates are the 1st of the month: {(df.price_date.dt.day == 1).all()}")

    print(f"\nUnique markets (mkt_name):  {df.mkt_name.nunique()}")
    print(f"Unique geo_id:              {df.geo_id.nunique()}")
    print(f"Unique (lat, lon):          {df[['lat', 'lon']].drop_duplicates().shape[0]}")
    print(f"Unique counties (adm2):     {df.adm2_name.nunique()}")
    print(f"Unique regions (adm1):      {df.adm1_name.nunique()}")

    # Constant columns carry no information
    const = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
    print(f"\nConstant columns: {const}")
    for c in const:
        print(f"  {c}: {df[c].iloc[0]!r}")

    # Market-level metadata that should be constant within a market
    per_mkt = ["adm1_name", "adm2_name", "lat", "lon", "geo_id", "start_dense_data",
               "last_survey_point", "data_coverage", "data_coverage_recent",
               "index_confidence_score"]
    varying = {c: (df.groupby("mkt_name")[c].nunique(dropna=False) > 1).sum() for c in per_mkt}
    print("\nMarkets where a supposedly per-market field varies over time:")
    print(pd.Series(varying).to_string())

    mkts_per_name = df.groupby("mkt_name").geo_id.nunique()
    if (mkts_per_name > 1).any():
        print("\nMarket names mapping to >1 geo_id:")
        print(mkts_per_name[mkts_per_name > 1])

    print("\nMarkets per region (adm1):")
    print(df.groupby("adm1_name").mkt_name.nunique().sort_values(ascending=False).to_string())

    print("\nMarkets per county (adm2), top 15 and counts summary:")
    mpc = df.groupby("adm2_name").mkt_name.nunique().sort_values(ascending=False)
    print(mpc.head(15).to_string())
    print(f"... counties with exactly 1 market: {(mpc == 1).sum()} of {len(mpc)}")

    print(f"\nlat range {df.lat.min()} to {df.lat.max()}, lon range {df.lon.min()} to {df.lon.max()}")

    # Rows with no coordinates: is this a real market?
    nocoord = df[df.lat.isna()].drop_duplicates("mkt_name")
    print("\nMarkets without coordinates (likely an aggregate, not a market):")
    print(nocoord[["adm1_name", "adm2_name", "mkt_name", "geo_id"]].to_string(index=False))

    # adm1 mixes old provinces with county / town names
    print("\nadm1 values that cover a single market (mixed admin levels?):")
    one = df.drop_duplicates("mkt_name").groupby("adm1_name").filter(lambda g: len(g) == 1)
    print(one[["adm1_name", "adm2_name", "mkt_name"]].to_string(index=False))


# --------------------------------------------------------------------------- 2
def completeness(df):
    section("2. MONTHLY SERIES COMPLETENESS PER MARKET")
    all_months = pd.date_range(df.price_date.min(), df.price_date.max(), freq="MS")
    g = df.groupby("mkt_name").price_date
    span = pd.DataFrame({"first": g.min(), "last": g.max(), "n_rows": g.size(),
                         "n_unique_months": g.nunique()})
    span["expected_in_span"] = (
        (span["last"].dt.year - span["first"].dt.year) * 12
        + (span["last"].dt.month - span["first"].dt.month) + 1
    )
    span["gaps_in_span"] = span.expected_in_span - span.n_unique_months
    span["missing_vs_full_range"] = len(all_months) - span.n_unique_months

    print(f"Full calendar range has {len(all_months)} months")
    print(f"Markets with all {len(all_months)} months: "
          f"{(span.missing_vs_full_range == 0).sum()} of {len(span)}")
    print(f"Markets with internal gaps (between their own first and last month): "
          f"{(span.gaps_in_span > 0).sum()}")
    print(f"Markets with duplicated months: {(span.n_rows > span.n_unique_months).sum()}")

    late = span[span["first"] > all_months[0]]
    early = span[span["last"] < all_months[-1]]
    print(f"\nMarkets starting after {all_months[0]:%Y-%m}: {len(late)}")
    if len(late):
        print(late.sort_values("first")[["first", "last", "n_rows"]].to_string())
    print(f"\nMarkets ending before {all_months[-1]:%Y-%m}: {len(early)}")
    if len(early):
        print(early.sort_values("last")[["first", "last", "n_rows"]].to_string())

    gappy = span[span.gaps_in_span > 0]
    if len(gappy):
        print("\nMarkets with internal gaps:")
        print(gappy.to_string())

    # Rows-per-month sanity check
    rpm = df.groupby("price_date").size()
    print(f"\nRows per month: min {rpm.min()}, max {rpm.max()}")

    # The metadata fields say when real data starts; compare with row span
    print("\nstart_dense_data values (top 10):")
    print(df.drop_duplicates("mkt_name").start_dense_data.value_counts().head(10).to_string())
    print("\nlast_survey_point values (top 10):")
    print(df.drop_duplicates("mkt_name").last_survey_point.value_counts().head(10).to_string())

    # Observed-data span per market (any raw item non-null)
    obs = df[df[ITEMS].notna().any(axis=1)]
    og = obs.groupby("mkt_name").price_date
    ospan = pd.DataFrame({"first_obs": og.min(), "last_obs": og.max(), "n_obs_months": og.nunique()})
    n_never = df.mkt_name.nunique() - len(ospan)
    print(f"\nMarkets with at least one observed (raw) price: {len(ospan)}; never observed: {n_never}")
    print("Distribution of observed months per market:")
    print(ospan.n_obs_months.describe().round(1).to_string())
    print("\nFirst observed month (year) distribution:")
    print(ospan.first_obs.dt.year.value_counts().sort_index().to_string())
    print("\nLast observed month (year) distribution:")
    print(ospan.last_obs.dt.year.value_counts().sort_index().to_string())

    print("\nObserved (raw, non-null) rows per year per item:")
    print(df.groupby(df.price_date.dt.year)[ITEMS].count().to_string())

    last = df.price_date.max()
    print(f"\nRows dated {last:%Y-%m} (after last_survey_point "
          f"{df.last_survey_point.iloc[0]}): {(df.price_date == last).sum()}, "
          f"raw obs in them: {df.loc[df.price_date == last, ITEMS].notna().sum().sum()}")
    return span, ospan


# --------------------------------------------------------------------------- 3
def missing(df):
    section("3. MISSING VALUES PER COLUMN")
    na = df.isna().sum()
    out = pd.DataFrame({"n_missing": na, "pct_missing": (100 * na / len(df)).round(2)})
    print(out.to_string())


# --------------------------------------------------------------------------- 4
def raw_vs_close(df):
    section("4. RAW ITEM COLUMNS vs c_<item> (close)")
    for item in ITEMS:
        raw, c = df[item], df[f"c_{item}"]
        mask = raw.notna()
        n = mask.sum()
        print(f"\n--- {item} ---")
        print(f"non-empty rows: {n:,} ({100 * n / len(df):.2f}%) across "
              f"{df.loc[mask, 'mkt_name'].nunique()} markets")
        if n == 0:
            continue
        r, cc = raw[mask], c[mask]
        print(f"c_{item} missing where {item} present: {cc.isna().sum()}")
        diff = cc - r
        rel = diff / r
        print(f"exact equality:            {(diff == 0).sum():,} ({100 * (diff == 0).mean():.1f}%)")
        for tol in [0.005, 0.01, 0.05, 0.10, 0.25]:
            print(f"|rel diff| <= {tol:>5.1%}:      {(rel.abs() <= tol).mean() * 100:5.1f}%")
        print(f"rel diff (c - raw)/raw: median {rel.median():+.4f}, "
              f"mean {rel.mean():+.4f}, p5 {rel.quantile(.05):+.4f}, p95 {rel.quantile(.95):+.4f}")
        print(f"abs |rel diff| max {rel.abs().max():.3f}")
        print(f"Pearson corr(raw, c): {np.corrcoef(r, cc)[0, 1]:.4f};  "
              f"corr(log): {np.corrcoef(np.log(r[r > 0]), np.log(cc[r > 0]))[0, 1]:.4f}")

        # Do o/h/l bracket the raw value?
        o, h, l = (df.loc[mask, f"{p}_{item}"] for p in "ohl")
        print(f"raw within [l, h]: {((r >= l) & (r <= h)).mean() * 100:.1f}%")
        # Is the raw maybe equal to o/h/l instead of c?
        for p in "ohl":
            col = df.loc[mask, f"{p}_{item}"]
            print(f"  exact match with {p}_{item}: {(col == r).mean() * 100:.1f}%")

        # Biggest disagreements
        worst = df.loc[mask].assign(rel_diff=rel).reindex(rel.abs().sort_values(ascending=False).index)
        print("largest disagreements:")
        print(worst[["mkt_name", "price_date", item, f"l_{item}", f"c_{item}", f"h_{item}", "rel_diff"]]
              .head(8).to_string(index=False))

        # Does the gap change over time?
        by_year = rel.groupby(df.loc[mask, "price_date"].dt.year).agg(["size", "median", lambda s: s.abs().median()])
        by_year.columns = ["n", "median_rel", "median_abs_rel"]
        print("by year:")
        print(by_year.round(4).to_string())

    # Is the food_price_index related to raw availability? (it has no raw column)
    print("\nRows with >=1 raw item observed:", df[ITEMS].notna().any(axis=1).sum())
    print("Rows with all 3 raw items observed:", df[ITEMS].notna().all(axis=1).sum())


# --------------------------------------------------------------------------- 5
def oddities(df):
    section("5. ODDITIES")

    # Duplicates
    dup_rows = df.duplicated().sum()
    dup_keys = df.duplicated(["mkt_name", "price_date"]).sum()
    dup_geo = df.duplicated(["geo_id", "price_date"]).sum()
    print(f"Exact duplicate rows: {dup_rows}")
    print(f"Duplicate (mkt_name, price_date): {dup_keys}")
    print(f"Duplicate (geo_id, price_date): {dup_geo}")
    # Distinct markets at the same coordinates
    coords = df.drop_duplicates("mkt_name").groupby(["lat", "lon"]).mkt_name.apply(list)
    coords = coords[coords.str.len() > 1]
    print(f"Coordinates shared by >1 market name: {len(coords)}")
    if len(coords):
        print(coords.head(20).to_string())

    # year/month consistency
    bad_ym = ((df.year != df.price_date.dt.year) | (df.month != df.price_date.dt.month)).sum()
    print(f"\nRows where year/month disagree with price_date: {bad_ym}")

    # spatially_interpolated
    print("\nspatially_interpolated value counts:")
    print(df.spatially_interpolated.value_counts(dropna=False).to_string())
    si = df.groupby("mkt_name").spatially_interpolated.agg(["min", "max", "mean"])
    print(f"Markets always interpolated: {(si['min'] == 1).sum()}, never: {(si['max'] == 0).sum()}, "
          f"mixed: {((si['min'] == 0) & (si['max'] == 1)).sum()}")
    interp = df.spatially_interpolated == 1
    print(f"Raw observations in spatially_interpolated rows: "
          f"{df.loc[interp, ITEMS].notna().sum().to_dict()}")
    print("data_coverage for interpolated vs not (per market):")
    m = df.drop_duplicates("mkt_name").set_index("mkt_name")
    m["interp"] = si["max"]
    print(m.groupby("interp")[["data_coverage", "index_confidence_score"]].describe().round(2).T.to_string())

    # data_coverage distribution
    print("\ndata_coverage (per market):")
    print(m.data_coverage.describe().round(2).to_string())
    print(f"markets with data_coverage == 0: {(m.data_coverage == 0).sum()}")

    # Zeros and negatives
    num = df.select_dtypes("number").drop(columns=["year", "month", "lat", "lon", "spatially_interpolated"])
    zeros = (num == 0).sum()
    neg = (num < 0).sum()
    print("\nColumns with zeros:")
    print(zeros[zeros > 0].to_string() if (zeros > 0).any() else "  none")
    print("Columns with negatives:")
    print(neg[neg > 0].to_string() if (neg > 0).any() else "  none")

    # OHLC internal consistency
    print("\nOHLC consistency (l <= o,c <= h):")
    for item in ITEMS + ["food_price_index"]:
        o, h, l, c = (df[f"{p}_{item}"] for p in OHLC)
        ok = (l <= o) & (o <= h) & (l <= c) & (c <= h)
        valid = o.notna() & h.notna() & l.notna() & c.notna()
        print(f"  {item:<22} violations: {(~ok & valid).sum()} of {valid.sum()}")

    # Distribution of close prices and outliers
    print("\nDistribution of close prices / raw prices:")
    cols = [f"c_{i}" for i in ITEMS] + ITEMS + ["c_food_price_index"]
    print(df[cols].describe(percentiles=[.001, .01, .25, .5, .75, .99, .999]).round(2).T.to_string())

    # Outliers: robust z-score of log price within each month (cross-sectional)
    # Months with few observed markets give MAD ~ 0, so require >= 5 obs and MAD > 0
    print("\nCross-sectional outliers (|robust z| of log price within month > 5, "
          "months with >= 5 values only):")
    for item in ITEMS:
        for col in [item, f"c_{item}"]:
            lp = np.log(df[col].where(df[col] > 0))
            grp = lp.groupby(df.price_date)
            med = grp.transform("median")
            mad = (lp - med).abs().groupby(df.price_date).transform("median") * 1.4826
            n = grp.transform("count")
            z = ((lp - med) / mad).where((n >= 5) & (mad > 0))
            flag = z.abs() > 5
            print(f"  {col:<26} {flag.sum():>5} flagged")
            if col == item and flag.any():
                print(df.loc[flag].assign(z=z[flag].round(1))
                      .sort_values("z", key=abs, ascending=False)
                      [["mkt_name", "price_date", item, f"c_{item}", "z"]]
                      .head(10).to_string(index=False))

    # Outliers over time: big month-on-month jumps in observed prices
    print("\nLargest month-on-month jumps in observed raw prices (consecutive months only):")
    for item in ITEMS:
        s = df[["mkt_name", "price_date", item]].dropna().sort_values(["mkt_name", "price_date"])
        s["prev"] = s.groupby("mkt_name")[item].shift()
        s["prev_date"] = s.groupby("mkt_name").price_date.shift()
        s = s[(s.price_date - s.prev_date).dt.days.between(28, 31)]
        s["ratio"] = s[item] / s["prev"]
        print(f"  {item}: n={len(s)}, ratio >3 or <1/3: {((s.ratio > 3) | (s.ratio < 1/3)).sum()}")
        print(s.reindex(np.log(s.ratio).abs().sort_values(ascending=False).index)
              .head(5)[["mkt_name", "price_date", "prev", item, "ratio"]]
              .round({"prev": 2, item: 2, "ratio": 2}).to_string(index=False))

    # Inflation columns: how often populated
    print("\nInflation columns: first non-null date per market (should be ~12 months after start)")
    for item in ITEMS + ["food_price_index"]:
        col = f"inflation_{item}"
        first = df.dropna(subset=[col]).groupby("mkt_name").price_date.min()
        print(f"  {col:<32} earliest {first.min():%Y-%m}, most common {first.mode().iloc[0]:%Y-%m}")

    # trust scores
    print("\nTrust score distributions:")
    tcols = [c for c in df.columns if c.startswith("trust_")]
    print(df[tcols].describe().round(2).T.to_string())
    for item in ITEMS:
        obs = df[item].notna()
        print(f"  trust_{item}: mean when observed {df.loc[obs, f'trust_{item}'].mean():.2f}, "
              f"when imputed {df.loc[~obs, f'trust_{item}'].mean():.2f}")

    # components column
    print("\ncomponents unique values:", df.components.nunique())


# --------------------------------------------------------------------------- 5b
def imputation_checks(df):
    section("5b. IMPUTED SERIES SANITY CHECKS")
    mk = df[df.mkt_name != "Market Average"]

    # Inflation columns: are they year-on-year % change of c_?
    d = mk.sort_values(["mkt_name", "price_date"])
    for item in ITEMS + ["food_price_index"]:
        yoy = d.groupby("mkt_name")[f"c_{item}"].pct_change(12) * 100
        err = (d[f"inflation_{item}"] - yoy).abs()
        print(f"inflation_{item:<22} vs 12-month % change of c_: "
              f"median |diff| {err.median():.3f} pp, max {err.max():.3f} pp")

    # Imputed vs observed range, by year
    print("\nMedian close price across markets by year, with observed raw range:")
    yr = mk.price_date.dt.year
    tbl = pd.concat({f"c_{i}": mk.groupby(yr)[f"c_{i}"].median() for i in ITEMS}
                    | {"c_food_price_index": mk.groupby(yr).c_food_price_index.median()}, axis=1)
    print(tbl.round(2).to_string())
    for item in ITEMS:
        lo, hi = mk[item].min(), mk[item].max()
        out = (mk[f"c_{item}"] > hi * 1.5) | (mk[f"c_{item}"] < lo / 1.5)
        print(f"  c_{item}: rows > 1.5x max observed or < min/1.5: {out.sum():,} "
              f"(years: {sorted(mk.loc[out, 'price_date'].dt.year.unique().tolist())})")

    # Goat has Index Weight = 0 but does the food price index follow it?
    print("\nMonthly cross-market medians around the 2023-25 observation gap (quarterly):")
    q = (mk[mk.price_date >= "2022-06-01"].groupby("price_date")
         [["c_beans", "c_maize_fao", "c_livestock_goat_s_fao", "c_food_price_index"]].median())
    print(q.iloc[::3].round(2).to_string())
    print(f"rows with c_food_price_index > 4: {(mk.c_food_price_index > 4).sum()} "
          f"(years: {sorted(mk.loc[mk.c_food_price_index > 4, 'price_date'].dt.year.unique().tolist())})")

    # How does the 'Market Average' row relate to the markets?
    ma = df[df.mkt_name == "Market Average"].set_index("price_date")
    if len(ma):
        print("\n'Market Average' row vs simple mean / median of markets (ratio):")
        for item in ["beans", "maize_fao"]:
            r_mean = ma[f"c_{item}"] / mk.groupby("price_date")[f"c_{item}"].mean()
            r_med = ma[f"c_{item}"] / mk.groupby("price_date")[f"c_{item}"].median()
            print(f"  c_{item}: vs mean median ratio {r_mean.median():.3f}, "
                  f"vs median median ratio {r_med.median():.3f}")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    df = load(path)
    print(f"Loaded {path}")
    overview(df)
    completeness(df)
    missing(df)
    raw_vs_close(df)
    oddities(df)
    imputation_checks(df)


if __name__ == "__main__":
    main()
