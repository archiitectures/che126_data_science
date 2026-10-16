"""Export a conservative value/context view; preserve all evidence in the master."""
import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from che126_data_science.data_science.master import atomic_bytes, atomic_json, fingerprint

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'data/processed'
CONTEXT_FIELDS = (
    'polymer', 'product', 'sample_form', 'property', 'value', 'unit', 'statistic',
    'record_type', 'temperature_C', 'temperature_role', 'duration_min', 'direction',
    'electrolyte_state', 'separator_architecture', 'coating', 'electrolyte_salt',
    'electrolyte_solvent', 'electrolyte_concentration', 'heating_rate_C_min',
)

def export():
    source = pq.read_table(DIRECTORY / 'master_observations.parquet')
    groups = defaultdict(list)
    for row in source.to_pylist():
        groups[fingerprint({k: row[k] for k in CONTEXT_FIELDS})].append(row)
    representatives, links = [], []
    for point_id, evidence in sorted(groups.items()):
        evidence.sort(key=lambda r: r['observation_id'])
        selected = dict(evidence[0])
        selected.update(unique_point_id=point_id, supporting_observations=len(evidence))
        representatives.append(selected)
        links.append({'unique_point_id': point_id,
                      'representative_observation_id': selected['observation_id'],
                      'supporting_observation_ids': [r['observation_id'] for r in evidence]})
    schema = source.schema.append(pa.field('unique_point_id', pa.string())).append(
        pa.field('supporting_observations', pa.int64()))
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(representatives, schema=schema), sink, compression='zstd')
    atomic_bytes(DIRECTORY / 'unique_points.parquet', sink.getvalue().to_pybytes())
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=schema.names, lineterminator='\n')
    writer.writeheader(); writer.writerows(representatives)
    atomic_bytes(DIRECTORY / 'unique_points.csv', stream.getvalue().encode())
    atomic_json(DIRECTORY / 'unique_point_evidence.json', links)
    separator = [r for r in representatives if r['sample_form'] in {'separator', 'separator_component'}]
    summary = {
        'accepted_master_rows': source.num_rows, 'unique_value_context_points': len(groups),
        'collapsed_rows': source.num_rows - len(groups),
        'separator_or_component_points': len(separator),
        'bulk_reference_points': sum(r['sample_form']=='bulk_reference' for r in representatives),
        'measured_separator_points': sum(r['record_type']=='measured' for r in separator),
        'temperature_resolved_measured_separator_points': sum(
            r['record_type']=='measured' and r['temperature_C'] is not None for r in separator),
        'by_property': dict(Counter(r['property'] for r in representatives)),
        'by_source': dict(Counter(r['source_type'] for r in representatives)),
        'key_fields': CONTEXT_FIELDS,
        'interpretation': 'Conservative distinct normalized value/context view. Equal contexts across sources collapse even when experiments might differ. Unknown identity is not invented. This does not certify independent experiments or complete material/temperature coverage.',
    }
    atomic_json(DIRECTORY / 'unique_points_summary.json', summary)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    export()
