import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from build_wi_district_results import (
    DATA_DIR,
    DEM_PARTIES,
    NONPARTISAN_ALIGNMENT,
    OFFICE_MAP,
    REP_PARTIES,
    build_precinct_lookup,
    build_precinct_records,
    build_result_node,
    election_tags,
    infer_election_type,
    iter_input_csv_paths,
    match_row_precincts,
    normalize_candidate_label,
    normalize_county,
    normalize_office,
    normalize_token,
    parse_min_year,
    row_label,
    should_include_contest,
)


OUT_DIR = DATA_DIR / "precinct_contests"
RECENT_WARD_PATH = DATA_DIR / "tiger" / "wi_ltsb_2025_wards.geojson"


def write_precinct_slice_dir(out_dir: Path, results_by_year: dict[str, dict[str, list[dict[str, object]]]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict[str, object]] = []
    rebuilt_years = {int(year) for year in results_by_year}
    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_entries.extend(
                entry for entry in (existing.get("files") or [])
                if int(entry.get("year") or 0) not in rebuilt_years
            )
        except (ValueError, OSError, TypeError):
            pass
    for year, contests in sorted(results_by_year.items(), key=lambda item: int(item[0])):
        for contest_type, rows in sorted(contests.items()):
            filename = f"{contest_type}_{year}.json"
            manifest_contest_type = "president" if contest_type == "presidential" else contest_type
            payload = {
                "rows": rows,
            }
            (out_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            manifest_entries.append(
                {
                    "contest_type": manifest_contest_type,
                    "year": int(year),
                    "election_type": (rows[0].get("election_type") if rows else "general") or "general",
                    "file": filename,
                    "rows": len(rows),
                }
            )
    manifest_entries.sort(key=lambda entry: (int(entry.get("year") or 0), str(entry.get("contest_type") or "")))
    manifest_path.write_text(
        json.dumps({"files": manifest_entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    min_year = parse_min_year(sys.argv)
    precincts_by_county, geoid_to_key = build_precinct_records()
    precinct_lookup_by_kind, precinct_lookup_by_any_kind = build_precinct_lookup(precincts_by_county)
    recent_lookup_by_kind = recent_lookup_by_any_kind = None
    if RECENT_WARD_PATH.exists():
        recent_precincts_by_county, _ = build_precinct_records(RECENT_WARD_PATH)
        recent_lookup_by_kind, recent_lookup_by_any_kind = build_precinct_lookup(recent_precincts_by_county)

    precinct_totals = defaultdict(
        lambda: {
            "dem_votes": 0.0,
            "rep_votes": 0.0,
            "other_votes": 0.0,
            "total_votes": 0.0,
            "dem_candidate": "",
            "rep_candidate": "",
            "county_name": "",
            "precinct_key": "",
            "geoids": set(),
        }
    )
    seen_total_rows = set()
    contest_election_types: dict[tuple[str, str], str] = {}
    unmatched_rows = 0
    matched_rows = 0
    row_precinct_cache: dict[tuple[str, str, str], list[dict[str, object]]] = {}

    for csv_path in iter_input_csv_paths():
        year = csv_path.parent.name
        year_num = int(year)
        if min_year is not None and year_num < min_year:
            continue
        election_date = csv_path.name.split("__", 1)[0]
        election_month = election_date[4:6] if len(election_date) >= 6 else ""
        tags = election_tags(csv_path)
        election_type = infer_election_type(tags, election_month)
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                office_label = (row.get("office") or "").strip()
                office_key = OFFICE_MAP.get(office_label)
                if not office_key:
                    continue
                if not should_include_contest(office_key, election_month, tags):
                    continue
                county = normalize_county(row.get("county") or "")
                ward_label = row_label(row)
                county_norm = normalize_token(county)
                if not county or not ward_label:
                    continue

                geometry_vintage = "2025" if year_num >= 2022 and recent_lookup_by_kind is not None else "2020"
                cache_key = (geometry_vintage, county_norm, ward_label)
                matched_precincts = row_precinct_cache.get(cache_key)
                if matched_precincts is None:
                    lookup_by_kind = precinct_lookup_by_kind
                    lookup_by_any_kind = precinct_lookup_by_any_kind
                    if year_num >= 2022 and recent_lookup_by_kind is not None:
                        lookup_by_kind = recent_lookup_by_kind
                        lookup_by_any_kind = recent_lookup_by_any_kind
                    matched_precincts = match_row_precincts(
                        county_norm,
                        ward_label,
                        lookup_by_kind,
                        lookup_by_any_kind,
                        allow_municipality_fallback=(geometry_vintage == "2025"),
                    )
                    row_precinct_cache[cache_key] = matched_precincts
                if not matched_precincts:
                    unmatched_rows += 1
                    continue
                matched_rows += 1

                contest_election_types[(year, office_key)] = election_type
                votes = float(row.get("votes") or 0)
                total_votes = float(row.get("total.votes") or 0)
                party = (row.get("party") or "").strip().upper()
                candidate = normalize_candidate_label(office_key, row.get("candidate") or "")
                aligned_party = NONPARTISAN_ALIGNMENT.get((year, normalize_office(office_label)), {}).get(candidate, "")
                fallback_population = sum(float(item.get("persons") or 0) for item in matched_precincts)

                for precinct in matched_precincts:
                    share = (
                        float(precinct.get("persons") or 0) / fallback_population
                        if precinct.get("_municipality_fallback") and fallback_population > 0
                        else 1.0 / len(matched_precincts)
                    )
                    precinct_key = str(precinct["precinct_key"])
                    geoid = str(precinct["geoid"])
                    node = precinct_totals[(year, office_key, precinct_key)]
                    share_votes = votes * share
                    share_total_votes = total_votes * share

                    node["county_name"] = precinct_key
                    node["precinct_key"] = precinct_key
                    node["geoids"].add(geoid)

                    if party in DEM_PARTIES or aligned_party == "dem":
                        node["dem_votes"] += share_votes
                        if candidate and not node["dem_candidate"]:
                            node["dem_candidate"] = candidate
                    elif party in REP_PARTIES or aligned_party == "rep":
                        node["rep_votes"] += share_votes
                        if candidate and not node["rep_candidate"]:
                            node["rep_candidate"] = candidate
                    else:
                        node["other_votes"] += share_votes

                    total_key = (year, office_key, precinct_key, county_norm, ward_label)
                    if total_key not in seen_total_rows:
                        node["total_votes"] += share_total_votes
                        seen_total_rows.add(total_key)

    results_by_year: dict[str, dict[str, list[dict[str, object]]]] = {}
    for (year, office_key, precinct_key), node in sorted(precinct_totals.items()):
        payload = build_result_node(
            node["dem_votes"],
            node["rep_votes"],
            node["other_votes"],
            node["total_votes"],
            str(node["dem_candidate"]),
            str(node["rep_candidate"]),
            office_key,
        )
        payload_row = {
            "county": str(node["county_name"]),
            "precinct_key": precinct_key,
            "geoids": sorted(node["geoids"]),
            "election_type": contest_election_types.get((year, office_key), "general"),
            **payload,
        }
        year_bucket = results_by_year.setdefault(year, {})
        year_bucket.setdefault(office_key, []).append(payload_row)

    write_precinct_slice_dir(OUT_DIR, results_by_year)
    print(f"Wrote {OUT_DIR}")
    print(f"Matched rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")


if __name__ == "__main__":
    main()
