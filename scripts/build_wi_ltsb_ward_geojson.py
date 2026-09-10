import argparse
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_ARCHIVE = DATA_DIR / "wi_municipal_wards_fall_2025.zip"
DEFAULT_OUT = DATA_DIR / "tiger" / "wi_ltsb_2025_wards.geojson"
DEFAULT_FRIENDLY_OUT = DATA_DIR / "mappings" / "precinct_friendly_names.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the official LTSB FileGDB ward layer to app-ready GeoJSON.")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--friendly-output", type=Path, default=DEFAULT_FRIENDLY_OUT)
    parser.add_argument("--simplify", type=float, default=0.00003, help="Geometry tolerance in degrees.")
    args = parser.parse_args()

    extract_dir = DATA_DIR / "tiger" / "_tmp" / args.archive.stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        archive.extractall(extract_dir)
    geodatabases = list(extract_dir.rglob("*.gdb"))
    shapefiles = list(extract_dir.rglob("*.shp"))
    sources = geodatabases or shapefiles
    if len(sources) != 1:
        raise RuntimeError(f"Expected one FileGDB or shapefile in {args.archive}, found {len(sources)}")

    wards = gpd.read_file(sources[0]).to_crs(4326)
    features = []
    for _, row in wards.iterrows():
        source_label = str(row.get("LABEL") or "").strip()
        county_fips = str(row.get("CNTY_FIPS") or "").strip().zfill(3)[-3:]
        county_name = str(row.get("CNTY_NAME") or "").strip()
        geoid = str(row.get("GEOID") or "").strip()
        municipality = str(row.get("MCD_NAME") or source_label.split(" - ", 1)[0]).strip()
        kind = str(row.get("CTV") or "").strip().upper()
        ward_id = str(row.get("WARDID") or source_label.rsplit(" ", 1)[-1]).strip()
        ward_match = re.fullmatch(r"0*(\d+)([A-Z]*)", ward_id, flags=re.IGNORECASE)
        if not ward_match:
            continue
        ward_token = f"{int(ward_match.group(1)):04d}{ward_match.group(2).upper()}"
        # Fall 2025 source corrections needed for the April 2026 reporting units.
        if county_name.upper() == "WAUSHARA" and municipality.upper() == "WAUTOMA" and kind == "C" and ward_token == "0004":
            continue
        if county_name.upper() == "LAFAYETTE" and municipality.upper() == "DARLINGTON" and kind == "T" and ward_token == "0008":
            kind = "C"
        label = f"{municipality.upper()} - {kind} {ward_token}"
        kind_name = {"C": "City", "T": "Town", "V": "Village"}.get(kind, "Municipality")
        ward_number = ward_id.lstrip("0") or "0"
        friendly_name = f"{kind_name} of {municipality}, Ward {ward_number}"
        geometry = row.geometry
        if not label or not county_name or not geoid or geometry is None or geometry.is_empty:
            continue
        if args.simplify > 0:
            geometry = geometry.simplify(args.simplify, preserve_topology=True)
        point = geometry.representative_point()
        persons = row.get("PERSONS")
        persons18 = row.get("PERSONS18")
        features.append({
            "type": "Feature",
            "properties": {
                "GEOID20": geoid,
                "COUNTYFP20": county_fips,
                "NAME20": label,
                "county_nam": county_name,
                "precinct_key": label,
                "precinct_name": label,
                "precinct_full_name": friendly_name,
                "prec_id": label.split(" - ", 1)[-1],
                "PERSONS": 0 if pd.isna(persons) else int(persons),
                "PERSONS18": 0 if pd.isna(persons18) else int(persons18),
                "INTPTLON20": f"{point.x:.8f}",
                "INTPTLAT20": f"{point.y:.8f}",
            },
            "geometry": geometry.__geo_interface__,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    names_by_county: dict[str, dict[str, str]] = defaultdict(dict)
    short_counts_by_county: dict[str, Counter[str]] = defaultdict(Counter)
    for feature in features:
        props = feature["properties"]
        county = str(props["county_nam"]).upper()
        short_counts_by_county[county][str(props["prec_id"])] += 1
    for feature in features:
        props = feature["properties"]
        county = str(props["county_nam"]).upper()
        full_key = str(props["precinct_key"])
        short_key = str(props["prec_id"])
        friendly = str(props["precinct_full_name"])
        names_by_county[county][full_key] = friendly
        if short_counts_by_county[county][short_key] == 1:
            names_by_county[county][short_key] = friendly
    args.friendly_output.parent.mkdir(parents=True, exist_ok=True)
    args.friendly_output.write_text(
        json.dumps({"counties": dict(sorted(names_by_county.items()))}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output} ({len(features)} wards)")
    print(f"Wrote {args.friendly_output} ({len(names_by_county)} counties)")


if __name__ == "__main__":
    main()
