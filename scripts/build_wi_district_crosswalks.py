from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import shapefile  # type: ignore
from shapely.geometry import Point, shape  # type: ignore
from shapely.strtree import STRtree  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TIGER_DIR = DATA_DIR / "tiger"
TMP_DIR = TIGER_DIR / "_tmp"
OUT_DIR = DATA_DIR / "crosswalks"


@dataclass(frozen=True)
class CrosswalkJob:
    district_shp: Path
    district_field: str
    out_csv: Path


JOBS = [
    CrosswalkJob(
        district_shp=TMP_DIR / "tl_2022_55_cd118" / "tl_2022_55_cd118.shp",
        district_field="CD118FP",
        out_csv=OUT_DIR / "precinct_to_cd118.csv",
    ),
    CrosswalkJob(
        district_shp=TMP_DIR / "tl_2022_55_sldl" / "tl_2022_55_sldl.shp",
        district_field="SLDLST",
        out_csv=OUT_DIR / "precinct_to_2022_state_house.csv",
    ),
    CrosswalkJob(
        district_shp=TMP_DIR / "tl_2022_55_sldu" / "tl_2022_55_sldu.shp",
        district_field="SLDUST",
        out_csv=OUT_DIR / "precinct_to_2022_state_senate.csv",
    ),
    CrosswalkJob(
        district_shp=TMP_DIR / "tl_2024_55_sldl" / "tl_2024_55_sldl.shp",
        district_field="SLDLST",
        out_csv=OUT_DIR / "precinct_to_2024_state_house.csv",
    ),
    CrosswalkJob(
        district_shp=TMP_DIR / "tl_2024_55_sldu" / "tl_2024_55_sldu.shp",
        district_field="SLDUST",
        out_csv=OUT_DIR / "precinct_to_2024_state_senate.csv",
    ),
]


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def district_number(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return str(int(digits)) if digits else ""


def reader_fields(reader: shapefile.Reader) -> list[str]:
    return [field[0] for field in reader.fields[1:]]


def build_shape_index(shp_path: Path, id_field: str, *, normalize_id=normalize_text) -> tuple[list, list[str], STRtree]:
    reader = shapefile.Reader(str(shp_path), encoding="latin1")
    fields = reader_fields(reader)
    geoms = []
    ids = []
    for sr in reader.iterShapeRecords():
        props = {fields[idx]: sr.record[idx] for idx in range(len(fields))}
        ident = normalize_id(props.get(id_field))
        if not ident:
            continue
        geom = shape(sr.shape.__geo_interface__)
        if geom.is_empty:
            continue
        geoms.append(geom)
        ids.append(ident)
    return geoms, ids, STRtree(geoms)


def locate_id(point: Point, geoms: list, ids: list[str], tree: STRtree, label: str) -> str:
    candidates = tree.query(point)
    if len(candidates) == 0:
        nearest_idx = tree.nearest(point)
        if nearest_idx is not None:
            return ids[int(nearest_idx)]
    for candidate in candidates:
        idx = int(candidate)
        geom = geoms[idx]
        if geom.contains(point) or geom.touches(point):
            return ids[idx]
    nearest = None
    best_dist = None
    for candidate in candidates:
        idx = int(candidate)
        geom = geoms[idx]
        dist = geom.distance(point)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            nearest = ids[idx]
    if nearest:
        return nearest
    raise RuntimeError(f"Could not assign point for {label}")


def build_vtd_membership() -> tuple[dict[str, dict[str, str]], dict[str, float], dict[str, dict[str, str]]]:
    vtd_shp = TMP_DIR / "tl_2020_55_vtd20" / "tl_2020_55_vtd20.shp"
    block_shp = TMP_DIR / "tl_2020_55_tabblock20" / "tl_2020_55_tabblock20.shp"

    vtd_geoms, vtd_ids, vtd_tree = build_shape_index(vtd_shp, "GEOID20", normalize_id=normalize_text)
    vtd_reader = shapefile.Reader(str(vtd_shp), encoding="latin1")
    vtd_fields = reader_fields(vtd_reader)
    vtd_meta_by_geoid: dict[str, dict[str, str]] = {}
    for sr in vtd_reader.iterShapeRecords():
        props = {vtd_fields[idx]: sr.record[idx] for idx in range(len(vtd_fields))}
        geoid = normalize_text(props.get("GEOID20"))
        if not geoid:
            continue
        vtd_meta_by_geoid[geoid] = {
            "precinct_key": normalize_text(props.get("NAME20")).upper(),
            "name20": normalize_text(props.get("NAME20")),
            "countyfp20": normalize_text(props.get("COUNTYFP20")),
            "geoid20": geoid,
            "vtdst20": normalize_text(props.get("VTDST20")),
        }

    block_reader = shapefile.Reader(str(block_shp), encoding="latin1")
    block_fields = reader_fields(block_reader)
    block_to_vtd: dict[str, dict[str, str]] = {}
    block_area: dict[str, float] = {}
    for idx, sr in enumerate(block_reader.iterShapeRecords(), start=1):
        props = {block_fields[i]: sr.record[i] for i in range(len(block_fields))}
        geoid = normalize_text(props.get("GEOID20"))
        if not geoid:
            continue
        geom = shape(sr.shape.__geo_interface__)
        if geom.is_empty:
            continue
        pt = geom.representative_point()
        vtd_geoid = locate_id(pt, vtd_geoms, vtd_ids, vtd_tree, geoid)
        meta = vtd_meta_by_geoid.get(vtd_geoid)
        if not meta:
            raise RuntimeError(f"Missing VTD metadata for {vtd_geoid}")
        block_to_vtd[geoid] = meta
        area = float(props.get("ALAND20") or 0) + float(props.get("AWATER20") or 0)
        if area <= 0:
            area = float(geom.area)
        block_area[geoid] = area
        if idx % 25000 == 0:
            print(f"Assigned {idx} blocks to VTDs")
    return block_to_vtd, block_area, vtd_meta_by_geoid


def build_crosswalk(job: CrosswalkJob, block_to_vtd: dict[str, dict[str, str]], block_area: dict[str, float], vtd_meta_by_geoid: dict[str, dict[str, str]]) -> None:
    district_geoms, district_ids, district_tree = build_shape_index(job.district_shp, job.district_field, normalize_id=district_number)
    block_shp = TMP_DIR / "tl_2020_55_tabblock20" / "tl_2020_55_tabblock20.shp"
    block_reader = shapefile.Reader(str(block_shp), encoding="latin1")
    block_fields = reader_fields(block_reader)

    vtd_total_area: dict[str, float] = defaultdict(float)
    vtd_district_area: dict[tuple[str, str], float] = defaultdict(float)

    for idx, sr in enumerate(block_reader.iterShapeRecords(), start=1):
        props = {block_fields[i]: sr.record[i] for i in range(len(block_fields))}
        block_geoid = normalize_text(props.get("GEOID20"))
        meta = block_to_vtd.get(block_geoid)
        if not meta:
            continue
        geom = shape(sr.shape.__geo_interface__)
        if geom.is_empty:
            continue
        pt = geom.representative_point()
        district_num = locate_id(pt, district_geoms, district_ids, district_tree, block_geoid)
        area = block_area.get(block_geoid, 0.0)
        vtd_geoid = meta["geoid20"]
        vtd_total_area[vtd_geoid] += area
        vtd_district_area[(vtd_geoid, district_num)] += area
        if idx % 25000 == 0:
            print(f"Assigned {idx} blocks to districts for {job.out_csv.name}")

    rows: list[dict[str, object]] = []
    for (vtd_geoid, district_num), area in sorted(vtd_district_area.items()):
        total_area = vtd_total_area[vtd_geoid]
        if total_area <= 0:
            continue
        meta = vtd_meta_by_geoid[vtd_geoid]
        rows.append(
            {
                "precinct_key": meta["precinct_key"],
                "name20": meta["name20"],
                "countyfp20": meta["countyfp20"],
                "geoid20": meta["geoid20"],
                "vtdst20": meta["vtdst20"],
                "district_num": district_num,
                "area_weight": area / total_area,
                "intersection_area": area,
                "precinct_area": total_area,
            }
        )

    write_rows(job.out_csv, rows)
    print(f"Wrote {job.out_csv} ({len(rows)} rows)")


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


def main() -> None:
    block_to_vtd, block_area, vtd_meta_by_geoid = build_vtd_membership()
    for job in JOBS:
        build_crosswalk(job, block_to_vtd, block_area, vtd_meta_by_geoid)


if __name__ == "__main__":
    main()
