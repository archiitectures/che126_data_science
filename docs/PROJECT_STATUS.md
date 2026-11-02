## Current project snapshot — 2026-11-02

The assembled dataset contains **10,676 distinct value/context points**, **13,379 accepted evidence observations**, and **37 properties**. **5,121 contexts have numeric temperatures**; 5,555 lack supported numeric conditions. Of 7,950 measured separator/component contexts, 2,571 have numeric temperatures. Bulk references remain separately identified.

This pass added 25 MD-reference contexts and 40 temperature-resolved separator observations (including 32 calibrated figure estimates). Source review corrected 105 observations and held 65 ambiguous observations for review. All withdrawn evidence remains traceable. The total temperature count fell after removing incorrect inherited conditions.

Run `.venv/bin/python scripts/assemble_dataset.py --check-replay` to rebuild from the existing local source archive. Validation: 167 tests pass; 42 generated artifacts replay byte-for-byte. A fresh clone requires the source archive for a full rebuild. Arbitrary PDF/figure interpretation still requires reviewed calibration and attribution.

See [the comprehensive project guide](COMPREHENSIVE_PROJECT_REPORT.md), [dataset](https://huggingface.co/datasets/archiitecture/che126), and [figures](../visualizations/README.md). Earlier dated sections below are historical snapshots.
