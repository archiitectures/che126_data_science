# Staged examples

These files demonstrate the new workflow; they have not been merged into the
published dry/wet tables or uploaded to Hugging Face.

- `fsri_observations.csv`: 60 tidy observations from the existing pinned HFM
  snapshot (36 conductivity, 24 volumetric heat capacity). This is another
  representation of existing evidence, not new measurements. Mass-specific heat
  derived using density in the legacy table is intentionally not re-derived here.
- `celgard_2400_observations.csv`: 8 supported scalar values/bounds from the January
  2026 official PDF. Only shrinkage has a known temperature, and it is exposure
  temperature. Porosity is calculated. Other temperatures and electrolyte state
  remain unknown.
- `celgard_2400_review.json`: two tensile rows with ambiguous `Kg/cm2` units, held
  for review. They are not silently dropped or converted.
- `acquisition_receipts.json`: source URLs, timestamps, byte counts and SHA-256
  hashes for the downloaded Celgard PDF and FSRI HDPE public page. The referenced
  `data/raw/` files are local and Git-ignored; fetch the source again to reproduce
  acquisition (dynamic pages may yield a different hash).

See `docs/COLLECTION_GUIDE.md` for extraction and coverage commands.
