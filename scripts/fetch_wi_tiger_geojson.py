from __future__ import annotations

import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TIGER_DIR = DATA_DIR / "tiger"
TMP_DIR = TIGER_DIR / "_tmp"
VENDOR_DIR = ROOT / ".vendor" / "pyshp"
MANIFEST_PATH = TIGER_DIR / "manifest.json"
STATE_NAME_2008 = "WISCONSIN"

if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

import shapefile  # type: ignore


DOWNLOADS = [
    {
        "name": "tl_2020_55_county20",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/55_WISCONSIN/55/tl_2020_55_county20.zip",
            "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/55_WISCONSIN/tl_2020_55_county20.zip",
        ],
    },
    {
        "name": "tl_2020_55_vtd20",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/55_WISCONSIN/55/tl_2020_55_vtd20.zip",
            "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/55_WISCONSIN/tl_2020_55_vtd20.zip",
            "https://www2.census.gov/geo/tiger/TIGER2020/VTD/tl_2020_55_vtd20.zip",
        ],
    },
    {
        "name": "tl_2020_55_tabblock20",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/55_WISCONSIN/55/tl_2020_55_tabblock20.zip",
            "https://www2.census.gov/geo/tiger/TIGER2020PL/STATE/55_WISCONSIN/tl_2020_55_tabblock20.zip",
            "https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_55_tabblock20.zip",
        ],
    },
    {
        "name": "tl_2010_55_tabblock10",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2010/TABBLOCK/2010/tl_2010_55_tabblock10.zip",
        ],
    },
    {
        "name": "tl_2010_55_vtd10",
        "optional": True,
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2010/VTD/2010/tl_2010_55_vtd10.zip",
            "https://www2.census.gov/geo/tiger/TIGER2010/VTD/tl_2010_55_vtd10.zip",
            "https://www2.census.gov/geo/tiger/TIGER2010/55_WISCONSIN/tl_2010_55_vtd10.zip",
            "https://www2.census.gov/geo/tiger/TIGER2010PL/STATE/55_WISCONSIN/tl_2010_55_vtd10.zip",
        ],
    },
    {
        "name": "tl_2022_55_cd118",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2022/CD/tl_2022_55_cd118.zip",
        ],
    },
    {
        "name": "tl_2022_55_sldl",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2022/SLDL/tl_2022_55_sldl.zip",
        ],
    },
    {
        "name": "tl_2022_55_sldu",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2022/SLDU/tl_2022_55_sldu.zip",
        ],
    },
    {
        "name": "tl_2024_55_sldl",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2024/SLDL/tl_2024_55_sldl.zip",
        ],
    },
    {
        "name": "tl_2024_55_sldu",
        "urls": [
            "https://www2.census.gov/geo/tiger/TIGER2024/SLDU/tl_2024_55_sldu.zip",
        ],
    },
]


def ensure_dirs() -> None:
    TIGER_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def download_first(urls: Iterable[str], dest_zip: Path) -> None:
    last_err: Exception | None = None
    for url in urls:
        try:
            print(f"Downloading {url} -> {dest_zip.name}")
            with urllib.request.urlopen(url) as resp, dest_zip.open("wb") as fh:
                fh.write(resp.read())
            print(f"Saved {dest_zip}")
            return
        except Exception as exc:  # pragma: no cover - runtime/network path
            last_err = exc
            print(f"Failed {url}: {exc}")
    if last_err:
        raise last_err
    raise RuntimeError("No download URLs were provided")


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    if dest_dir.exists():
        for child in dest_dir.iterdir():
            if child.is_file():
                child.unlink()
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)


def coerce_value(value):
    if isinstance(value, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                return value.decode(encoding)
            except Exception:
                continue
        return value.decode("utf-8", errors="replace")
    return value


def shp_to_geojson(shp_path: Path, out_path: Path) -> None:
    if out_path.exists():
        print(f"Skipping existing {out_path}")
        return
    reader = shapefile.Reader(str(shp_path), encoding="latin1")
    fields = [field[0] for field in reader.fields[1:]]
    features = []
    for sr in reader.iterShapeRecords():
        props = {
            fields[idx]: coerce_value(value)
            for idx, value in enumerate(sr.record)
        }
        geom = sr.shape.__geo_interface__
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": geom,
            }
        )
    fc = {"type": "FeatureCollection", "features": features}
    out_path.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {out_path} ({len(features)} features)")


def county_url_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def load_counties() -> list[tuple[str, str]]:
    county_geojson = TIGER_DIR / "tl_2020_55_county20.geojson"
    if not county_geojson.exists():
        raise FileNotFoundError(f"County geography is required before tabblock00 fetch: {county_geojson}")
    payload = json.loads(county_geojson.read_text(encoding="utf-8"))
    counties: list[tuple[str, str]] = []
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        countyfp = str(props.get("COUNTYFP20") or "").zfill(3)
        name = str(props.get("NAME20") or "").strip()
        if countyfp and name:
            counties.append((countyfp, name))
    counties.sort(key=lambda item: item[0])
    return counties


def fetch_2008_county_zip(countyfp: str, county_name: str, layer_name: str) -> Path:
    out_name = f"tl_2008_55{countyfp}_{layer_name}.zip"
    zip_path = TMP_DIR / out_name
    if zip_path.exists():
        return zip_path
    slug = county_url_slug(county_name)
    url = (
        f"https://www2.census.gov/geo/tiger/TIGER2008/55_{STATE_NAME_2008}/"
        f"55{countyfp}_{slug}_County/tl_2008_55{countyfp}_{layer_name}.zip"
    )
    download_first([url], zip_path)
    return zip_path


def append_shapefile_features(writer, shp_path: Path) -> int:
    reader = shapefile.Reader(str(shp_path), encoding="latin1")
    fields = [field[0] for field in reader.fields[1:]]
    count = 0
    for sr in reader.iterShapeRecords():
        props = {
            fields[idx]: coerce_value(value)
            for idx, value in enumerate(sr.record)
        }
        geom = sr.shape.__geo_interface__
        feature = {
            "type": "Feature",
            "properties": props,
            "geometry": geom,
        }
        if count > 0:
            writer.write(",")
        writer.write(json.dumps(feature, separators=(",", ":")))
        count += 1
    return count


def build_2008_statewide_county_layer(layer_name: str, *, optional: bool = False) -> None:
    out_path = TIGER_DIR / f"tl_2008_55_{layer_name}.geojson"
    if out_path.exists():
        print(f"Skipping existing {out_path}")
        return
    total_features = 0
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write('{"type":"FeatureCollection","features":[')
        first = True
        for countyfp, county_name in load_counties():
            try:
                zip_path = fetch_2008_county_zip(countyfp, county_name, layer_name)
            except Exception:
                if optional:
                    print(f"Skipping optional layer tl_2008_55_{layer_name}")
                    return
                raise
            extract_dir = TMP_DIR / f"tl_2008_55{countyfp}_{layer_name}"
            extract_zip(zip_path, extract_dir)
            shp_files = sorted(extract_dir.glob("*.shp"))
            if not shp_files:
                raise FileNotFoundError(f"No .shp file found in {zip_path}")
            reader = shapefile.Reader(str(shp_files[0]), encoding="latin1")
            fields = [field[0] for field in reader.fields[1:]]
            for sr in reader.iterShapeRecords():
                props = {
                    fields[idx]: coerce_value(value)
                    for idx, value in enumerate(sr.record)
                }
                geom = sr.shape.__geo_interface__
                feature = {
                    "type": "Feature",
                    "properties": props,
                    "geometry": geom,
                }
                if not first:
                    fh.write(",")
                fh.write(json.dumps(feature, separators=(",", ":")))
                first = False
                total_features += 1
        fh.write("]}")
    print(f"Wrote {out_path} ({total_features} features)")


def write_manifest() -> None:
    entries = []
    for path in sorted(TIGER_DIR.glob("*.geojson")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            features = len(payload.get("features") or [])
        except Exception:
            features = None
        entries.append(
            {
                "file": path.name,
                "features": features,
                "bytes": path.stat().st_size,
            }
        )
    MANIFEST_PATH.write_text(json.dumps({"files": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH}")


def convert_zip(zip_path: Path, out_name: str) -> None:
    extract_dir = TMP_DIR / out_name
    extract_zip(zip_path, extract_dir)
    shp_files = sorted(extract_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp file found in {zip_path}")
    shp_to_geojson(shp_files[0], TIGER_DIR / f"{out_name}.geojson")


def main() -> None:
    ensure_dirs()

    for item in DOWNLOADS:
        zip_path = TMP_DIR / f"{item['name']}.zip"
        try:
            if not zip_path.exists():
                download_first(item["urls"], zip_path)
            convert_zip(zip_path, item["name"])
        except Exception:
            if item.get("optional"):
                print(f"Skipping optional layer {item['name']}")
                continue
            raise
    build_2008_statewide_county_layer("tabblock00")
    build_2008_statewide_county_layer("vtd00", optional=True)
    write_manifest()


if __name__ == "__main__":
    main()
