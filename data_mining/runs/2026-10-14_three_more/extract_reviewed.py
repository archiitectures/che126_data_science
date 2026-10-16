"""Reproduce visually reviewed EPH table transcription; run from repository root."""
import json
from pathlib import Path

from che126_data_science.data_science.observations import (
    Observation, coverage, read_observations, write_observations,
)

ROOT = Path('data_mining/runs/2026-10-14_three_more')
receipt = next(r for r in json.loads((ROOT / 'receipts.json').read_text())
               if 'Lithium-Prod-Portfolio-21-04-23.pdf' in r['url'])
products = ('9EPH', '12EPH', '16EPH')
# PDF page 2, EPH table; independently checked against rendered page.
source_rows = [
    ('Nominal Thickness', 'thickness', 'um', 'unspecified', [9, 12, 16]),
    ('Basis Weight', 'basis_weight', 'g/m2', 'unspecified', [4.6, 6.2, 8.1]),
    ('Nominal Porosity', 'porosity', '%', 'unspecified', [48, 48, 48]),
    ('Air Permeability', 'air_permeability_time', 's', 'unspecified', [75, 95, 125]),
    ('Tensile Elongation MD', 'elongation', '%', 'MD', [68, 68, 81]),
    ('Tensile Elongation TD', 'elongation', '%', 'TD', [249, 289, 284]),
    ('Thermal Shrinkage MD @120C, 1 hr', 'thermal_shrinkage', '%', 'MD', [9.5, 7.5, 9]),
    ('Thermal Shrinkage TD @120C, 1 hr', 'thermal_shrinkage', '%', 'TD', [4, 2, 3.5]),
]
rows = []
for label, prop, unit, direction, values in source_rows:
    for product, value in zip(products, values, strict=True):
        thermal = prop == 'thermal_shrinkage'
        air = prop == 'air_permeability_time'
        rows.append(Observation(
            record_id=f'entek_2021_{product}_{prop}_{direction}',
            sample_id=f'entek_{product}', material='PE (UHMWPE-based)',
            property=prop, value=value, unit=unit, source_url=receipt['url'],
            source_locator=f'PDF page 2; EPH table; column {product}; row {label}; SHA256 {receipt["sha256"]}',
            sample_form='separator', temperature_C=120 if thermal else None,
            temperature_role='exposure' if thermal else 'unknown', direction=direction,
            method='Air permeability time for 100 ml; apparatus/standard unspecified' if air else 'unspecified',
            conditions='heat exposure 1 hour; measurement temperature unspecified' if thermal else
                       'Reported air volume 100 ml; pressure and area unspecified' if air else 'unspecified',
            value_type='typical', raw_value=str(value), raw_unit='sec/100 ml' if air else unit,
            notes='Historical 2021 ENTEK manufacturer portfolio; visually reviewed EPH table. '
                  'Biaxially oriented, wet-process PE largely composed of UHMWPE. Manufacturing wet process '
                  'does not establish electrolyte-wet measurement state. Nominal values are not independent '
                  'specimen measurements; no ambient measurement temperature inferred.'))
write_observations(rows, ROOT / 'separator_observations.csv')
assert read_observations(ROOT / 'separator_observations.csv') == rows
old = read_observations('data_mining/runs/2026-10-14_pe_pp/separator_observations.csv')
assert {r.sample_id for r in rows}.isdisjoint(r.sample_id for r in old)
write_observations(old + rows, ROOT / 'combined_separator_observations.csv')
report = coverage(rows, ['thickness', 'basis_weight', 'porosity', 'air_permeability_time',
                        'elongation', 'thermal_shrinkage', 'tensile_strength', 'puncture_force'],
                  [25, 60, 90, 105, 120])
(ROOT / 'coverage.json').write_text(json.dumps(report, indent=2) + '\n')
review = {'withheld': [
    {'row': 'Puncture Resistance', 'unit_as_printed': 'g', 'values': dict(zip(products, [255,315,375])),
     'reason': 'Mass symbol used for a force quantity; do not silently convert to newtons.'},
    {'row': 'Tensile Strength MD', 'unit_as_printed': 'kg/cm2', 'comparator': '>=',
     'values': dict(zip(products,[1100,1000,900])), 'reason': 'Force-unit interpretation requires confirmation; retain lower bounds.'},
    {'row': 'Tensile Strength TD', 'unit_as_printed': 'kg/cm2', 'comparator': '>=',
     'values': dict(zip(products,[800,800,700])), 'reason': 'Force-unit interpretation requires confirmation; retain lower bounds.'}],
    'air_permeability': 'Stored as time for the stated 100 ml volume, not assumed Gurley/JIS method.',
    'source_version': '2021 portfolio; current product availability/specifications not established.'}
(ROOT / 'review.json').write_text(json.dumps(review, indent=2) + '\n')
summary = {'new_separator_products': list(products), 'new_scalar_records': len(rows),
           'scalar_records_per_product': 8, 'known_exposure_temperature_C': 120,
           'known_temperature_records': 6, 'unknown_temperature_records': 18, 'known_measurement_temperature_records': 0,
           'combined_separator_products': len({r.sample_id for r in old+rows}),
           'combined_separator_records': len(old+rows), 'google_billing_enabled': False,
           'google_queries_executed': 0, 'cloud_spend_usd': 0}
(ROOT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
