"""Export explicit-temperature contexts without inventing missing conditions."""

import csv
import io
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from che126_data_science.data_science.master import atomic_bytes

ROOT = Path(__file__).resolve().parents[1]


def export():
    table = pq.read_table(ROOT / "datasets/unique_points.parquet")
    rows = [r for r in table.to_pylist() if r["temperature_C"] is not None]
    subset = pa.Table.from_pylist(rows, schema=table.schema)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=table.schema.names, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    sink = pa.BufferOutputStream()
    pq.write_table(subset, sink, compression="zstd")
    for folder in [ROOT / "datasets", ROOT / "data/processed"]:
        atomic_bytes(
            folder / "temperature_resolved_points.csv", stream.getvalue().encode()
        )
        atomic_bytes(
            folder / "temperature_resolved_points.parquet", sink.getvalue().to_pybytes()
        )
    print(
        f"Explicit measurement/exposure temperatures: {len(rows)} / {len(table)}; roles and bulk-reference labels retained."
    )


if __name__ == "__main__":
    export()
