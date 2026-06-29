import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TIGER_DIR = DATA_DIR / "tiger"
CW_DIR = DATA_DIR / "crosswalks"
OUT_PATH = DATA_DIR / "mappings" / "precinct_centroids.geojson"


REQUIRED_CROSSWALK_FIELDS = {"precinct_key", "name20", "countyfp20", "geoid20", "vtdst20"}


def read_geojson(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_county_fips_to_name() -> dict[str, str]:
    out: dict[str, str] = {}
    fc = read_geojson(TIGER_DIR / "tl_2020_55_county20.geojson")
    for feature in fc.get("features") or []:
        props = feature.get("properties") or {}
        fips = str(props.get("COUNTYFP20") or "").zfill(3)
        name = " ".join(str(props.get("NAME20") or "").split()).strip()
        if fips and name:
            out[fips] = name
    return out


def load_crosswalk_precincts() -> dict[str, dict[str, str]]:
    rows_by_geoid: dict[str, dict[str, str]] = {}
    for path in sorted(CW_DIR.glob("precinct_to_*.csv")):
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = set(reader.fieldnames or [])
            if not REQUIRED_CROSSWALK_FIELDS.issubset(fieldnames):
                continue
            for row in reader:
                geoid = str(row.get("geoid20") or "").strip()
                if not geoid:
                    continue
                rows_by_geoid.setdefault(
                    geoid,
                    {
                        "precinct_key": " ".join(str(row.get("precinct_key") or "").split()).strip(),
                        "name20": " ".join(str(row.get("name20") or "").split()).strip(),
                        "countyfp20": str(row.get("countyfp20") or "").strip().zfill(3),
                        "vtdst20": str(row.get("vtdst20") or "").strip(),
                    },
                )
    return rows_by_geoid


def derive_precinct_code(precinct_name: str, fallback: str) -> str:
    text = " ".join(str(precinct_name or "").split()).strip()
    if " - " in text:
        suffix = text.split(" - ", 1)[1].strip()
        if suffix:
            return suffix
    return str(fallback or "").strip()


def build_centroid_features() -> list[dict]:
    county_fips_to_name = build_county_fips_to_name()
    crosswalk_precincts = load_crosswalk_precincts()
    vtd_fc = read_geojson(TIGER_DIR / "tl_2020_55_vtd20.geojson")

    grouped: dict[str, dict[str, object]] = {}
    for feature in vtd_fc.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID20") or "").strip()
        if not geoid:
            continue
        meta = crosswalk_precincts.get(geoid)
        if not meta:
            continue

        lon_raw = str(props.get("INTPTLON20") or "").strip()
        lat_raw = str(props.get("INTPTLAT20") or "").strip()
        try:
            lon = float(lon_raw)
            lat = float(lat_raw)
        except ValueError:
            continue

        area_raw = props.get("ALAND20") or 0
        water_raw = props.get("AWATER20") or 0
        try:
            area_weight = float(area_raw) + float(water_raw)
        except (TypeError, ValueError):
            area_weight = 0.0
        if area_weight <= 0:
            area_weight = 1.0

        county_name = county_fips_to_name.get(meta["countyfp20"]) or county_fips_to_name.get(str(props.get("COUNTYFP20") or "").zfill(3), "")
        precinct_name = meta["precinct_key"] or meta["name20"] or " ".join(str(props.get("NAME20") or "").split()).strip()
        precinct_norm = precinct_name.upper()
        prec_id = derive_precinct_code(precinct_name, meta["vtdst20"] or str(props.get("VTDST20") or "").strip())
        node = grouped.setdefault(
            precinct_norm,
            {
                "geoid20": geoid,
                "countyfp20": meta["countyfp20"] or str(props.get("COUNTYFP20") or "").strip().zfill(3),
                "county_nam": county_name,
                "name20": meta["name20"] or precinct_name,
                "prec_id": prec_id,
                "precinct_key": precinct_name,
                "precinct_norm": precinct_norm,
                "precinct_full_name": meta["name20"] or precinct_name,
                "weight_sum": 0.0,
                "lon_sum": 0.0,
                "lat_sum": 0.0,
                "member_geoids": [],
            },
        )
        node["weight_sum"] = float(node["weight_sum"]) + area_weight
        node["lon_sum"] = float(node["lon_sum"]) + (lon * area_weight)
        node["lat_sum"] = float(node["lat_sum"]) + (lat * area_weight)
        node["member_geoids"].append(geoid)

    features: list[dict] = []
    for node in grouped.values():
        weight_sum = float(node.pop("weight_sum", 0.0) or 0.0)
        lon = float(node.pop("lon_sum", 0.0) or 0.0) / weight_sum if weight_sum > 0 else 0.0
        lat = float(node.pop("lat_sum", 0.0) or 0.0) / weight_sum if weight_sum > 0 else 0.0
        member_geoids = node.pop("member_geoids", [])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    **node,
                    "vtd_count": len(member_geoids),
                    "member_geoids": member_geoids,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
            }
        )

    features.sort(
        key=lambda f: (
            str((f.get("properties") or {}).get("county_nam") or "").upper(),
            str((f.get("properties") or {}).get("prec_id") or "").upper(),
        )
    )
    return features


def main() -> None:
    features = build_centroid_features()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"type": "FeatureCollection", "features": features}
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print(f"Wrote {OUT_PATH} ({len(features)} features)")


if __name__ == "__main__":
    main()
