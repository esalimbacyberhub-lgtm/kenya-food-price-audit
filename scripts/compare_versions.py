"""Compare archived versions of the World Bank RTFP Kenya market file.

Read-only with respect to data/: loads each CSV in data/raw/versions/*/ plus the
current file, prints a comparison to stdout, and saves the same text to
outputs/version_comparison.txt.

For each version (with the "Market Average" row dropped):
    - file date, rows, markets, last month in the file
    - column names that differ from the current file
    - monthly median of c_livestock_goat_s_fao for 2022-10..2024-06 and
      2025-12..2026-04, with the number of markets with an observed (raw,
      non-null livestock_goat_s_fao) goat price in each month
    - peak month and peak value of the monthly goat median (whole file)

Missing columns or months print "n/a" rather than failing.

Usage:
    python scripts/compare_versions.py
"""

import io
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
CURRENT = RAW / "KEN_RTFP_mkt_2007_2026-10-05.csv"
OUT = ROOT / "outputs/version_comparison.txt"

GOAT_C = "c_livestock_goat_s_fao"
GOAT_OBS = "livestock_goat_s_fao"
WINDOWS = [("2022-10", "2024-06"), ("2025-12", "2026-04")]
NA = "n/a"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)
pd.set_option("display.max_rows", 500)


def section(title):
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def file_date(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    return m.group(1) if m else path.parent.name


def find_versions():
    paths = []
    for d in sorted((RAW / "versions").iterdir()):
        if not d.is_dir():
            continue
        csvs = sorted(d.glob("KEN_RTFP_mkt_*.csv"))
        if csvs:
            paths.append(csvs[0])
        else:
            print(f"WARNING: no KEN_RTFP_mkt_*.csv in {d}", file=sys.stderr)
    paths.append(CURRENT)
    return paths


def load(path):
    df = pd.read_csv(path, low_memory=False)
    if "mkt_name" in df.columns:
        df = df[df.mkt_name != "Market Average"]
    if "price_date" in df.columns:
        df["price_date"] = pd.to_datetime(df.price_date, errors="coerce")
        df["ym"] = df.price_date.dt.to_period("M")
    return df


def months_in(start, end):
    return pd.period_range(start, end, freq="M")


def summarise(path, current_cols):
    df = load(path)
    cols = [c for c in df.columns if c != "ym"]
    has = lambda c: c in df.columns  # noqa: E731

    s = {
        "date": file_date(path),
        "rows": len(df),
        "markets": df.mkt_name.nunique() if has("mkt_name") else NA,
        "last_month": str(df.ym.max()) if has("ym") else NA,
        "only_here": [c for c in cols if c not in current_cols],
        "missing": [c for c in current_cols if c not in cols],
        "order_differs": [c for c in cols if c in current_cols]
        != [c for c in current_cols if c in cols],
    }

    # Monthly goat median and observed-market counts
    med = cnt = None
    if has("ym") and has(GOAT_C):
        med = df.groupby("ym")[GOAT_C].median()
    if has("ym") and has(GOAT_OBS):
        obs = df[df[GOAT_OBS].notna()]
        key = "mkt_name" if has("mkt_name") else "geo_id"
        if key in df.columns:
            # Months in the file with no observed goat price count as 0, not n/a
            all_months = pd.period_range(df.ym.min(), df.ym.max(), freq="M")
            cnt = (obs.groupby("ym")[key].nunique()
                   .reindex(all_months, fill_value=0))

    s["median"] = med
    s["count"] = cnt
    if med is not None and med.notna().any():
        s["peak_month"] = str(med.idxmax())
        s["peak_value"] = med.max()
    else:
        s["peak_month"] = s["peak_value"] = NA
    return s


def fmt(v, nd=2):
    if v is None or v is NA or (isinstance(v, float) and pd.isna(v)):
        return NA
    if isinstance(v, float):
        return f"{v:,.{nd}f}"
    return str(v)


def lookup(series, month):
    if series is None:
        return NA
    v = series.get(month)
    return NA if v is None or pd.isna(v) else v


def report(summaries):
    section("1. VERSION OVERVIEW (Market Average row dropped)")
    for s in summaries:
        print(f"\n{s['date']}")
        print(f"  rows:        {s['rows']:,}")
        print(f"  markets:     {s['markets']}")
        print(f"  last month:  {s['last_month']}")
        if s["only_here"] or s["missing"] or s["order_differs"]:
            print(f"  columns only in this version: {s['only_here'] or 'none'}")
            print(f"  current columns missing here: {s['missing'] or 'none'}")
            if s["order_differs"]:
                print("  column order differs from current file")
        else:
            print("  columns: identical to current file")
        print(f"  goat median peak: {s['peak_month']}  {fmt(s['peak_value'])}")

    for start, end in WINDOWS:
        months = months_in(start, end)
        section(f"2. MONTHLY MEDIAN {GOAT_C}, {start} to {end}")
        print("(cell = median of c_ across markets / markets with an observed goat price)\n")
        table = pd.DataFrame(
            {
                s["date"]: [
                    f"{fmt(lookup(s['median'], m))} / {fmt(lookup(s['count'], m))}"
                    for m in months
                ]
                for s in summaries
            },
            index=[str(m) for m in months],
        )
        table.index.name = "month"
        print(table.to_string())

    section("3. COMPACT SUMMARY")
    print(compact_table(summaries))


def compact_table(summaries):
    w1_end = pd.Period(WINDOWS[0][1], "M")
    w2_end = pd.Period(WINDOWS[1][1], "M")
    rows = []
    for s in summaries:
        diffs = len(s["only_here"]) + len(s["missing"])
        rows.append(
            {
                "version": s["date"],
                "rows": f"{s['rows']:,}",
                "mkts": s["markets"],
                "last": s["last_month"],
                "col_diffs": diffs if diffs or not s["order_differs"] else "order",
                f"goat_{w1_end}": fmt(lookup(s["median"], w1_end), 0),
                f"goat_{w2_end}": fmt(lookup(s["median"], w2_end), 0),
                f"obs_{WINDOWS[0][0]}..{WINDOWS[0][1]}": obs_total(s, *WINDOWS[0]),
                f"obs_{WINDOWS[1][0]}..{WINDOWS[1][1]}": obs_total(s, *WINDOWS[1]),
                "peak_month": s["peak_month"],
                "peak_value": fmt(s["peak_value"], 0),
            }
        )
    return pd.DataFrame(rows).to_string(index=False)


def obs_total(s, start, end):
    """Market-months with an observed goat price in the window."""
    if s["count"] is None:
        return NA
    return int(sum(lookup(s["count"], m) if lookup(s["count"], m) != NA else 0
                   for m in months_in(start, end)))


def main():
    current_cols = [c for c in pd.read_csv(CURRENT, nrows=0).columns]
    summaries = [summarise(p, current_cols) for p in find_versions()]

    buf = io.StringIO()
    stdout = sys.stdout
    sys.stdout = buf
    try:
        report(summaries)
    finally:
        sys.stdout = stdout
    text = buf.getvalue()
    print(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"\nSaved to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
