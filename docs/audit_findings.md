# Audit findings: KEN_RTFP_mkt_2007_2026-10-05.csv

Every number below was produced by the command shown directly beneath it, run from the project root against the unmodified raw file. Outputs are pasted verbatim. "Markets" means the 233 real markets unless a command says otherwise; `Market Average` is excluded where noted in the code.

Charts: `python3 scripts/plot_checks.py` writes `outputs/figures/check_medians.png`, `check_obs_vs_close.png` and `check_obs_counts.png`. The shaded period in the first and third is 2023-02 to 2025-12 (no observed goat or maize prices in the maize_fao and goat columns of release 2026-10-05; see section 5).

## Raw file checksum

The CSV used here is byte-identical to the copy inside the downloaded zip.

```bash
sha256sum data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv
unzip -p data/raw/KEN_RTFP_mkt_2007_2026-10-05.zip KEN_RTFP_mkt_2007_2026-10-05.csv | sha256sum
```

Output:

```
b0c4cdcf0a785667ba6e8786498f433f5c15bd50d44279b94fbfdbee3e857fc3  data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv
b0c4cdcf0a785667ba6e8786498f433f5c15bd50d44279b94fbfdbee3e857fc3  -
```

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

- In the maize_fao and goat columns of release 2026-10-05, observed maize and goat prices stop after **2023-01**, have **0** rows from 2023-02 to 2025-12, resume in **2026-01**, and last appear in **2026-08**.
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
- 16 markets report goat prices in each month of 2022-10 to 2023-01 and 2026-01 to 2026-08; 0 in between.
- Median `c_goat` rises from 3,234 (2023-01, last observed month) to a peak of **22,299 in 2024-01**, then settles at 5,022–5,532 from 2024-06 to 2025-12.
- Share of 233 markets with `c_goat` > 8,028: 13.7% (2023-04), 48.9% (2023-05), 97.0% (2023-06), 99.6% (2023-07), **100% every month 2023-08 to 2024-03**, 84.5% (2024-04).
- Outside 2023-04 to 2024-04, markets above 8,028: 2 in 2023-03, 2 in 2024-05, 2 in 2026-08, 2 in 2026-09, 7 in 2026-10.
- When observations resume, the observed medians for 2026-01 to 03 (5,224 / 5,132 / 5,650) cover only the 16 markets that reported. The `c_` medians for those same markets are identical (section 11); the `c_` medians across all 233 markets (4,920 / 5,142 / 5,518) include the 217 markets that did not report, so they are not like-for-like with the observed medians.

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
print(t.loc["2022-10":"2026-08"].to_string(na_rep="-"))
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
2026-04            5504.0           5972.0           16              0              0.0
2026-05            5689.0           6204.0           16              0              0.0
2026-06            5884.0           6176.0           16              0              0.0
2026-07            5938.0           6010.0           16              0              0.0
2026-08            6014.0           6212.0           16              2              0.9
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

## 11. Observed vs modelled medians in the same markets (2026)

The observed median covers only the markets that reported that month; the `c_` median in sections 6 and 7 covers all 233. This section compares the observed median with the `c_` median over the same reporting markets.

- From 2026-01 to 2026-08 the same 16 markets report maize every month, and the same 16 report goat every month; none report either in 2026-09 or 2026-10.
- From 2026-01 onwards, the 16 maize-reporting markets and the 16 goat-reporting markets are the same set.
- Maize: the observed median in the reporting markets falls from 83.0 (2026-01) to 56.0 (2026-08). The `c_` median for the same markets equals it in 7 of 8 months (63.4 vs 65.5 in 2026-06). The all-233 `c_` median is 3.5 to 17.4 above the observed median in every month.
- Goat: the `c_` median for the same markets equals the observed median in all 8 months. The all-233 `c_` median ranges from 10 above to 514 below the observed median.
- The same-markets agreement follows from section 4: where an observed price exists, `c_` usually equals it.

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
df = df[df.mkt_name != "Market Average"]
for item in ["maize_fao", "livestock_goat_s_fao"]:
    rep = df[df[item].notna()]
    g, gr = df.groupby("price_date"), rep.groupby("price_date")
    t = pd.DataFrame({
        "obs_median": gr[item].median(),
        "c_median_same_mkts": gr[f"c_{item}"].median(),
        "c_median_all_233": g[f"c_{item}"].median(),
        "n_reporting": g[item].count(),
    }).round(1)
    t.index = t.index.strftime("%Y-%m")
    print(item)
    print(t.loc["2026-01":].to_string(na_rep="-"))
    sets = rep[rep.price_date >= "2026-01-01"].groupby("price_date").mkt_name.apply(frozenset)
    print("distinct sets of reporting markets, 2026-01 onward:", sets.nunique())
EOF
```

Output:

```
maize_fao
            obs_median  c_median_same_mkts  c_median_all_233  n_reporting
price_date                                                               
2026-01           83.0                83.0              86.5           16
2026-02           74.0                74.0              85.0           16
2026-03           74.5                74.5              84.2           16
2026-04           69.0                69.0              84.2           16
2026-05           66.0                66.0              83.4           16
2026-06           65.5                63.4              79.8           16
2026-07           59.0                59.0              74.6           16
2026-08           56.0                56.0              67.6           16
2026-09              -                   -              66.9            0
2026-10              -                   -              67.0            0
distinct sets of reporting markets, 2026-01 onward: 1
livestock_goat_s_fao
            obs_median  c_median_same_mkts  c_median_all_233  n_reporting
price_date                                                               
2026-01         5223.5              5223.5            4920.1           16
2026-02         5132.0              5132.0            5142.0           16
2026-03         5650.0              5650.0            5517.6           16
2026-04         5972.5              5972.5            5504.1           16
2026-05         6203.5              6203.5            5689.1           16
2026-06         6176.0              6176.0            5884.1           16
2026-07         6010.0              6010.0            5938.2           16
2026-08         6212.5              6212.5            6014.4           16
2026-09              -                   -            5975.6            0
2026-10              -                   -            6109.1            0
distinct sets of reporting markets, 2026-01 onward: 1
```

```bash
python3 -I - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv", parse_dates=["price_date"])
df = df[df.mkt_name != "Market Average"]
d = df[df.price_date >= "2026-01-01"]
maize = set(d.loc[d.maize_fao.notna(), "mkt_name"])
goat = set(d.loc[d.livestock_goat_s_fao.notna(), "mkt_name"])
print("maize-reporting markets", len(maize), "| goat-reporting markets", len(goat), "| in both", len(maize & goat))
print("same set:", maize == goat)
print("maize only:", sorted(maize - goat))
print("goat only:", sorted(goat - maize))
EOF
```

Output:

```
maize-reporting markets 16 | goat-reporting markets 16 | in both 16
same set: True
maize only: []
goat only: []
```

## 12. Comparison with earlier releases

The commands in this section also read the archived releases in `data/raw/versions/`. `Market Average` is excluded everywhere except the first `rows` count. "% change" is (2026-10-05 value / earlier value − 1) × 100.

### Goat columns, rows and markets

- Goat columns appear only in 2026-09-28 and 2026-10-05 (7 columns each, including `c_livestock_goat_s_fao`). The four earlier releases (2024-01-23, 2025-01-13, 2026-01-13, 2026-03-10) have none.
- Rows excluding `Market Average` / markets: 11,685 / 57 (2024-01-23), 13,454 / 62 (2025-01-13), 51,754 / 226 (2026-01-13), 52,206 / 226 (2026-03-10), 55,221 / 233 (2026-09-28), 55,454 / 233 (2026-10-05).

```bash
python3 -I - <<'EOF'
import glob, pandas as pd
paths = sorted(glob.glob("data/raw/versions/*/KEN_RTFP_mkt_*.csv")) + ["data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv"]
for p in paths:
    df = pd.read_csv(p, parse_dates=["price_date"], low_memory=False)
    mk = df[df.mkt_name != "Market Average"]
    goat = [c for c in df if "goat" in c]
    print(f"{p[-14:-4]}  rows {len(df):>6,}  rows excl. Market Average {len(mk):>6,}  markets {mk.mkt_name.nunique():>3}  "
          f"last month {df.price_date.max():%Y-%m}  goat columns {len(goat)}  has c_livestock_goat_s_fao {'c_livestock_goat_s_fao' in df}")
EOF
```

Output:

```
2024-01-23  rows 11,890  rows excl. Market Average 11,685  markets  57  last month 2024-01  goat columns 0  has c_livestock_goat_s_fao False
2025-01-13  rows 13,671  rows excl. Market Average 13,454  markets  62  last month 2025-01  goat columns 0  has c_livestock_goat_s_fao False
2026-01-13  rows 51,983  rows excl. Market Average 51,754  markets 226  last month 2026-01  goat columns 0  has c_livestock_goat_s_fao False
2026-03-10  rows 52,437  rows excl. Market Average 52,206  markets 226  last month 2026-03  goat columns 0  has c_livestock_goat_s_fao False
2026-09-28  rows 55,458  rows excl. Market Average 55,221  markets 233  last month 2026-09  goat columns 7  has c_livestock_goat_s_fao True
2026-10-05  rows 55,692  rows excl. Market Average 55,454  markets 233  last month 2026-10  goat columns 7  has c_livestock_goat_s_fao True
```

### Goat: 2026-09-28 vs 2026-10-05

Median `c_livestock_goat_s_fao` across the 233 markets:

| Month | 2026-09-28 | 2026-10-05 | % change |
|---|---|---|---|
| 2022-10 | 2,770.34 | 2,796.03 | +0.93 |
| 2023-01 | 3,199.72 | 3,234.16 | +1.08 |
| 2023-06 | 8,374.92 | 9,431.62 | +12.62 |
| 2023-12 | 16,691.05 | 18,633.41 | +11.64 |
| 2024-01 | 20,693.55 | 22,298.97 | +7.76 |
| 2024-06 | 5,057.99 | 5,459.14 | +7.93 |

```bash
python3 -I - <<'EOF'
import pandas as pd
months = ["2022-10", "2023-01", "2023-06", "2023-12", "2024-01", "2024-06"]
med = {}
for name, p in [("2026-09-28", "data/raw/versions/2026-09-28/KEN_RTFP_mkt_2007_2026-09-28.csv"),
                ("2026-10-05", "data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv")]:
    df = pd.read_csv(p, parse_dates=["price_date"], low_memory=False)
    df = df[df.mkt_name != "Market Average"]
    print(name, "markets", df.mkt_name.nunique())
    med[name] = df.groupby(df.price_date.dt.strftime("%Y-%m")).c_livestock_goat_s_fao.median()
t = pd.DataFrame(med).loc[months]
t["pct_change"] = 100 * (t["2026-10-05"] / t["2026-09-28"] - 1)
print(t.round(2).to_string())
EOF
```

Output:

```
2026-09-28 markets 233
2026-10-05 markets 233
            2026-09-28  2026-10-05  pct_change
price_date                                    
2022-10        2770.34     2796.03        0.93
2023-01        3199.72     3234.16        1.08
2023-06        8374.92     9431.62       12.62
2023-12       16691.05    18633.41       11.64
2024-01       20693.55    22298.97        7.76
2024-06        5057.99     5459.14        7.93
```

### Maize, 2022-10 to 2024-01

The maize column is `maize` in 2024-01-23 and 2025-01-13, `maize_fao` in 2026-01-13, both in 2026-03-10, and `maize_fao` in 2026-09-28 and 2026-10-05. Each column is compared separately with `maize_fao` / `c_maize_fao` in 2026-10-05, matching on market and month.

- Median % change in the modelled price (`c_`) per matched market-month: +30.04 (2024-01-23 `maize`), +10.19 (2025-01-13 `maize`), −99.85 (2026-01-13 `maize_fao`), +30.39 (2026-03-10 `maize`), −99.84 (2026-03-10 `maize_fao`), −0.47 (2026-09-28 `maize_fao`).
- Every matched market-month differs in the four earlier releases; 3,657 of 3,728 differ between 2026-09-28 and 2026-10-05 (range −22.43% to +19.54%).
- The cross-market median `c_` in 2026-01-13 and 2026-03-10 `maize_fao` is 42,943.22 to 65,363.22 per month, against 76.99 to 85.93 in 2026-10-05.
- Observed prices: 2024-01-23 has 97 observed maize rows in 12 markets across 10 months from 2023-01 to 2023-12. 2026-10-05 has 64 rows in 16 markets, 2022-10 to 2023-01 only. No market-month has an observed price in both files. The 64 observed values in 2026-09-28 are identical to 2026-10-05.

```bash
python3 -I - <<'EOF'
import glob, pandas as pd
paths = sorted(glob.glob("data/raw/versions/*/KEN_RTFP_mkt_*.csv")) + ["data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv"]
key = ["mkt_name", "price_date"]
def window(p):
    df = pd.read_csv(p, parse_dates=["price_date"], low_memory=False)
    return df[(df.mkt_name != "Market Average") & df.price_date.between("2022-10-01", "2024-01-01")]
cur = window(paths[-1])[key + ["maize_fao", "c_maize_fao"]].rename(columns={"maize_fao": "obs_cur", "c_maize_fao": "c_cur"})
med = {}
for p in paths:
    d = window(p)
    for col in [c for c in ["maize", "maize_fao"] if c in d]:
        name = f"{p[-14:-4]} {col}"
        med[name] = d.groupby(d.price_date.dt.strftime("%Y-%m"))[f"c_{col}"].median()
        o = d[d[col].notna()]
        m = d[key + [col, f"c_{col}"]].rename(columns={col: "obs", f"c_{col}": "c"}).merge(cur, on=key)
        pc = 100 * (m.c_cur / m.c - 1)
        both = m.obs.notna() & m.obs_cur.notna()
        print(name)
        print(f"  observed rows {len(o)}, markets {o.mkt_name.nunique()}, months {sorted(o.price_date.dt.strftime('%Y-%m').unique())}")
        print(f"  market-months matched to 2026-10-05: {len(m)} ({m.mkt_name.nunique()} markets); observed in both {both.sum()}, differing {(m.obs[both] != m.obs_cur[both]).sum()}")
        print(f"  c_ % change to 2026-10-05: median {pc.median():+.2f}, min {pc.min():+.2f}, max {pc.max():+.2f}, rows differing {(pc != 0).sum()}")
print("\nmonthly median of c_ across markets")
print(pd.DataFrame(med).round(2).to_string())
EOF
```

Output:

```
2024-01-23 maize
  observed rows 97, markets 12, months ['2023-01', '2023-02', '2023-03', '2023-04', '2023-05', '2023-06', '2023-07', '2023-10', '2023-11', '2023-12']
  market-months matched to 2026-10-05: 912 (57 markets); observed in both 0, differing 0
  c_ % change to 2026-10-05: median +30.04, min -33.33, max +171.34, rows differing 912
2025-01-13 maize
  observed rows 0, markets 0, months []
  market-months matched to 2026-10-05: 992 (62 markets); observed in both 0, differing 0
  c_ % change to 2026-10-05: median +10.19, min -32.32, max +100.64, rows differing 992
2026-01-13 maize_fao
  observed rows 6, markets 2, months ['2022-10', '2022-11', '2022-12', '2023-01']
  market-months matched to 2026-10-05: 3616 (226 markets); observed in both 0, differing 0
  c_ % change to 2026-10-05: median -99.85, min -99.91, max -99.68, rows differing 3616
2026-03-10 maize
  observed rows 0, markets 0, months []
  market-months matched to 2026-10-05: 3616 (226 markets); observed in both 0, differing 0
  c_ % change to 2026-10-05: median +30.39, min -25.32, max +113.63, rows differing 3616
2026-03-10 maize_fao
  observed rows 6, markets 2, months ['2022-10', '2022-11', '2022-12', '2023-01']
  market-months matched to 2026-10-05: 3616 (226 markets); observed in both 0, differing 0
  c_ % change to 2026-10-05: median -99.84, min -99.92, max -99.67, rows differing 3616
2026-09-28 maize_fao
  observed rows 64, markets 16, months ['2022-10', '2022-11', '2022-12', '2023-01']
  market-months matched to 2026-10-05: 3728 (233 markets); observed in both 64, differing 0
  c_ % change to 2026-10-05: median -0.47, min -22.43, max +19.54, rows differing 3657
2026-10-05 maize_fao
  observed rows 64, markets 16, months ['2022-10', '2022-11', '2022-12', '2023-01']
  market-months matched to 2026-10-05: 3728 (233 markets); observed in both 64, differing 0
  c_ % change to 2026-10-05: median +0.00, min +0.00, max +0.00, rows differing 0

monthly median of c_ across markets
            2024-01-23 maize  2025-01-13 maize  2026-01-13 maize_fao  2026-03-10 maize  2026-03-10 maize_fao  2026-09-28 maize_fao  2026-10-05 maize_fao
price_date                                                                                                                                              
2022-10                44.00             60.90              42943.22             64.00              49175.72                 85.20                 85.64
2022-11                46.78             60.98              43419.98             62.96              47721.96                 84.70                 85.90
2022-12                49.73             61.52              44326.14             64.26              48216.71                 83.00                 84.68
2023-01                57.27             63.03              45634.27             63.74              48367.92                 85.28                 85.00
2023-02                59.86             63.39              46163.77             63.88              48516.85                 81.41                 83.86
2023-03                63.13             65.47              48596.90             64.04              48712.07                 79.64                 85.51
2023-04                65.58             69.85              53065.28             63.16              50161.79                 79.55                 81.99
2023-05                66.43             73.31              56022.24             63.06              51117.70                 80.72                 83.77
2023-06                67.18             77.65              56981.70             62.43              51680.75                 82.58                 85.51
2023-07                69.37             80.94              57367.48             62.75              51756.39                 82.90                 85.93
2023-08                68.09             79.67              58188.28             62.37              52083.14                 83.84                 83.99
2023-09                66.17             79.54              59622.74             62.41              52220.22                 81.70                 81.56
2023-10                65.69             78.47              60517.45             62.36              52197.00                 80.81                 81.54
2023-11                62.67             81.34              62349.00             62.14              52686.40                 80.22                 79.98
2023-12                59.85             79.49              63256.37             62.68              52688.10                 79.62                 78.25
2024-01                61.02             76.28              65363.22             62.06              54503.41                 79.12                 76.99
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
- Why maize differs across releases (units or item definitions): not established.
