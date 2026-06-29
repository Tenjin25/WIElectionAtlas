from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TIGER_DIR = DATA_DIR / "tiger"
OUT_DIR = DATA_DIR / "crosswalks"
SHAPELY_VENDOR_DIR = ROOT / ".vendor_geo"

if str(SHAPELY_VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(SHAPELY_VENDOR_DIR))

from shapely.geometry import shape  # type: ignore
from shapely.strtree import STRtree  # type: ignore


@dataclass(frozen=True)
class CrosswalkJob:
    district_geojson: Path
    district_field: str
    out_csv: Path
    scope: str


JOBS = [
    CrosswalkJob(
        district_geojson=TIGER_DIR / "tl_2022_55_cd118.geojson",
        district_field="CD118FP",
        out_csv=OUT_DIR / "precinct_to_cd118.csv",
        scope="congressional",
    ),
    CrosswalkJob(
        district_geojson=TIGER_DIR / "tl_2022_55_sldl.geojson",
        district_field="SLDLST",
        out_csv=OUT_DIR / "precinct_to_2022_state_house.csv",
        scope="state_house_2022",
    ),
    CrosswalkJob(
        district_geojson=TIGER_DIR / "tl_2022_55_sldu.geojson",
        district_field="SLDUST",
        out_csv=OUT_DIR / "precinct_to_2022_state_senate.csv",
        scope="state_senate_2022",
    ),
    CrosswalkJob(
        district_geojson=TIGER_DIR / "tl_2024_55_sldl.geojson",
        district_field="SLDLST",
        out_csv=OUT_DIR / "precinct_to_2024_state_house.csv",
        scope="state_house_2024",
    ),
    CrosswalkJob(
        district_geojson=TIGER_DIR / "tl_2024_55_sldu.geojson",
        district_field="SLDUST",
        out_csv=OUT_DIR / "precinct_to_2024_state_senate.csv",
        scope="state_senate_2024",
    ),
]


def read_geojson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def district_number(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    return str(int(digits))


def build_district_index(features: list[dict], district_field: str) -> tuple[list, list[dict[str, str]], STRtree]:
    geometries = []
    meta = []
    for feature in features:
        props = feature.get("properties") or {}
        district_num = district_number(props.get(district_field))
        if not district_num:
            continue
        geom = shape(feature["geometry"])
        if geom.is_empty:
            continue
        geometries.append(geom)
        meta.append({"district_num": district_num})
    return geometries, meta, STRtree(geometries)


def overlap_rows(precinct_features: list[dict], district_geoms: list, district_meta: list[dict[str, str]], tree: STRtree) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature in precinct_features:
        props = feature.get("properties") or {}
        precinct_geom = shape(feature["geometry"])
        if precinct_geom.is_empty:
            continue

        precinct_area = float(precinct_geom.area)
        if precinct_area <= 0:
            continue

        precinct_key = normalize_text(props.get("NAME20") or props.get("NAMELSAD20") or props.get("GEOID20"))
        candidates = tree.query(precinct_geom)

        matched = False
        for candidate in candidates:
            idx = int(candidate)
            district_geom = district_geoms[idx]
            intersection = precinct_geom.intersection(district_geom)
            if intersection.is_empty:
                continue
            intersection_area = float(intersection.area)
            if intersection_area <= 0:
                continue
            matched = True
            rows.append(
                {
                    "precinct_key": precinct_key.upper(),
                    "name20": normalize_text(props.get("NAME20")),
                    "countyfp20": normalize_text(props.get("COUNTYFP20")),
                    "geoid20": normalize_text(props.get("GEOID20")),
                    "vtdst20": normalize_text(props.get("VTDST20")),
                    "district_num": district_meta[idx]["district_num"],
                    "area_weight": intersection_area / precinct_area,
                    "intersection_area": intersection_area,
                    "precinct_area": precinct_area,
                }
            )

        if not matched:
            raise RuntimeError(f"Precinct {precinct_key} did not intersect any district geometry")
    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "precinct_key",
        "name20",
        "countyfp20",
        "geoid20",
        "vtdst20",
        "district_num",
        "area_weight",
        "intersection_area",
        "precinct_area",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["area_weight"] = f"{float(out['area_weight']):.12f}"
            out["intersection_area"] = f"{float(out['intersection_area']):.6f}"
            out["precinct_area"] = f"{float(out['precinct_area']):.6f}"
            writer.writerow(out)


def build_crosswalk(job: CrosswalkJob, precinct_features: list[dict]) -> None:
    district_fc = read_geojson(job.district_geojson)
    district_features = district_fc.get("features") or []
    district_geoms, district_meta, tree = build_district_index(district_features, job.district_field)
    rows = overlap_rows(precinct_features, district_geoms, district_meta, tree)
    write_rows(job.out_csv, rows)
    print(f"Wrote {job.out_csv} ({len(rows)} rows)")


def main() -> None:
    precinct_fc = read_geojson(TIGER_DIR / "tl_2020_55_vtd20.geojson")
    precinct_features = precinct_fc.get("features") or []
    if not precinct_features:
        raise RuntimeError("No precinct features found in tl_2020_55_vtd20.geojson")

    for job in JOBS:
        build_crosswalk(job, precinct_features)


if __name__ == "__main__":
    main()
