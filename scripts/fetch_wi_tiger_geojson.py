from __future__ import annotations

import json
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
]

LOCAL_ZIPS = [
    DATA_DIR / "tl_2022_55_cd118.zip",
    DATA_DIR / "tl_2022_55_sldl.zip",
    DATA_DIR / "tl_2022_55_sldu.zip",
    DATA_DIR / "tl_2024_55_sldl.zip",
    DATA_DIR / "tl_2024_55_sldu.zip",
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
        if not zip_path.exists():
            download_first(item["urls"], zip_path)
        convert_zip(zip_path, item["name"])

    for zip_path in LOCAL_ZIPS:
        if not zip_path.exists():
            raise FileNotFoundError(f"Required local zip not found: {zip_path}")
        convert_zip(zip_path, zip_path.stem)


if __name__ == "__main__":
    main()
