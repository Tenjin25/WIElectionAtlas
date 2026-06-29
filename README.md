# Wisconsin Election Atlas

The Wisconsin Election Atlas is an interactive map of how Wisconsin politics changed over time. It is built to show not just who won, but where coalitions grew, where they weakened, how different kinds of contests produced different geographies, and how those same voting patterns look when translated into newer district maps.

The project combines ward-level returns, precinct geography, district crosswalks, and historical reaggregation to trace Wisconsin's electoral evolution from 2000 through 2026. The result is a map built for political geography: realignment, ticket-splitting, redistricting, and long-run regional change.

## Live Site

Primary deployment target: GitHub Pages.

If this repository is published as a standard project site, the expected URL is:

`https://tenjin25.github.io/WIElectionAtlas/`

If your Pages settings use a different custom domain or branch configuration, update this link accordingly.

## License

This project is available under the MIT License. See `LICENSE`.

## What This Atlas Shows

- County and precinct-level election results across modern Wisconsin political history
- The geographic coalition behind presidential, Senate, gubernatorial, down-ballot, judicial, and education races
- Urban, suburban, small-city, and rural realignment over multiple cycles
- How the same underlying vote behaves when viewed through different congressional, assembly, and senate line vintages
- Where political change is gradual, where it is abrupt, and where ticket-splitting persists
- How spring elections, fall elections, partisan races, and nominally nonpartisan statewide contests differ geographically

## What Kind Of Story It Tells

This atlas is especially built to surface a few big stories in Wisconsin politics:

- the long Republican shift across much of rural and small-town Wisconsin
- the deepening Democratic base in Madison, Milwaukee, and some close-in suburban territory
- the changing role of suburban counties, especially where old Republican margins softened or reversed
- the difference between presidential geography and the geography of governor, Senate, Supreme Court, and superintendent races
- the relationship between electoral realignment and representation under changing district lines

## Contest Coverage

The atlas covers a broad range of statewide and district-relevant contests, including:

- Presidential elections
- U.S. Senate elections
- U.S. House elections
- Governor
- Lieutenant Governor
- Attorney General
- Secretary of State
- State Treasurer
- Wisconsin State Assembly
- Wisconsin State Senate
- Wisconsin Supreme Court
- State Superintendent of Public Instruction

The underlying dataset spans general elections, special generals, recall-related generals, and major statewide spring contests where ward-level data is available.

## Time Span

The map is designed as a long-run electoral history, not just a recent-cycle viewer.

- Core coverage begins in 2000
- It includes the major statewide and federal cycles of the 2000s, 2010s, and 2020s
- It extends through 2026 in the currently checked-in data

That makes it possible to compare pre-Obama Wisconsin, the Walker era, the Trump-era partisan reshaping of the state, and the more recent post-2020 map environment in one place.

## Realignments And Political Storylines

A big part of the point of this project is not simply who won, but where the coalition moved.

The atlas is especially useful for tracking:

- The long Republican trend in many rural and small-town areas
- The countervailing Democratic consolidation in Madison, Milwaukee, and their close-in suburbs
- The changing behavior of WOW counties and other suburban counties
- Split-ticket territory that behaves differently in presidential, gubernatorial, Senate, and Supreme Court races
- The distinct geography of spring judicial and superintendent elections
- Places where swing is broad and uniform versus places where it is highly localized

Because the data is mapped at precinct scale where possible, it can show changes that disappear in county-only analysis.

## Color Thresholds And What They Mean

The atlas uses custom color thresholds so the map can communicate not just party control, but the intensity and character of the vote.

In the default margin view:

- darker blue means a stronger Democratic margin
- darker red means a stronger Republican margin
- gray marks a tie or effectively neutral result

The threshold bands are:

- under 0.5 points: `Tossup`
- 0.50 to 0.99 points: `Tilt`
- 1.00 to 5.49 points: `Lean`
- 5.50 to 9.99 points: `Likely`
- 10.00 to 19.99 points: `Safe`
- 20.00 to 29.99 points: `Stronghold`
- 30.00 to 39.99 points: `Dominant`
- 40 points or more: `Annihilation`

Those are the atlas's actual competitiveness labels. If you want them in plain English, they roughly mean:

- `Tossup`: effectively even
- `Tilt`: barely off even, but with a real edge
- `Lean`: competitive, but one side has the edge
- `Likely`: a clear advantage, though not a lock
- `Safe`: a solid result that would take a meaningful shift to overturn
- `Stronghold`: deeply anchored partisan terrain
- `Dominant`: overwhelming local control short of the top tier
- `Annihilation`: overwhelming local dominance

That means the colors are not arbitrary decoration. They are meant to help a reader separate:

- true battleground terrain from mild lean
- ordinary wins from durable partisan advantage
- durable partisan advantage from genuine local strongholds
- broad partisan regions from places that remain contestable

This matters in Wisconsin because many of the state's most important changes are not simple flips from blue to red or red to blue. Often the real story is that a region stayed the same party but became much more or much less competitive. The threshold system is meant to make those changes legible at a glance.

The same basic logic also supports other views in the atlas, including shift and flip-style interpretations, where the emphasis is less on raw margin and more on direction of movement.

## District Lines And Reaggregation

One of the most useful features of the atlas is that it does not stop at raw statewide precinct returns. It also reaggregates those returns into district views.

That allows the project to show:

- Congressional results under the current district framework
- State Assembly and State Senate results under multiple line vintages
- The difference between the same vote pattern viewed through 2022-era and 2024-era legislative maps
- How electoral coalitions translate into district performance after redistricting

In other words, the atlas can separate two different questions that are often blurred together:

1. How did people vote?
2. How do those votes map onto representation under a given set of lines?

## How Older Elections Were Mapped To Modern Districts

One of the harder parts of the project was making older elections usable in modern district frameworks.

Wisconsin did not report older elections in terms of today's congressional, assembly, or senate districts. Older results exist as ward-level or precinct-level returns tied to the geography of their own time. To compare those elections under modern lines, the project had to rebuild that relationship spatially.

The method works roughly like this:

1. Start with historical ward or precinct election returns.
2. Normalize those returns into a consistent statewide election table.
3. Anchor them to modernized precinct geography using Wisconsin voting district and Census block relationships.
4. Use block-level bridge files to connect older and newer census vintages where the underlying geography changed.
5. Intersect those modern precinct units with newer congressional and legislative district lines.
6. Reaggregate votes into the target district framework using geographic weights.

In practice, that means the atlas can take an older contest and answer a modern question like:

- How would the 2004 presidential vote look under 2024 assembly lines?
- How would the 2010 governor race distribute across the post-redistricting senate map?
- How did older Democratic or Republican strength line up with the districts Wisconsin uses now?

The key enabling pieces are:

- NHGIS block bridge crosswalks that connect older census-block vintages to newer ones
- precinct-to-district crosswalks built from 2020 voting district geography and current district polygons
- weighted geographic assignment rather than a simple county-based approximation

This is what allows the atlas to show realignment and redistricting together instead of as separate stories.

## Why The Reaggregation Matters

Without that historical-to-modern translation work, older elections and newer district maps would live in separate worlds. You could study the old vote, or you could study the new lines, but not really connect them.

This project makes it possible to ask questions like:

- Which present-day assembly districts were already drifting right before the newest map?
- Which districts look competitive now because the lines changed, and which look competitive because the voters changed?
- How much of a district's current political identity is inherited from older regional behavior?

That is the difference between a results archive and an atlas. The goal here is interpretation, not just storage.

## Why Wisconsin

Wisconsin is one of the best states for this kind of atlas because it repeatedly produces close statewide elections, strong regional identities, sharp urban-rural contrast, and meaningful ticket-splitting. It is also a state where redistricting, court races, and down-ballot statewide contests matter enough to tell a broader political story.

That makes it a particularly rich place to study:

- partisan drift
- regional polarization
- crossover voting
- turnout geography
- map effects versus raw vote effects

## Stack

- Static HTML/CSS/JavaScript app in [`index.html`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/index.html)
- [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) for mapping
- [Turf.js](https://turfjs.org/) for geospatial helpers in the browser
- [Papa Parse](https://www.papaparse.com/) for CSV parsing
- Python scripts for data ingestion and preprocessing
- Checked-in GeoJSON, CSV, JSON, ZIP, and workbook inputs under `data/`

## Repository Layout

- [`index.html`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/index.html): the full client application
- [`data/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/data): published datasets consumed by the site
- [`data/tiger/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/data/tiger): Census geography converted to GeoJSON
- [`data/crosswalks/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/data/crosswalks): precinct-to-district and block bridge lookup tables
- [`data/district_contests/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/data/district_contests): district result slices aligned to 2022-era lines
- [`data/district_contests_2024_lines/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/data/district_contests_2024_lines): district result slices aligned to 2024-era lines
- [`data/mappings/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/data/mappings): derived map helper files such as precinct centroids
- [`scripts/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts): data pipeline utilities
- [`.vendor/`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/.vendor): vendored Python dependencies used by some scripts

## How To Use The Atlas

The atlas is meant to be explored comparatively.

- Switch between counties, precincts, and district views
- Move across years within the same contest type
- Compare presidential performance with gubernatorial, Senate, or Supreme Court results
- Toggle district-line vintages to see how the same underlying vote maps into different representative boundaries
- Use scenario and modeling tools to test what broad swings would look like geographically

The project is published as a static GitHub Pages site and is designed to work directly in the browser from checked-in data files.

For statewide legislative views, the app uses chamber leadership labels rather than generic party placeholders in the statewide summary. In the current UI, State Assembly statewide contests are shown against `Speaker Robin Vos` and `Assembly Democrats`, while State Senate statewide contests use year-specific Republican chamber leaders such as `Chris Kapenga` for 2022 and `Mary Felzkowski` for 2024 and later.

## Data And Method

At runtime, the site is static. The analytical value comes from the prepared data behind it.

### 1. Normalize Recent Excel Results

[`scripts/load_recent_excel_results.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/load_recent_excel_results.py) converts newer Wisconsin Elections Commission workbook exports into normalized CSV files in the same year folders under `data/`.

It currently contains explicit workbook-name mappings for newer files such as:

- 2024 spring and general exports
- 2025 spring exports
- 2026 spring exports

Run:

```powershell
python scripts/load_recent_excel_results.py
```

### 2. Download And Convert TIGER Geography

[`scripts/fetch_wi_tiger_geojson.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/fetch_wi_tiger_geojson.py) downloads Wisconsin TIGER shapefiles and converts them to GeoJSON used by the app.

Outputs include:

- counties
- 2020 voting districts
- 2020 census blocks
- 2010 census blocks
- congressional districts
- 2022 and 2024 state legislative districts
- stitched 2008 county-based layers for older geography support

Run:

```powershell
python scripts/fetch_wi_tiger_geojson.py
```

Note: this step downloads data from Census endpoints, so it requires network access.

### 3. Build NHGIS Block Bridge Crosswalks

[`scripts/build_wi_nhgis_block_bridges.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/build_wi_nhgis_block_bridges.py) reads NHGIS crosswalk ZIPs and writes normalized CSV bridges under `data/crosswalks/`.

These bridges connect block vintages across redistricting and census-era geography changes. They are a major part of how older election geography is made comparable to modern district frameworks.

Run:

```powershell
python scripts/build_wi_nhgis_block_bridges.py
```

### 4. Build Precinct-To-District Crosswalks

[`scripts/build_wi_district_crosswalks.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/build_wi_district_crosswalks.py) assigns 2020 precinct geography to congressional, 2022 assembly/senate, and 2024 assembly/senate district layers using representative points and area-weighted aggregation.

Outputs:

- `data/crosswalks/precinct_to_cd118.csv`
- `data/crosswalks/precinct_to_2022_state_house.csv`
- `data/crosswalks/precinct_to_2022_state_senate.csv`
- `data/crosswalks/precinct_to_2024_state_house.csv`
- `data/crosswalks/precinct_to_2024_state_senate.csv`

Run:

```powershell
python scripts/build_wi_district_crosswalks.py
```

These files are the bridge between precinct-scale vote geography and district-scale political analysis.

### 5. Aggregate Statewide Election Results

[`scripts/build_wi_elections_aggregated.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/build_wi_elections_aggregated.py) reads normalized ward-level CSV files and produces:

- `data/wi_elections_aggregated.json`

This is the main statewide election dataset used by the site.

Run:

```powershell
python scripts/build_wi_elections_aggregated.py
```

### 6. Build District Result Slices

[`scripts/build_wi_district_results.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/build_wi_district_results.py) combines statewide ward results with the precinct-to-district crosswalks to create district-level slices for multiple district scopes and line vintages.

Outputs include:

- `data/wi_district_results_2022_lines.json`
- many contest-specific JSON files in `data/district_contests/`
- many contest-specific JSON files in `data/district_contests_2024_lines/`

Run:

```powershell
python scripts/build_wi_district_results.py
```

This is the step that turns historical statewide vote totals into comparable modern district results.

### 7. Build Precinct Centroids

[`scripts/build_wi_precinct_centroids.py`](/C:/Users/Shama/OneDrive/Documents/Side_Projects/Side_Projects/WIPrecinctmap/scripts/build_wi_precinct_centroids.py) creates a weighted centroid point file for precinct labels and map interactions.

Output:

- `data/mappings/precinct_centroids.geojson`

Run:

```powershell
python scripts/build_wi_precinct_centroids.py
```

Together, those scripts do four main things:

- normalize source election files into a consistent tabular format
- download and convert Wisconsin Census geography into map-ready GeoJSON
- build precinct-to-district and block-bridge crosswalks so votes can be reaggregated across line vintages
- produce statewide and district-level JSON outputs consumed by the browser app

Conceptually, the pipeline lets the project move from:

- old election returns tied to old reporting geography

to:

- historically comparable results expressed in modern district terms

## Data Sources

Main upstream sources include:

- Wisconsin Elections Commission ward-by-ward and county-by-county exports
- U.S. Census TIGER/Line shapefiles
- NHGIS block bridge crosswalk files

This repository stores many derived outputs directly so GitHub Pages can serve the site without any server-side processing.

## What Makes This Useful

There are many places to look up Wisconsin results. Fewer places let you do all of the following in one interface:

- move from statewide results down to precinct geography
- compare fall and spring political geographies
- inspect district performance under different line vintages
- trace long-run partisan movement instead of just one-cycle swings
- study where coalition change is concentrated rather than only seeing the statewide topline

The project is meant to be useful to anyone trying to understand Wisconsin as a political place rather than just a sequence of election nights.

## Notes On Interpretation

- Some district results are derived by reaggregating precinct-level returns through geographic crosswalks rather than copied from official district canvasses.
- District comparisons across line vintages are best understood as analytical reconstructions of how the same vote base maps onto different boundaries.
- Not every contest exists in every year, and spring-election coverage is naturally different from fall-election coverage.
- As with any long-run precinct project, source formats and naming conventions change over time, so normalization is part of the work.

## License

No license file is currently present in this repository. If you want others to reuse or contribute to the project with clear terms, add a `LICENSE` file and update this section.
