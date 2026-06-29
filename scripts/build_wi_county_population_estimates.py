import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "cc-est2025-alldata-55.csv"
OUTPUT = ROOT / "data" / "wi_county_population_estimates_2025.csv"

YEAR_TO_FIELD = {
    "1": "population_base_2020",
    "2": "population_2020",
    "3": "population_2021",
    "4": "population_2022",
    "5": "population_2023",
    "6": "population_2024",
    "7": "population_2025",
}

OUTPUT_FIELDS = [
    "county_name",
    "county_norm",
    "population_base_2020",
    "population_2020",
    "population_2021",
    "population_2022",
    "population_2023",
    "population_2024",
    "population_2025",
    "change_2020_2025",
    "change_2020_2025_pct",
    "change_2024_2025",
    "change_2024_2025_pct",
]


def normalize_county_name(name: str) -> str:
    raw = (name or "").replace(" County", "").replace(".", " ").strip().upper()
    return " ".join(raw.split())


def safe_pct_change(old_value: int, new_value: int) -> str:
    if not old_value:
        return ""
    return f"{((new_value - old_value) / old_value) * 100:.4f}"


def build_rows():
    counties = {}
    statewide = {field: 0 for field in YEAR_TO_FIELD.values()}

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("SUMLEV") != "050" or row.get("AGEGRP") != "0":
                continue

            year_field = YEAR_TO_FIELD.get(str(row.get("YEAR", "")).strip())
            county_name = str(row.get("CTYNAME", "")).strip()
            if not year_field or not county_name:
                continue

            total_pop = int(float(row.get("TOT_POP") or 0))
            county = counties.setdefault(
                county_name,
                {
                    "county_name": county_name,
                    "county_norm": normalize_county_name(county_name),
                    **{field: 0 for field in YEAR_TO_FIELD.values()},
                },
            )
            county[year_field] = total_pop
            statewide[year_field] += total_pop

    out_rows = []
    for county_name in sorted(counties):
        row = counties[county_name]
        base_2020 = int(row["population_base_2020"])
        pop_2024 = int(row["population_2024"])
        pop_2025 = int(row["population_2025"])
        row["change_2020_2025"] = str(pop_2025 - base_2020)
        row["change_2020_2025_pct"] = safe_pct_change(base_2020, pop_2025)
        row["change_2024_2025"] = str(pop_2025 - pop_2024)
        row["change_2024_2025_pct"] = safe_pct_change(pop_2024, pop_2025)
        out_rows.append(row)

    statewide_row = {
        "county_name": "Wisconsin",
        "county_norm": "WISCONSIN",
        **{field: statewide[field] for field in YEAR_TO_FIELD.values()},
    }
    base_2020 = int(statewide_row["population_base_2020"])
    pop_2024 = int(statewide_row["population_2024"])
    pop_2025 = int(statewide_row["population_2025"])
    statewide_row["change_2020_2025"] = str(pop_2025 - base_2020)
    statewide_row["change_2020_2025_pct"] = safe_pct_change(base_2020, pop_2025)
    statewide_row["change_2024_2025"] = str(pop_2025 - pop_2024)
    statewide_row["change_2024_2025_pct"] = safe_pct_change(pop_2024, pop_2025)
    out_rows.append(statewide_row)

    return out_rows


def main():
    rows = build_rows()
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
