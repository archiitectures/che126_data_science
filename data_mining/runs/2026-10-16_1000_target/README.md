# Collection completed - 2026-10-19

The conservative target is achieved: **1004 distinct normalized value/context points**, supported by **2086 accepted source observations**. 1082 equal value/context rows were collapsed while all evidence was retained. This definition intentionally merges equal contexts across sources even if they might represent separate experiments; it does not certify independent experiments.

The point view includes **835 separator/component points** and **169 bulk references**. Only **124 distinct measured separator points have explicit temperatures**. This is not 1,000 temperature-complete separator experiments. The master has 20,477 pending review entries, excluded from these counts.

## Sources and tools

| Origin | Input and extraction | Distinct points |
| --- | --- | ---: |
| Celgard | PDF tables via PyMuPDF | 224 |
| FSRI | HFM .tst SI tables (157) and density CSV (12) | 169 |
| Patent pages | HTML grids/methods via BeautifulSoup + lxml | 581 |
| Earlier patent acquisition | Saved official BigQuery JSON -> verified structured CSV import | 30 |

Content-addressed DocumentStore/HTTPClient acquisition, versioned Pipeline adapters, canonical normalization/validation, and CSV/Parquet aggregation were used. The additional unique_points exporter collapses equal recorded value/condition contexts; unique_point_evidence.json preserves every supporting record ID. Celgard used PyMuPDF geometry, not OCR. Patent HTML tables were expanded and linked to explicit test protocols. FSRI raw/snapshot representations were linked to avoid duplicate evidence. No digitized graph points, PoLyInfo data or unverified review rows were counted.

Thirty previously reviewed separator strengths from US20250326880A1 were mechanically checked against the saved official full text and imported through the structured importer: 15 tensile values measured at 23 C and 15 puncture values with unknown test temperature. Controls without strength data, manufacturing temperatures and pressed-sheet elongation were excluded. See verified_snapshot_lineage.json for hashes and source lineage. This import reused the earlier authorized acquisition; no new BigQuery query or billing change was made.

Collection resumed from saved public patent reference links, prioritized relevant microporous/polyolefin titles and checked nine additional material leads. EPO credentials were absent. All acquisition was public/cached; source permissions are retained in the manifest. Extraction versions v5/v6 added tested description-line support, numbered heading/body protocols, explicit units, Ex headers and aligned number-only headers beneath a single Example group. Uncertain comparative groups and normalized-thickness forces remain in review. The remaining source queue is preserved.

## Properties

There are **13 property categories overall** and **11 in the separator/component view**.

| Property | Distinct points |
| --- | ---: |
| air_permeability_time | 30 |
| basis_weight | 9 |
| density | 21 |
| elongation | 7 |
| gurley_time | 38 |
| pore_size | 41 |
| porosity | 191 |
| puncture_force | 127 |
| tensile_strength | 26 |
| thermal_conductivity | 97 |
| thermal_shrinkage | 201 |
| thickness | 156 |
| volumetric_heat_capacity | 60 |

## Materials and construction

Three explicitly identified separator polymer labels: PP (113 points), PP/PE/PP (111), and PE/PP (30). The PE/PP records distinguish block copolymers from physical blends. Six known construction labels occur: monolayer, trilayer, laminate, microporous component, PE/PP block copolymer, and PE/PP physical blend. Polymer identity remains unresolved for 581 patent-derived points. Bulk references include HDPE, LDPE, PP, PE foam/pipe insulation and cellulose insulation; raw source labels are preserved rather than silently unified.

## Temperatures

**14 distinct reported temperatures overall:** 10.0, 15.0, 15.01, 20.01, 23.0, 30.01, 40.01, 45.01, 90.0, 105.0, 120.0, 130.0, 140.0, 170.0 C. A total of 365 distinct points has an explicit temperature; the remainder is unknown.

- Measurement temperatures: 10.0, 15.0, 15.01, 20.01, 23.0, 30.01, 40.01, 45.01 C.
- Exposure temperatures: 90.0, 105.0, 120.0, 130.0, 140.0, 170.0 C.
- Measured separator temperatures: 23.0, 90.0, 105.0, 120.0, 130.0, 140.0, 170.0 C.
- Temperature-resolved measured separator points: 109 shrinkage exposure results and 15 tensile measurements.

Property coverage is not complete at each temperature. Ionic conductivity, electrolyte uptake and several thermal transition properties remain absent; many polymer identities and electrolyte states remain unknown. Do not infer missing temperatures, dry/wet conditions or polymer composition from search keywords or processing descriptions.

## Final artifacts and validation

- data/processed/unique_points.csv and unique_points.parquet: conservative point view.
- data/processed/unique_point_evidence.json: supporting observation links.
- data/processed/master_observations.csv and .parquet: complete accepted source evidence.
- data/processed/collection_breakdown.json and unique_points_summary.json: exact counts and definitions.
- coverage.csv and summary.json in this run directory: full-master coverage (not the conservative counts).
- output/pdf/code_review_handbook.pdf: 16-page newcomer handbook, including review findings/fixes and final source/coverage breakdown.

Validation passed for source file hashes, unique IDs/context fingerprints, complete evidence links, finite values, temperature roles and matching CSV/Parquet rows. The code suite has 104 passing tests. No upload, commit, push, paid query or billing change was performed.
