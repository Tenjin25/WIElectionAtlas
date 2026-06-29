from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TIGER_DIR = DATA_DIR / "tiger"
CW_DIR = DATA_DIR / "crosswalks"
OUT_2022_JSON = DATA_DIR / "wi_district_results_2022_lines.json"
OUT_2022_DIR = DATA_DIR / "district_contests"
OUT_2024_DIR = DATA_DIR / "district_contests_2024_lines"

OFFICE_MAP = {
    "President": "presidential",
    "Senate": "us_senate",
    "US Senator": "us_senate",
    "House": "us_house",
    "Governor": "governor",
    "Lieutenant Governor": "lieutenant_governor",
    "Attorney General": "attorney_general",
    "Secretary Of State": "secretary_of_state",
    "Secretary of State": "secretary_of_state",
    "State Treasurer": "treasurer",
    "State Assembly": "state_house",
    "Supreme Court": "state_supreme_court",
    "Justice of the Supreme Court": "state_supreme_court",
    "State Superintendent Of Public Instruction": "superintendent",
    "State Superintendent of Public Instruction": "superintendent",
    "State Senate": "state_senate",
    "State Senator": "state_senate",
}
INPUT_GLOBS = (
    "*/*__wi__general__ward.csv",
    "*/*__wi__general-recall__ward.csv",
    "*/*__wi__special__general__ward.csv",
    "*/*__wi__spring__ward_all_contests.csv",
)

DEM_PARTIES = {"DEM"}
REP_PARTIES = {"REP"}
NONPARTISAN_ALIGNMENT = {
    ("2005", "supreme court"): {
        "Ann W. Bradley": "dem",
    },
    ("2006", "supreme court"): {
        "Patrick Crooks": "rep",
    },
    ("2005", "state superintendent of public instruction"): {
        "Elizabeth Burmaster": "dem",
        "Gregg Underheim": "rep",
    },
    ("2007", "supreme court"): {
        "Linda M. Clifford": "dem",
        "Annette K. Ziegler": "rep",
    },
    ("2008", "supreme court"): {
        "Louis Butler": "dem",
        "Mike Gableman": "rep",
    },
    ("2009", "supreme court"): {
        "Shirley S. Abrahamson": "dem",
        "Randy R. Koschnick": "rep",
    },
    ("2009", "state superintendent of public instruction"): {
        "Tony Evers": "dem",
        "Lowell E. Holtz": "rep",
    },
    ("2011", "supreme court"): {
        "Joanne F. Kloppenburg": "dem",
        "David T. Prosser, Jr.": "rep",
        "David T. Prosser Jr": "rep",
    },
    ("2013", "supreme court"): {
        "Ed Fallone": "dem",
        "Pat Roggensack": "rep",
    },
    ("2013", "state superintendent of public instruction"): {
        "Tony Evers": "dem",
        "Don Pridemore": "rep",
    },
    ("2015", "supreme court"): {
        "Ann W. Bradley": "dem",
        "James P. Daley": "rep",
    },
    ("2016", "supreme court"): {
        "JoAnne F. Kloppenburg": "dem",
        "Rebecca G. Bradley": "rep",
    },
    ("2017", "supreme court"): {
        "Annette Ziegler": "rep",
    },
    ("2017", "state superintendent of public instruction"): {
        "Tony Evers": "dem",
        "Lowell E. Holtz": "rep",
    },
    ("2018", "supreme court"): {
        "Rebecca Dallet": "dem",
        "Michael Screnock": "rep",
    },
    ("2019", "supreme court"): {
        "Lisa Neubauer": "dem",
        "Brian Hagedorn": "rep",
    },
    ("2020", "supreme court"): {
        "Jill J. Karofsky": "dem",
        "Daniel Kelly": "rep",
        "Ed Fallone": "dem",
    },
    ("2021", "state superintendent of public instruction"): {
        "Jill Underly": "dem",
        "Deborah Kerr": "rep",
    },
    ("2023", "justice of the supreme court"): {
        "Janet C. Protasiewicz": "dem",
        "Daniel Kelly": "rep",
    },
    ("2025", "supreme court"): {
        "Susan Crawford": "dem",
        "Brad Schimel": "rep",
    },
    ("2025", "state superintendent of public instruction"): {
        "Jill Underly": "dem",
        "Brittany Kinser": "rep",
    },
    ("2026", "supreme court"): {
        "Chris Taylor": "dem",
        "Maria S. Lazar": "rep",
    },
}
CONTEST_DISPLAY = {
    "state_supreme_court": {
        "contest_partisan_style": "nonpartisan_ideology",
        "dem_label": "Liberal",
        "rep_label": "Conservative",
    },
    "superintendent": {
        "contest_partisan_style": "nonpartisan_ideology",
        "dem_label": "Liberal",
        "rep_label": "Conservative",
    },
}
PRESIDENTIAL_TOP_TICKET_NAMES = {
    "Kamala D. Harris Tim Walz": "Kamala D. Harris",
    "Donald J. Trump JD Vance": "Donald J. Trump",
}
NOVEMBER_ONLY_CONTESTS = {
    "presidential",
    "us_senate",
    "governor",
    "lieutenant_governor",
    "attorney_general",
    "secretary_of_state",
    "treasurer",
}
SPRING_ONLY_CONTESTS = {"state_supreme_court", "superintendent"}

DISTRICT_ONLY_SCOPE_BY_OFFICE = {
    "us_house": ("congressional",),
    "state_house": ("state_house",),
    "state_senate": ("state_senate",),
}
TARGET_YEARS = {"2022", "2024"}

SCOPE_CONFIGS = {
    "congressional": {
        "2022": ("tl_2022_55_cd118.geojson", "CD118FP"),
        "2024": ("tl_2022_55_cd118.geojson", "CD118FP"),
    },
    "state_house": {
        "2022": ("tl_2022_55_sldl.geojson", "SLDLST"),
        "2024": ("tl_2024_55_sldl.geojson", "SLDLST"),
    },
    "state_senate": {
        "2022": ("tl_2022_55_sldu.geojson", "SLDUST"),
        "2024": ("tl_2024_55_sldu.geojson", "SLDUST"),
    },
}


def read_geojson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", (value or "").upper()).strip()


def normalize_county(value: str) -> str:
    return " ".join((value or "").strip().split()).title()


def normalize_office(value: str) -> str:
    return " ".join((value or "").strip().split()).lower()


def normalize_candidate_label(office_key: str, candidate: str) -> str:
    candidate = " ".join((candidate or "").strip().split())
    if office_key == "presidential":
        return PRESIDENTIAL_TOP_TICKET_NAMES.get(candidate, candidate)
    return candidate


def normalize_district_number(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if not digits:
        return ""
    return str(int(digits))


def iter_input_csv_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in INPUT_GLOBS:
        for path in sorted(DATA_DIR.glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return paths


def election_tags(csv_path: Path) -> set[str]:
    return {
        part.strip().lower()
        for part in csv_path.stem.split("__")[2:-1]
        if part.strip()
    }


def should_include_contest(office_key: str, election_month: str, tags: set[str]) -> bool:
    if any("primary" in tag for tag in tags):
        return False
    if office_key in NOVEMBER_ONLY_CONTESTS:
        return (
            election_month == "11"
            or "general-recall" in tags
            or ("special" in tags and "general" in tags)
        )
    if office_key in SPRING_ONLY_CONTESTS:
        return election_month != "11"
    return True


def row_label(row: dict[str, str]) -> str:
    return " ".join(((row.get("ward") or row.get("precinct") or "")).strip().split())


def infer_election_type(tags: set[str], election_month: str) -> str:
    if "general-recall" in tags:
        return "recall"
    if "special" in tags and "general" in tags:
        return "special_general"
    if election_month and election_month != "11":
        return "spring"
    return "general"


def winner_from_votes(dem: float, rep: float) -> str:
    if rep > dem:
        return "REP"
    if dem > rep:
        return "DEM"
    return "TIE"


def color_from_margin(margin_pct: float, winner: str) -> str:
    if winner == "TIE":
        return "#9ca3af"
    abs_margin = abs(margin_pct)
    if winner == "DEM":
        if abs_margin >= 20:
            return "#08306b"
        if abs_margin >= 10:
            return "#2171b5"
        if abs_margin >= 5:
            return "#6baed6"
        return "#c6dbef"
    if abs_margin >= 20:
        return "#67000d"
    if abs_margin >= 10:
        return "#cb181d"
    if abs_margin >= 5:
        return "#fb6a4a"
    return "#fcbba1"


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    def point_on_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> bool:
        cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
        if abs(cross) > 1e-9:
            return False
        dot = (px - ax) * (px - bx) + (py - ay) * (py - by)
        return dot <= 1e-9

    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if point_on_segment(x, y, xi, yi, xj, yj):
            return True
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, polygon_coords: list[list[list[float]]]) -> bool:
    if not polygon_coords:
        return False
    if not point_in_ring(x, y, polygon_coords[0]):
        return False
    for hole in polygon_coords[1:]:
        if point_in_ring(x, y, hole):
            return False
    return True


def geometry_contains_point(geometry: dict, x: float, y: float) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        return point_in_polygon(x, y, coords)
    if gtype == "MultiPolygon":
        return any(point_in_polygon(x, y, poly) for poly in coords)
    return False


def build_county_fips_to_name() -> dict[str, str]:
    out: dict[str, str] = {}
    fc = read_geojson(TIGER_DIR / "tl_2020_55_county20.geojson")
    for feature in fc.get("features") or []:
        props = feature.get("properties") or {}
        fips = str(props.get("COUNTYFP20") or "").zfill(3)
        name = normalize_county(str(props.get("NAME20") or ""))
        if fips and name:
            out[fips] = name
    return out


def parse_vtd_name(raw_name: str) -> tuple[str, str, int] | None:
    name = (raw_name or "").strip()
    match = re.match(r"^(.*?)\s*-\s*([A-Z])?\s*0*([0-9]+)$", name, flags=re.IGNORECASE)
    if not match:
        return None
    muni = normalize_token(match.group(1))
    kind = (match.group(2) or "").upper()
    ward_num = int(match.group(3))
    return muni, kind, ward_num


def build_precinct_records() -> tuple[dict[str, list[dict[str, object]]], dict[str, str]]:
    county_fips_to_name = build_county_fips_to_name()
    fc = read_geojson(TIGER_DIR / "tl_2020_55_vtd20.geojson")
    precincts_by_county: dict[str, list[dict[str, object]]] = defaultdict(list)
    geoid_to_key: dict[str, str] = {}
    for feature in fc.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID20") or "")
        county_name = county_fips_to_name.get(str(props.get("COUNTYFP20") or "").zfill(3), "")
        parsed = parse_vtd_name(str(props.get("NAME20") or ""))
        if not geoid or not county_name or not parsed:
            continue
        muni, kind, ward_num = parsed
        record = {
            "geoid": geoid,
            "county": county_name,
            "county_norm": normalize_token(county_name),
            "precinct_key": str(props.get("NAME20") or "").upper(),
            "municipality_norm": muni,
            "kind": kind,
            "ward_num": ward_num,
            "lon": float(str(props.get("INTPTLON20") or "0")),
            "lat": float(str(props.get("INTPTLAT20") or "0")),
        }
        precincts_by_county[normalize_token(county_name)].append(record)
        geoid_to_key[geoid] = record["precinct_key"]
    return precincts_by_county, geoid_to_key


def build_precinct_lookup(precincts_by_county: dict[str, list[dict[str, object]]]) -> tuple[dict[tuple[str, str, str, int], list[dict[str, object]]], dict[tuple[str, str, int], list[dict[str, object]]]]:
    by_kind: dict[tuple[str, str, str, int], list[dict[str, object]]] = defaultdict(list)
    by_any_kind: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    for county_norm, rows in precincts_by_county.items():
        for precinct in rows:
            muni = str(precinct["municipality_norm"])
            kind = str(precinct["kind"])
            ward_num = int(precinct["ward_num"])
            by_kind[(county_norm, muni, kind, ward_num)].append(precinct)
            by_any_kind[(county_norm, muni, ward_num)].append(precinct)
    return by_kind, by_any_kind


def load_crosswalk_assignments() -> dict[tuple[str, str], dict[str, dict[str, float]]]:
    files = {
        ("congressional", "2022"): CW_DIR / "precinct_to_cd118.csv",
        ("congressional", "2024"): CW_DIR / "precinct_to_cd118.csv",
        ("state_house", "2022"): CW_DIR / "precinct_to_2022_state_house.csv",
        ("state_house", "2024"): CW_DIR / "precinct_to_2024_state_house.csv",
        ("state_senate", "2022"): CW_DIR / "precinct_to_2022_state_senate.csv",
        ("state_senate", "2024"): CW_DIR / "precinct_to_2024_state_senate.csv",
    }
    out: dict[tuple[str, str], dict[str, dict[str, float]]] = {}
    for key, path in files.items():
        if not path.exists():
            continue
        mapping: dict[str, dict[str, float]] = defaultdict(dict)
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                geoid = str(row.get("geoid20") or "").strip()
                district_num = str(row.get("district_num") or "").strip()
                weight = float(row.get("area_weight") or 0)
                if geoid and district_num and weight > 0:
                    mapping.setdefault(geoid, {})[district_num] = weight
        if mapping:
            out[key] = mapping
    return out


def build_district_assignment_by_scope_year(precincts_by_county: dict[str, list[dict[str, object]]]) -> dict[tuple[str, str], dict[str, dict[str, float]]]:
    crosswalk_assignments = load_crosswalk_assignments()
    if crosswalk_assignments:
        return crosswalk_assignments

    all_precincts = [p for rows in precincts_by_county.values() for p in rows]
    out: dict[tuple[str, str], dict[str, dict[str, float]]] = {}
    for scope, year_map in SCOPE_CONFIGS.items():
        for year, (filename, field) in year_map.items():
            fc = read_geojson(TIGER_DIR / filename)
            districts = []
            for feature in fc.get("features") or []:
                props = feature.get("properties") or {}
                district_num = re.sub(r"[^0-9]", "", str(props.get(field) or ""))
                district_num = str(int(district_num)) if district_num else ""
                if district_num:
                    districts.append((district_num, feature.get("geometry") or {}))
            mapping: dict[str, dict[str, float]] = {}
            for precinct in all_precincts:
                lon = float(precinct["lon"])
                lat = float(precinct["lat"])
                assigned = ""
                for district_num, geometry in districts:
                    if geometry_contains_point(geometry, lon, lat):
                        assigned = district_num
                        break
                if assigned:
                    mapping[str(precinct["geoid"])] = {assigned: 1.0}
            out[(scope, year)] = mapping
    return out


def parse_ward_list(ward_part: str) -> list[int]:
    text = (ward_part or "").replace("&", ",")
    text = re.sub(r"\bAND\b", ",", text, flags=re.IGNORECASE)
    numbers: list[int] = []
    for part in re.split(r",", text):
        token = part.strip()
        if not token:
            continue
        range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", token)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start <= end:
                numbers.extend(range(start, end + 1))
            else:
                numbers.extend(range(end, start + 1))
            continue
        for n in re.findall(r"\d+", token):
            numbers.append(int(n))
    return sorted(set(numbers))


def parse_ward_label(raw: str) -> tuple[str, str, list[int]] | None:
    text = " ".join((raw or "").strip().split())
    match = re.match(r"^(Town|Village|City)\s+Of\s+(.*?)\s+Wards?\s+(.+)$", text, flags=re.IGNORECASE)
    if not match:
        return None
    kind_word = match.group(1).lower()
    kind = {"town": "T", "village": "V", "city": "C"}.get(kind_word, "")
    municipality = normalize_token(match.group(2))
    ward_nums = parse_ward_list(match.group(3))
    if not municipality or not ward_nums:
        return None
    return municipality, kind, ward_nums


def match_row_precincts(
    county_norm: str,
    ward_label: str,
    by_kind: dict[tuple[str, str, str, int], list[dict[str, object]]],
    by_any_kind: dict[tuple[str, str, int], list[dict[str, object]]],
) -> list[dict[str, object]]:
    parsed = parse_ward_label(ward_label)
    if not parsed:
        return []
    municipality_norm, kind, ward_nums = parsed
    matches = []
    if not matches:
        for ward_num in ward_nums:
            matches.extend(by_kind.get((county_norm, municipality_norm, kind, ward_num), []))
    if not matches:
        for ward_num in ward_nums:
            matches.extend(by_any_kind.get((county_norm, municipality_norm, ward_num), []))
    seen = set()
    deduped = []
    for item in matches:
        geoid = str(item["geoid"])
        if geoid in seen:
            continue
        seen.add(geoid)
        deduped.append(item)
    return deduped


def build_result_node(dem_votes: float, rep_votes: float, other_votes: float, total_votes: float, dem_candidate: str, rep_candidate: str, office_key: str) -> dict[str, object]:
    total = total_votes if total_votes > 0 else dem_votes + rep_votes + other_votes
    margin = rep_votes - dem_votes
    margin_pct = (margin / total * 100.0) if total else 0.0
    winner = winner_from_votes(dem_votes, rep_votes)
    out = {
        "dem_votes": round(dem_votes),
        "rep_votes": round(rep_votes),
        "other_votes": round(other_votes),
        "total_votes": round(total),
        "dem_candidate": dem_candidate,
        "rep_candidate": rep_candidate,
        "margin": round(margin),
        "margin_pct": margin_pct,
        "winner": winner,
        "competitiveness": {"color": color_from_margin(margin_pct, winner)},
    }
    out.update(CONTEST_DISPLAY.get(office_key, {}))
    return out


def should_write_slice(scope: str, contest_type: str, year: str) -> bool:
    if year not in TARGET_YEARS:
        return False
    if scope == "congressional" and contest_type == "us_house":
        return True
    if scope == "state_house" and contest_type == "state_house":
        return True
    if scope == "state_senate" and contest_type == "state_senate":
        return True
    return False


def write_slice_dir(out_dir: Path, results_by_year: dict[str, dict[str, dict[str, dict[str, object]]]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict[str, object]] = []
    for year, scopes in results_by_year.items():
        for scope, contests in scopes.items():
            for contest_type, payload in contests.items():
                if not should_write_slice(scope, contest_type, year):
                    continue
                filename = f"{scope}_{contest_type}_{year}.json"
                (out_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                rows = len((((payload or {}).get("general") or {}).get("results") or {}))
                manifest_contest_type = "president" if contest_type == "presidential" else contest_type
                manifest_entries.append(
                    {
                        "scope": scope,
                        "contest_type": manifest_contest_type,
                        "year": int(year),
                        "election_type": (((payload or {}).get("general") or {}).get("election_type") or "general"),
                        "file": filename,
                        "rows": rows,
                    }
                )
    manifest_entries.sort(key=lambda entry: (entry["year"], entry["scope"], entry["contest_type"]))
    (out_dir / "manifest.json").write_text(
        json.dumps({"files": manifest_entries}, indent=2) + "\n",
        encoding="utf-8",
    )


def copy_scope_slices(
    out_dir: Path,
    results_by_year: dict[str, dict[str, dict[str, dict[str, object]]]],
    scope_filter: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for year, scopes in results_by_year.items():
        contests = scopes.get(scope_filter) or {}
        for contest_type, payload in contests.items():
            if not should_write_slice(scope_filter, contest_type, year):
                continue
            filename = f"{scope_filter}_{contest_type}_{year}.json"
            (out_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_requested_scopes(argv: list[str]) -> set[str] | None:
    requested = {arg.strip().lower() for arg in argv[1:] if arg.strip() and not arg.startswith("--")}
    if not requested:
        return None
    valid = {"congressional", "state_house", "state_senate"}
    chosen = requested & valid
    if not chosen:
        raise SystemExit(f"Expected optional scope arguments from {sorted(valid)}, got: {sorted(requested)}")
    return chosen


def parse_min_year(argv: list[str]) -> int | None:
    for arg in argv[1:]:
        if not arg.startswith("--min-year="):
            continue
        value = arg.split("=", 1)[1].strip()
        if not value:
            raise SystemExit("Expected --min-year=YYYY")
        return int(value)
    return None


def main() -> None:
    requested_scopes = parse_requested_scopes(sys.argv)
    min_year = parse_min_year(sys.argv)
    precincts_by_county, _ = build_precinct_records()
    precinct_lookup_by_kind, precinct_lookup_by_any_kind = build_precinct_lookup(precincts_by_county)
    district_assignments = build_district_assignment_by_scope_year(precincts_by_county)

    district_totals = defaultdict(
        lambda: {
            "dem_votes": 0.0,
            "rep_votes": 0.0,
            "other_votes": 0.0,
            "total_votes": 0.0,
            "dem_candidate": "",
            "rep_candidate": "",
        }
    )
    seen_total_rows = set()
    contest_election_types: dict[tuple[str, str, str, str], str] = {}
    unmatched_rows = 0
    matched_rows = 0
    row_precinct_cache: dict[tuple[str, str], list[dict[str, object]]] = {}
    row_district_cache: dict[tuple[str, str, str, str], dict[str, float]] = {}

    for csv_path in iter_input_csv_paths():
        year = csv_path.parent.name
        year_num = int(year)
        if year not in TARGET_YEARS:
            continue
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

                cache_key = (county_norm, ward_label)
                matched_precincts = row_precinct_cache.get(cache_key)
                if matched_precincts is None:
                    matched_precincts = match_row_precincts(
                        county_norm,
                        ward_label,
                        precinct_lookup_by_kind,
                        precinct_lookup_by_any_kind,
                    )
                    row_precinct_cache[cache_key] = matched_precincts
                if not matched_precincts:
                    unmatched_rows += 1
                    continue
                matched_rows += 1

                votes = float(row.get("votes") or 0)
                total_votes = float(row.get("total.votes") or 0)
                party = (row.get("party") or "").strip().upper()
                candidate = normalize_candidate_label(office_key, row.get("candidate") or "")
                aligned_party = NONPARTISAN_ALIGNMENT.get((year, normalize_office(office_label)), {}).get(candidate, "")
                source_district_num = normalize_district_number(row.get("district") or "")
                share = 1.0 / len(matched_precincts)

                target_scopes = DISTRICT_ONLY_SCOPE_BY_OFFICE.get(
                    office_key,
                    ("congressional", "state_house", "state_senate"),
                )
                for scope in target_scopes:
                    if requested_scopes and scope not in requested_scopes:
                        continue
                    target_lines_years = ("2022",) if scope == "congressional" else ("2022", "2024")
                    for lines_year in target_lines_years:
                        contest_election_types[(lines_year, year, scope, office_key)] = election_type
                        district_cache_key = (lines_year, scope, county_norm, ward_label)
                        district_share_by_num = row_district_cache.get(district_cache_key)
                        if district_share_by_num is None:
                            assignment = district_assignments.get((scope, lines_year), {})
                            district_share_by_num = defaultdict(float)
                            for precinct in matched_precincts:
                                district_weights = assignment.get(str(precinct["geoid"])) or {}
                                for district_num, weight in district_weights.items():
                                    district_share_by_num[district_num] += share * float(weight)
                            district_share_by_num = dict(district_share_by_num)
                            row_district_cache[district_cache_key] = district_share_by_num
                        if office_key in DISTRICT_ONLY_SCOPE_BY_OFFICE and source_district_num:
                            row_share = district_share_by_num.get(source_district_num)
                            if row_share is None:
                                continue
                            district_share_items = ((source_district_num, row_share),)
                        else:
                            district_share_items = district_share_by_num.items()

                        for district_num, row_share in district_share_items:
                            node = district_totals[(lines_year, year, scope, office_key, district_num)]
                            share_votes = votes * row_share
                            share_total_votes = total_votes * row_share
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

                            total_key = (lines_year, year, scope, office_key, district_num, county_norm, ward_label)
                            if total_key not in seen_total_rows:
                                node["total_votes"] += share_total_votes
                        for district_num, _ in district_share_items:
                            seen_total_rows.add((lines_year, year, scope, office_key, district_num, county_norm, ward_label))

    results_2022: dict[str, dict[str, dict[str, dict[str, object]]]] = {}
    results_2024: dict[str, dict[str, dict[str, dict[str, object]]]] = {}

    for (lines_year, year, scope, office_key, district_num), node in sorted(district_totals.items()):
        payload = build_result_node(
            node["dem_votes"],
            node["rep_votes"],
            node["other_votes"],
            node["total_votes"],
            str(node["dem_candidate"]),
            str(node["rep_candidate"]),
            office_key,
        )
        target_root = results_2022 if lines_year == "2022" else results_2024
        year_bucket = target_root.setdefault(year, {})
        scope_bucket = year_bucket.setdefault(scope, {})
        election_type = contest_election_types.get((lines_year, year, scope, office_key), "general")
        contest_bucket = scope_bucket.setdefault(office_key, {"general": {"results": {}, "election_type": election_type}})
        contest_bucket["general"]["election_type"] = election_type
        contest_bucket["general"]["results"][str(district_num)] = payload

    out_2022_payload = {
        "generated_from": "Wisconsin general-election ward CSVs matched to 2020 VTDs by municipality/ward labels and assigned to 2022 district lines by VTD interior points",
        "matching_method": "attempted_label_bridge",
        "coverage": {
            "matched_rows": matched_rows,
            "unmatched_rows": unmatched_rows,
            "matched_pct": (matched_rows / (matched_rows + unmatched_rows) * 100.0) if (matched_rows + unmatched_rows) else 0.0,
        },
        "results_by_year": results_2022,
    }
    OUT_2022_JSON.write_text(json.dumps(out_2022_payload, indent=2), encoding="utf-8")
    write_slice_dir(OUT_2022_DIR, results_2022)
    write_slice_dir(OUT_2024_DIR, results_2024)
    if not requested_scopes or "congressional" in requested_scopes:
        copy_scope_slices(OUT_2024_DIR, results_2022, "congressional")
    print(f"Wrote {OUT_2022_JSON}")
    print(f"Matched rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")


if __name__ == "__main__":
    main()
