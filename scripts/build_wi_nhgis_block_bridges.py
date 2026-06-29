from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = DATA_DIR / "crosswalks"


def read_nhgis_zip(zip_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(name for name in zf.namelist() if name.lower().endswith(".csv"))
        with zf.open(csv_name) as fh:
            reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8"))
            rows = [dict(row) for row in reader]
            fieldnames = list(reader.fieldnames or [])
    return rows, fieldnames


def source_target_fields(fieldnames: list[str]) -> tuple[str, str]:
    ge_fields = [name for name in fieldnames if name.endswith("ge")]
    if len(ge_fields) < 2:
        raise RuntimeError(f"Could not infer source/target fields from {fieldnames}")
    return ge_fields[0], ge_fields[1]


def normalize_weights(rows: list[dict[str, object]], source_field: str) -> list[dict[str, object]]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[str(row[source_field])] += float(row["weight"] or 0.0)
    out: list[dict[str, object]] = []
    for row in rows:
        source = str(row[source_field])
        total = totals[source]
        weight = float(row["weight"] or 0.0)
        if total > 0:
            weight = weight / total
        out.append({**row, "weight": weight})
    return out


def compose_rows(
    left_rows: list[dict[str, object]],
    left_source: str,
    left_target: str,
    right_rows: list[dict[str, object]],
    right_source: str,
    right_target: str,
) -> list[dict[str, object]]:
    by_mid: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in right_rows:
        by_mid[str(row[right_source])].append(row)

    agg: dict[tuple[str, str], float] = defaultdict(float)
    for row in left_rows:
        source = str(row[left_source])
        mid = str(row[left_target])
        left_weight = float(row["weight"] or 0.0)
        if left_weight <= 0:
            continue
        for nxt in by_mid.get(mid, []):
            target = str(nxt[right_target])
            right_weight = float(nxt["weight"] or 0.0)
            if right_weight <= 0:
                continue
            agg[(source, target)] += left_weight * right_weight

    out = [
        {left_source: source, right_target: target, "weight": weight}
        for (source, target), weight in sorted(agg.items())
        if weight > 0
    ]
    return normalize_weights(out, left_source)


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            if "weight" in out:
                out["weight"] = f"{float(out['weight']):.12f}"
            writer.writerow(out)


def main() -> None:
    blk2000_blk2010_zip = DATA_DIR / "nhgis_blk2000_blk2010_55.zip"
    blk2010_blk2020_zip = DATA_DIR / "nhgis_blk2010_blk2020_55.zip"
    blk2020_blk2010_zip = DATA_DIR / "nhgis_blk2020_blk2010_55.zip"

    rows_00_10_raw, fields_00_10 = read_nhgis_zip(blk2000_blk2010_zip)
    rows_10_20_raw, fields_10_20 = read_nhgis_zip(blk2010_blk2020_zip)
    rows_20_10_raw, fields_20_10 = read_nhgis_zip(blk2020_blk2010_zip)

    src_00, tgt_10 = source_target_fields(fields_00_10)
    src_10, tgt_20 = source_target_fields(fields_10_20)
    src_20, tgt_10b = source_target_fields(fields_20_10)

    rows_00_10 = normalize_weights(
        [{src_00: row[src_00], tgt_10: row[tgt_10], "weight": float(row["weight"] or 0.0)} for row in rows_00_10_raw],
        src_00,
    )
    rows_10_20 = normalize_weights(
        [{src_10: row[src_10], tgt_20: row[tgt_20], "weight": float(row["weight"] or 0.0)} for row in rows_10_20_raw],
        src_10,
    )
    rows_20_10 = normalize_weights(
        [{src_20: row[src_20], tgt_10b: row[tgt_10b], "weight": float(row["weight"] or 0.0)} for row in rows_20_10_raw],
        src_20,
    )

    rows_00_20 = compose_rows(rows_00_10, src_00, tgt_10, rows_10_20, src_10, tgt_20)

    write_rows(OUT_DIR / "nhgis_blk2000_blk2010_55.csv", rows_00_10, [src_00, tgt_10, "weight"])
    write_rows(OUT_DIR / "nhgis_blk2010_blk2020_55.csv", rows_10_20, [src_10, tgt_20, "weight"])
    write_rows(OUT_DIR / "nhgis_blk2020_blk2010_55.csv", rows_20_10, [src_20, tgt_10b, "weight"])
    write_rows(OUT_DIR / "nhgis_blk2000_blk2020_55.csv", rows_00_20, [src_00, tgt_20, "weight"])

    print(f"Wrote {OUT_DIR / 'nhgis_blk2000_blk2010_55.csv'} ({len(rows_00_10)} rows)")
    print(f"Wrote {OUT_DIR / 'nhgis_blk2010_blk2020_55.csv'} ({len(rows_10_20)} rows)")
    print(f"Wrote {OUT_DIR / 'nhgis_blk2020_blk2010_55.csv'} ({len(rows_20_10)} rows)")
    print(f"Wrote {OUT_DIR / 'nhgis_blk2000_blk2020_55.csv'} ({len(rows_00_20)} rows)")


if __name__ == "__main__":
    main()
