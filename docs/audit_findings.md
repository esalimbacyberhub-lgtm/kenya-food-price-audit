# Audit findings: KEN_RTFP_mkt_2007_2026-10-05.csv

Every number below was produced by the command shown directly beneath it, run from the project root against the unmodified raw file. Outputs are pasted verbatim. "Markets" means the 233 real markets unless a command says otherwise; `Market Average` is excluded where noted in the code.

Charts: `python3 scripts/plot_checks.py` writes `outputs/figures/check_medians.png`, `check_obs_vs_close.png` and `check_obs_counts.png`. The shaded period in the first and third is 2023-02 to 2025-12 (no observed goat or maize prices; see section 5).

## 1. Structure

- 55,692 rows × 46 columns.
- Monthly from 2007-01-01 to 2026-10-01: 238 months.
- 234 `mkt_name` / `geo_id` values = 233 real markets + `Market Average` (`gid_ken_national_average`), which is the only row group without lat/lon (238 rows).
- 36 counties (`adm2_name`), 16 regions (`adm1_name`).
- 10 columns are constant across all rows, including `data_coverage` 4.46, `data_coverage_recent` 5.45, `index_confidence_score` 0.97, `last_survey_point` "Sep 2026", and `spatially_interpolated`.

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
print("shape", df.shape)
print("dates", df.price_date.min().date(), df.price_date.max().date(), "unique months", df.price_date.nunique())
print("mkt_name", df.mkt_name.nunique(), "geo_id", df.geo_id.nunique(),
      "adm2", df.adm2_name.nunique(), "adm1", df.adm1_name.nunique())
print("rows missing lat", df.lat.isna().sum(), "->", df.loc[df.lat.isna(), ["mkt_name", "geo_id"]].drop_duplicates().values.tolist())
const = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
print("constant columns", len(const), const)
print(df[["data_coverage", "data_coverage_recent", "index_confidence_score", "last_survey_point"]].iloc[0].to_dict())
EOF
```

Output:

```
shape (55692, 46)
dates 2007-01-01 2026-10-01 unique months 238
mkt_name 234 geo_id 234 adm2 36 adm1 16
rows missing lat 238 -> [['Market Average', 'gid_ken_national_average']]
constant columns 10 ['ISO3', 'country', 'currency', 'components', 'start_dense_data', 'last_survey_point', 'data_coverage', 'data_coverage_recent', 'index_confidence_score', 'spatially_interpolated']
{'data_coverage': 4.46, 'data_coverage_recent': 5.45, 'index_confidence_score': 0.97, 'last_survey_point': 'Sep 2026'}
```

## 2. Completeness and observation coverage

- All 234 series have all 238 months; 0 duplicate market-months; 0 exact duplicate rows.
- Of 233 real markets, 49 have at least one observed price; 184 never do.
- Observed markets have a median of 50 observed months (min 1, max 201).
- 27 of the 49 are first observed in 2021.

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
items = ["beans", "maize_fao", "livestock_goat_s_fao"]
per_mkt = df.groupby("mkt_name").price_date.nunique()
print("markets with all 238 months", (per_mkt == 238).sum(), "of", len(per_mkt))
print("duplicate market-months", df.duplicated(["mkt_name", "price_date"]).sum(), "| exact duplicate rows", df.duplicated().sum())
mk = df[df.mkt_name != "Market Average"]
obs = mk[mk[items].notna().any(axis=1)]
n_obs_mkts = obs.mkt_name.nunique()
print("real markets", mk.mkt_name.nunique(), "| with any observed price", n_obs_mkts, "| never observed", mk.mkt_name.nunique() - n_obs_mkts)
months = obs.groupby("mkt_name").price_date.nunique()
print("observed months per observed market: median", months.median(), "min", months.min(), "max", months.max())
print("first observed year:", obs.groupby("mkt_name").price_date.min().dt.year.value_counts().sort_index().to_dict())
EOF
```

Output:

```
markets with all 238 months 234 of 234
duplicate market-months 0 | exact duplicate rows 0
real markets 233 | with any observed price 49 | never observed 184
observed months per observed market: median 50.0 min 1 max 201
first observed year: {2007: 4, 2010: 12, 2015: 4, 2018: 1, 2020: 1, 2021: 27}
```

## 3. Missing values

- `beans` 53,868 missing (96.72%), `livestock_goat_s_fao` 53,091 (95.33%), `maize_fao` 52,647 (94.53%).
- `lat`/`lon` 238 each (the `Market Average` row).
- Each `inflation_*` column: 2,808 missing (5.04%) = 234 series × the 12 months of 2007.
- No other column has missing values.

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
for c in ["beans", "livestock_goat_s_fao", "maize_fao", "lat", "lon"] + [c for c in df if c.startswith("inflation_")]:
    print(f"{c:<32} {df[c].isna().sum():>6}  {100 * df[c].isna().mean():.2f}%")
infl_na = df[df.inflation_beans.isna()]
print("inflation missing rows all in 2007:", (infl_na.price_date.dt.year == 2007).all(), "| = 234 x 12:", len(infl_na) == 234 * 12)
other = [c for c in df if df[c].isna().any()]
print("columns with any missing:", other)
EOF
```

Output:

```
beans                             53868  96.72%
livestock_goat_s_fao              53091  95.33%
maize_fao                         52647  94.53%
lat                                 238  0.43%
lon                                 238  0.43%
inflation_beans                    2808  5.04%
inflation_livestock_goat_s_fao     2808  5.04%
inflation_maize_fao                2808  5.04%
inflation_food_price_index         2808  5.04%
inflation missing rows all in 2007: True | = 234 x 12: True
columns with any missing: ['lat', 'lon', 'beans', 'livestock_goat_s_fao', 'maize_fao', 'inflation_beans', 'inflation_livestock_goat_s_fao', 'inflation_maize_fao', 'inflation_food_price_index']
```

## 4. Observed vs modelled (`c_*`) prices

| Item | Observed rows | Markets | Exactly equal to `c_` | Within 5% | Outside ±25% | Correlation |
|---|---|---|---|---|---|---|
| beans | 1,824 | 43 | 86.2% | 91.9% | 36 | 0.9799 |
| maize_fao | 3,045 | 20 | 93.5% | 96.2% | 33 | 0.9948 |
| livestock_goat_s_fao | 2,601 | 16 | 93.3% | 96.8% | 24 | 0.9951 |

- Largest relative gap `(c - obs) / obs`: beans 0.978, maize 1.091, goat 1.000.
- `trust_* == 10` does not identify observed rows: 2,402 / 166 / 1,340 rows (beans / maize / goat) have trust 10 with no observation, and 143 / 419 / 2,210 observed rows have trust below 10.

```bash
python3 -I - <<'EOF'
import numpy as np, pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
for item in ["beans", "maize_fao", "livestock_goat_s_fao"]:
    d = df[df[item].notna()]
    raw, c = d[item], d[f"c_{item}"]
    rel = (c - raw) / raw
    print(f"{item:<22} rows {len(d):>5}  markets {d.mkt_name.nunique():>2}  "
          f"exact {100 * (rel == 0).mean():.1f}%  within5% {100 * (rel.abs() <= .05).mean():.1f}%  "
          f"outside25% {(rel.abs() > .25).sum():>3}  corr {np.corrcoef(raw, c)[0, 1]:.4f}  "
          f"mean rel {rel.mean():+.4f}  max |rel| {rel.abs().max():.3f}")
for item in ["beans", "maize_fao", "livestock_goat_s_fao"]:
    t = df[f"trust_{item}"]
    print(f"{item:<22} trust==10 & no obs {((t == 10) & df[item].isna()).sum():>5}   obs & trust<10 {((t < 10) & df[item].notna()).sum():>5}")
EOF
```

Output:

```
beans                  rows  1824  markets 43  exact 86.2%  within5% 91.9%  outside25%  36  corr 0.9799  mean rel +0.0090  max |rel| 0.978
maize_fao              rows  3045  markets 20  exact 93.5%  within5% 96.2%  outside25%  33  corr 0.9948  mean rel +0.0036  max |rel| 1.091
livestock_goat_s_fao   rows  2601  markets 16  exact 93.3%  within5% 96.8%  outside25%  24  corr 0.9951  mean rel +0.0034  max |rel| 1.000
beans                  trust==10 & no obs  2402   obs & trust<10   143
maize_fao              trust==10 & no obs   166   obs & trust<10   419
livestock_goat_s_fao   trust==10 & no obs  1340   obs & trust<10  2210
```

## 5. Observation gap for goat and maize

- Observed maize and goat prices stop after **2023-01**, have **0** rows from 2023-02 to 2025-12, resume in **2026-01**, and last appear in **2026-08**.
- Beans continue through the gap (357 observed rows in Feb 2023 – Dec 2025); last beans observation 2026-09 (4 markets).
- 2026-10 has no observed prices for any item.

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
for c in ["maize_fao", "livestock_goat_s_fao", "beans"]:
    d = df.dropna(subset=[c]).price_date
    gap = d[(d >= "2023-02-01") & (d < "2026-01-01")]
    print(f"{c:<22} last before Feb 2023 {d[d < '2023-02-01'].max():%Y-%m}  obs rows Feb 2023-Dec 2025 {len(gap):>4}  "
          f"first from 2026 {d[d >= '2026-01-01'].min():%Y-%m}  last {d.max():%Y-%m}")
print("raw obs in 2026-09:", df[df.price_date == "2026-09-01"][["beans", "maize_fao", "livestock_goat_s_fao"]].notna().sum().to_dict())
print("raw obs in 2026-10:", df[df.price_date == "2026-10-01"][["beans", "maize_fao", "livestock_goat_s_fao"]].notna().sum().to_dict())
EOF
```

Output:

```
maize_fao              last before Feb 2023 2023-01  obs rows Feb 2023-Dec 2025    0  first from 2026 2026-01  last 2026-08
livestock_goat_s_fao   last before Feb 2023 2023-01  obs rows Feb 2023-Dec 2025    0  first from 2026 2026-01  last 2026-08
beans                  last before Feb 2023 2023-01  obs rows Feb 2023-Dec 2025  357  first from 2026 2026-01  last 2026-09
raw obs in 2026-09: {'beans': 4, 'maize_fao': 0, 'livestock_goat_s_fao': 0}
raw obs in 2026-10: {'beans': 0, 'maize_fao': 0, 'livestock_goat_s_fao': 0}
```

## 6. Goat price spike

- Highest observed goat price anywhere: 8,028 KES. Highest `c_livestock_goat_s_fao`: 28,380.59.
- 16 markets report goat prices in each month of 2022-10 to 2023-01 and 2026-01 to 2026-03; 0 in between.
- Median `c_goat` rises from 3,234 (2023-01, last observed month) to a peak of **22,299 in 2024-01**, then settles at 5,022–5,532 from 2024-06 to 2025-12.
- Share of 233 markets with `c_goat` > 8,028: 13.7% (2023-04), 48.9% (2023-05), 97.0% (2023-06), 99.6% (2023-07), **100% every month 2023-08 to 2024-03**, 84.5% (2024-04).
- Outside 2023-04 to 2024-04, markets above 8,028: 2 in 2023-03, 2 in 2024-05, 2 in 2026-08, 2 in 2026-09, 7 in 2026-10.
- When observations resume, observed medians (5,224 / 5,132 / 5,650 for 2026-01 to 03) are close to `c_` medians (4,920 / 5,142 / 5,518).

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
df = df[df.mkt_name != "Market Average"]
obs_max = df.livestock_goat_s_fao.max()
print("max observed goat price", obs_max, "| max c_goat", df.c_livestock_goat_s_fao.max())
g = df.groupby("price_date")
t = pd.DataFrame({
    "median_c_goat": g.c_livestock_goat_s_fao.median().round(0),
    "median_obs_goat": g.livestock_goat_s_fao.median().round(0),
    "n_reporting": g.livestock_goat_s_fao.count(),
    "n_c_above_max": g.c_livestock_goat_s_fao.apply(lambda s: (s > obs_max).sum()),
})
t["pct_c_above_max"] = (100 * t.n_c_above_max / df.mkt_name.nunique()).round(1)
t.index = t.index.strftime("%Y-%m")
print(t.loc["2022-10":"2026-03"].to_string(na_rep="-"))
print("months outside 2023-04..2024-04 with any c_goat > max:",
      t[(t.n_c_above_max > 0) & ~t.index.to_series().between("2023-04", "2024-04")].n_c_above_max.to_dict())
EOF
```

Output:

```
max observed goat price 8028.0 | max c_goat 28380.59
            median_c_goat  median_obs_goat  n_reporting  n_c_above_max  pct_c_above_max
price_date                                                                             
2022-10            2796.0           3342.0           16              0              0.0
2022-11            2956.0           3266.0           16              0              0.0
2022-12            3140.0           3460.0           16              0              0.0
2023-01            3234.0           3612.0           16              0              0.0
2023-02            4164.0                -            0              0              0.0
2023-03            5592.0                -            0              2              0.9
2023-04            7050.0                -            0             32             13.7
2023-05            7992.0                -            0            114             48.9
2023-06            9432.0                -            0            226             97.0
2023-07           10341.0                -            0            232             99.6
2023-08           11704.0                -            0            233            100.0
2023-09           13387.0                -            0            233            100.0
2023-10           14815.0                -            0            233            100.0
2023-11           16842.0                -            0            233            100.0
2023-12           18633.0                -            0            233            100.0
2024-01           22299.0                -            0            233            100.0
2024-02           19100.0                -            0            233            100.0
2024-03           15839.0                -            0            233            100.0
2024-04            9447.0                -            0            197             84.5
2024-05            6386.0                -            0              2              0.9
2024-06            5459.0                -            0              0              0.0
2024-07            5532.0                -            0              0              0.0
2024-08            5302.0                -            0              0              0.0
2024-09            5126.0                -            0              0              0.0
2024-10            5022.0                -            0              0              0.0
2024-11            5284.0                -            0              0              0.0
2024-12            5249.0                -            0              0              0.0
2025-01            5238.0                -            0              0              0.0
2025-02            5239.0                -            0              0              0.0
2025-03            5407.0                -            0              0              0.0
2025-04            5375.0                -            0              0              0.0
2025-05            5281.0                -            0              0              0.0
2025-06            5270.0                -            0              0              0.0
2025-07            5218.0                -            0              0              0.0
2025-08            5238.0                -            0              0              0.0
2025-09            5316.0                -            0              0              0.0
2025-10            5199.0                -            0              0              0.0
2025-11            5340.0                -            0              0              0.0
2025-12            5096.0                -            0              0              0.0
2026-01            4920.0           5224.0           16              0              0.0
2026-02            5142.0           5132.0           16              0              0.0
2026-03            5518.0           5650.0           16              0              0.0
months outside 2023-04..2024-04 with any c_goat > max: {'2023-03': 2, '2024-05': 2, '2026-08': 2, '2026-09': 2, '2026-10': 7}
```

## 7. Food price index

- Cross-market median `c_food_price_index` peaks at **7.58 in 2024-01**, against 1.13 in 2023-01 and 1.83 in 2025-06. Maize median over the same months: 85.00 → 76.99 → 87.74; beans: 139.31 → 177.13 → 150.72.
- 1,638 market-months have `c_food_price_index` > 4, all in 2023 and 2024.
- `inflation_*` equals the 12-month % change of `c_*` to within 0.145 pp for beans, maize and goat, but differs by up to 10.294 pp for the food price index.

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
mk = df[df.mkt_name != "Market Average"]
med = mk.groupby("price_date")[["c_maize_fao", "c_beans", "c_food_price_index"]].median()
peak = med.c_food_price_index.idxmax()
print(f"FPI median peak {med.c_food_price_index.max():.2f} in {peak:%Y-%m}")
print(med.loc[pd.to_datetime(["2023-01-01", peak, "2025-06-01"])].round(2).to_string())
hi = mk[mk.c_food_price_index > 4]
print("rows with c_food_price_index > 4:", len(hi), "years", sorted(hi.price_date.dt.year.unique().tolist()))
d = mk.sort_values(["mkt_name", "price_date"])
for item in ["beans", "maize_fao", "livestock_goat_s_fao", "food_price_index"]:
    yoy = d.groupby("mkt_name")[f"c_{item}"].pct_change(12) * 100
    print(f"inflation_{item:<22} max |inflation - 12m % change of c_| = {(d[f'inflation_{item}'] - yoy).abs().max():.3f} pp")
EOF
```

Output:

```
FPI median peak 7.58 in 2024-01
            c_maize_fao  c_beans  c_food_price_index
2023-01-01        85.00   139.31                1.13
2024-01-01        76.99   177.13                7.58
2025-06-01        87.74   150.72                1.83
rows with c_food_price_index > 4: 1638 years [2023, 2024]
inflation_beans                  max |inflation - 12m % change of c_| = 0.038 pp
inflation_maize_fao              max |inflation - 12m % change of c_| = 0.145 pp
inflation_livestock_goat_s_fao   max |inflation - 12m % change of c_| = 0.008 pp
inflation_food_price_index       max |inflation - 12m % change of c_| = 10.294 pp
```

## 8. Other checks

- `spatially_interpolated` is 0 in all 55,692 rows.
- Open/high/low/close: 1 violation (maize, Mandera, 2007-01); none for beans, goat or the food price index.
- No zero prices; zeros appear only in `inflation_*` (37 / 147 / 34 / 10 for beans / maize / goat / index).
- `Market Average` is not the simple mean of markets: median ratio to the mean is 0.930 (beans) and 0.911 (maize).

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
print("spatially_interpolated values:", df.spatially_interpolated.value_counts().to_dict())
for item in ["beans", "maize_fao", "livestock_goat_s_fao", "food_price_index"]:
    o, h, l, c = (df[f"{p}_{item}"] for p in "ohlc")
    bad = df[~((l <= o) & (o <= h) & (l <= c) & (c <= h))]
    print(f"OHLC violations {item}: {len(bad)}", bad[["mkt_name", "price_date"]].astype(str).values.tolist())
num = df.select_dtypes("number")
print("columns with zeros:", {c: int(v) for c, v in (num == 0).sum().items() if v and c != "spatially_interpolated"})
mk = df[df.mkt_name != "Market Average"]
ma = df[df.mkt_name == "Market Average"].set_index("price_date")
for item in ["beans", "maize_fao"]:
    r = ma[f"c_{item}"] / mk.groupby("price_date")[f"c_{item}"].mean()
    print(f"Market Average / mean of markets, c_{item}: median ratio {r.median():.3f}")
EOF
```

Output:

```
spatially_interpolated values: {0: 55692}
OHLC violations beans: 0 []
OHLC violations maize_fao: 1 [['Mandera', '2007-01-01']]
OHLC violations livestock_goat_s_fao: 0 []
OHLC violations food_price_index: 0 []
columns with zeros: {'inflation_beans': 37, 'inflation_livestock_goat_s_fao': 34, 'inflation_maize_fao': 147, 'inflation_food_price_index': 10}
Market Average / mean of markets, c_beans: median ratio 0.930
Market Average / mean of markets, c_maize_fao: median ratio 0.911
```

## 9. Cross-sectional outliers

Observed or modelled prices more than 5 robust standard deviations from that month's cross-market median of log price, counting only months with at least 5 values: beans 16, maize 6, goat 7 (observed); `c_beans` 48, `c_maize_fao` 16, `c_goat` 10 (modelled).

```bash
python3 -I scripts/explore_rtfp.py 2>/dev/null | grep -E "^  (beans|maize_fao|livestock_goat_s_fao|c_beans|c_maize_fao|c_livestock_goat_s_fao) +[0-9]+ flagged"
```

Output:

```
  beans                         16 flagged
  c_beans                       48 flagged
  maize_fao                      6 flagged
  c_maize_fao                   16 flagged
  livestock_goat_s_fao           7 flagged
  c_livestock_goat_s_fao        10 flagged
```

## 10. Companion details file

The details file reports 233 markets modelled and observation counts of beans 1,906, maize 3,039, goat 2,603. These differ slightly from the non-empty counts in the market file (1,824 / 3,045 / 2,601, section 4); the reason is not known.

```bash
python3 -I - <<'EOF'
import pandas as pd
d = pd.read_csv("data/raw/KEN_RTP_details_mkt_2007_2026-10-05.csv")
print(d[["number_of_markets_modeled", "number_of_observations_food", "number_of_observations_other"]].iloc[0].to_dict())
EOF
```

Output:

```
{'number_of_markets_modeled': 233, 'number_of_observations_food': 'beans: 1906, maize_fao: 3039', 'number_of_observations_other': 'livestock_goat_s_fao: 2603'}
```

The details file also reports `imputation_model` as cubist (Andree, 2021), `data_coverage_food` of 4.46%, and imputation R-squared values of 0.98 (beans), 0.97 (maize) and 0.97 (goat). As written in the file, `imputation_model` lists beans twice and does not list `livestock_goat_s_fao`.

```bash
python3 -I - <<'EOF'
import pandas as pd
d = pd.read_csv("data/raw/KEN_RTP_details_mkt_2007_2026-10-05.csv")
for c in ["imputation_model", "data_coverage_food", "Rsquared_individual_food_items", "Rsquared_individual_other_items"]:
    print(f"{c}: {d[c].iloc[0]}")
EOF
```

Output:

```
imputation_model: beans: cubist (Andree, 2021), maize_fao: cubist (Andree, 2021), beans: cubist (Andree, 2021)
data_coverage_food: 4.46%
Rsquared_individual_food_items: beans: 0.98, maize_fao: 0.97
Rsquared_individual_other_items: livestock_goat_s_fao: 0.97
```

## Corrections to earlier statements

- Observed maize and goat prices were first reported as stopping in May 2023. They stop after **January 2023** (section 5).
- The goat spike was first framed as April 2023 to April 2024. The rise starts in **February 2023**, the month after the last observation; April 2023 to April 2024 is only the stretch where many markets exceed the observed maximum (section 6).
- The food price index peak was first quoted as about 6.3 in December 2023, from quarterly sampling. The monthly peak is **7.58 in January 2024** (section 7).

## Not verified (interpretation or outside knowledge)

- That `c_*` is a model estimate and the non-empty raw columns are observations: consistent with the details file (`imputation_model`, data coverage of about 4.5%, imputation R-squared values) but not documented in the file itself.
- That the rise in the food price index over the same period may reflect the goat series despite "Index Weight = 0": inferred from the timing in sections 6 and 7 only, not from the index formula.
- That some `adm1_name`/`adm2_name` values (e.g. "Moyale", "Ongata Rongai", "Hola (Tana River)") may not match the administrative level of other entries: based on my knowledge of Kenyan geography, not checked against a boundary file.
- Why `Market Average` sits 7–9% below the simple mean (likely a weighted or geometric mean).
- Whether the close agreement between observed and `c_` prices where both exist reflects accuracy or simply that the model was fitted to those observations: not tested here, since no independent observations were used.
