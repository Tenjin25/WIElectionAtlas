import argparse
import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_ARCHIVE = DATA_DIR / "ltsb_2024_election_2025_wards.zip"
DEFAULT_OUT = DATA_DIR / "tiger" / "wi_ltsb_2025_wards.geojson"


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the official LTSB FileGDB ward layer to app-ready GeoJSON.")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--simplify", type=float, default=0.00003, help="Geometry tolerance in degrees.")
    args = parser.parse_args()

    extract_dir = DATA_DIR / "tiger" / "_tmp" / "ltsb_2025_wards"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        archive.extractall(extract_dir)
    geodatabases = list(extract_dir.glob("*.gdb"))
    if len(geodatabases) != 1:
        raise RuntimeError(f"Expected one FileGDB in {args.archive}, found {len(geodatabases)}")

    wards = gpd.read_file(geodatabases[0]).to_crs(4326)
    features = []
    for _, row in wards.iterrows():
        label = str(row.get("LABEL") or "").strip().upper()
        county_fips = str(row.get("CNTY_FIPS") or "").strip().zfill(3)[-3:]
        county_name = str(row.get("CNTY_NAME") or "").strip()
        geoid = str(row.get("GEOID") or "").strip()
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
                "precinct_full_name": label,
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
    print(f"Wrote {args.output} ({len(features)} wards)")


if __name__ == "__main__":
    main()
