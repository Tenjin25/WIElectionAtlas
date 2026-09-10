import csv
import argparse
from collections import Counter
from pathlib import Path

from build_wi_district_results import (
    OFFICE_MAP,
    build_precinct_lookup,
    build_precinct_records,
    election_tags,
    iter_input_csv_paths,
    match_row_precincts,
    normalize_county,
    normalize_token,
    row_label,
    should_include_contest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report election ward labels that do not match 2020 VTDs.")
    parser.add_argument("--min-year", type=int)
    parser.add_argument("--year", type=int)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--geometry", type=Path, help="Optional ward GeoJSON to audit instead of 2020 VTDs.")
    parser.add_argument("--municipality-fallback", action="store_true")
    args = parser.parse_args()
    precincts_by_county, _ = build_precinct_records(args.geometry)
    by_kind, by_any_kind = build_precinct_lookup(precincts_by_county)
    missing: Counter[tuple[str, str, str]] = Counter()

    for csv_path in iter_input_csv_paths():
        year = int(csv_path.parent.name)
        if args.year is not None and year != args.year:
            continue
        if args.min_year is not None and year < args.min_year:
            continue
        with csv_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                office_key = OFFICE_MAP.get((row.get("office") or "").strip())
                if not office_key or not should_include_contest(
                    office_key, csv_path.name[4:6], election_tags(csv_path)
                ):
                    continue
                county = normalize_county(row.get("county") or "")
                label = row_label(row)
                if not county or not label or normalize_token(label) == "COUNTY TOTALS":
                    continue
                if not match_row_precincts(
                    normalize_token(county), label, by_kind, by_any_kind,
                    allow_municipality_fallback=args.municipality_fallback,
                ):
                    missing[(csv_path.parent.name, county, label)] += 1

    print(f"Unique unmatched labels: {len(missing)}")
    print(f"Unmatched candidate rows: {sum(missing.values())}")
    print("By year: " + ", ".join(
        f"{year}={count}" for year, count in sorted(Counter(key[0] for key in missing).items())
    ))
    print("year\tcounty\tward label\trows")
    for (year, county, label), count in missing.most_common(args.limit):
        print(f"{year}\t{county}\t{label}\t{count}")


if __name__ == "__main__":
    main()
