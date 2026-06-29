from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "wi_elections_aggregated.json"

OFFICE_MAP = {
    "President": "presidential",
    "Senate": "us_senate",
    "US Senator": "us_senate",
    "Governor": "governor",
    "Attorney General": "attorney_general",
    "Secretary Of State": "secretary_of_state",
    "Secretary of State": "secretary_of_state",
    "State Treasurer": "treasurer",
    "Supreme Court": "state_supreme_court",
    "State Superintendent Of Public Instruction": "superintendent",
    "State Superintendent of Public Instruction": "superintendent",
}

DEM_PARTIES = {"DEM"}
REP_PARTIES = {"REP"}
NONPARTISAN_ALIGNMENT = {
    ("2005", "supreme court"): {
        "Ann W. Bradley": "dem",
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


def normalize_county(raw: str) -> str:
    return " ".join((raw or "").strip().split()).title()


def normalize_office(raw: str) -> str:
    return " ".join((raw or "").strip().split()).lower()


def normalize_candidate_label(office_key: str, candidate: str) -> str:
    candidate = " ".join((candidate or "").strip().split())
    if office_key == "presidential":
        return PRESIDENTIAL_TOP_TICKET_NAMES.get(candidate, candidate)
    return candidate


def winner_from_votes(dem: int, rep: int) -> str:
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


def main() -> None:
    county_totals = defaultdict(
        lambda: {
            "dem_votes": 0,
            "rep_votes": 0,
            "other_votes": 0,
            "total_votes": 0,
            "dem_candidate": "",
            "rep_candidate": "",
        }
    )
    seen_total_rows = set()

    for csv_path in sorted(DATA_DIR.glob("*/*__wi__general__ward.csv")):
        year = csv_path.parent.name
        election_date = csv_path.name.split("__", 1)[0]
        election_month = election_date[4:6] if len(election_date) >= 6 else ""
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                office_raw = (row.get("office") or "").strip()
                office_key = OFFICE_MAP.get(office_raw)
                if not office_key:
                    continue
                # Wisconsin's spring election files can include presidential preference contests.
                # Keep the presidential series tied to the November general only.
                if office_key == "presidential" and election_month != "11":
                    continue
                county = normalize_county(row.get("county") or "")
                if not county or county.endswith(":") or "total" in county.lower():
                    continue
                votes = int(float(row.get("votes") or 0))
                total_votes = int(float(row.get("total.votes") or 0))
                party = (row.get("party") or "").strip().upper()
                candidate = normalize_candidate_label(office_key, row.get("candidate") or "")
                ward = " ".join((row.get("ward") or "").strip().split())
                if ward.lower().startswith("county totals"):
                    continue

                aligned_party = NONPARTISAN_ALIGNMENT.get((year, normalize_office(office_raw)), {}).get(candidate, "")

                node = county_totals[(year, office_key, county)]
                if party in DEM_PARTIES or aligned_party == "dem":
                    node["dem_votes"] += votes
                    if candidate and not node["dem_candidate"]:
                        node["dem_candidate"] = candidate
                elif party in REP_PARTIES or aligned_party == "rep":
                    node["rep_votes"] += votes
                    if candidate and not node["rep_candidate"]:
                        node["rep_candidate"] = candidate
                else:
                    node["other_votes"] += votes

                total_key = (year, office_key, county, ward)
                if total_key not in seen_total_rows:
                    node["total_votes"] += total_votes
                    seen_total_rows.add(total_key)

    results_by_year: dict[str, dict[str, dict[str, dict[str, object]]]] = {}
    for (year, office_key, county), node in sorted(county_totals.items()):
        if node["total_votes"] <= 0:
            node["total_votes"] = node["dem_votes"] + node["rep_votes"] + node["other_votes"]
        margin = int(node["rep_votes"] - node["dem_votes"])
        total = int(node["total_votes"])
        margin_pct = ((node["rep_votes"] - node["dem_votes"]) / total * 100.0) if total else 0.0
        winner = winner_from_votes(node["dem_votes"], node["rep_votes"])

        year_bucket = results_by_year.setdefault(year, {})
        office_bucket = year_bucket.setdefault(office_key, {})
        contest_bucket = office_bucket.setdefault("general", {"results": {}})
        result = {
            "dem_votes": node["dem_votes"],
            "rep_votes": node["rep_votes"],
            "other_votes": node["other_votes"],
            "total_votes": total,
            "dem_candidate": node["dem_candidate"],
            "rep_candidate": node["rep_candidate"],
            "margin": margin,
            "margin_pct": margin_pct,
            "winner": winner,
            "competitiveness": {
                "color": color_from_margin(margin_pct, winner)
            },
        }
        result.update(CONTEST_DISPLAY.get(office_key, {}))
        contest_bucket["results"][county] = result

    payload = {
        "generated_from": "Wisconsin ward-level general-election CSVs already in this workspace",
        "results_by_year": results_by_year,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
