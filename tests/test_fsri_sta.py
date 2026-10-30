"""STA protocol checks and real-row selection; negative baseline offsets survive."""

import hashlib
from dataclasses import replace

import pytest

from che126_data_science.data_mining.acquisition import RawDocument
from che126_data_science.data_mining.fsri_sta import extract_sta


def test_sta_metadata_units_and_native_selection(tmp_path):
    name = "HDPE_STA_N2_10KData_210909_R1.csv"
    data = tmp_path / name
    data.write_text(
        "##Temp./°C,Time/min,DSC(subtr.2)/(mW/mg),Mass loss(subtr.2)/mg,Sensit./(uV/mW)\n49.92,1,-0.2,-0.01,1\n50.02,2,-0.1,-0.02,1\n55.4,3,0.3,0.1,1\n60.1,4,0.4,0.2,1\n"
    )
    meta = tmp_path / name.replace("Data_", "Meta_")
    meta.write_text(
        "#MATERIAL:,HDPE\n#SAMPLE:,HDPE_10K_1\n#FILE:,HDPE_STA_N2_10K_210909_R1.ngb-ss3\n#SAMPLE MASS /mg:,4.0\n"
    )
    doc = RawDocument(
        "sta",
        "fsri",
        str(data),
        hashlib.sha256(data.read_bytes()).hexdigest(),
        url="https://raw.githubusercontent.com/test/01_Data/HDPE/STA/N2/10K_min/"
        + name,
    )
    context = {
        "filename": name,
        "sta_metadata": {
            "filename": meta.name,
            "path": str(meta),
            "sha256": hashlib.sha256(meta.read_bytes()).hexdigest(),
            "url": "https://example.com/meta",
        },
    }
    rows, artifacts = extract_sta(doc, context)
    assert len(rows) == 4 and {r.temperature_C for r in rows} == {50.02, 60.1}
    assert all(r.review_status == "accepted" for r in rows)
    heat = next(r for r in rows if r.property == "mass_specific_heat_flow")
    assert heat.value == -100 and heat.unit == "W/kg" and heat.original_value == "-0.1"
    mass = next(r for r in rows if r.property == "sta_mass_change")
    assert mass.value == pytest.approx(-2e-8) and mass.unit == "kg"
    assert all(r.curve_id and r.heating_rate_C_min == 10 for r in rows)
    assert artifacts[0]["native_rows"] == 4
    assert extract_sta(doc, context)[0] == rows
    with pytest.raises(ValueError, match="filenames differ"):
        extract_sta(
            doc,
            {
                **context,
                "sta_metadata": {**context["sta_metadata"], "filename": "wrong.csv"},
            },
        )
    with pytest.raises(ValueError, match="hash mismatch"):
        extract_sta(
            doc,
            {**context, "sta_metadata": {**context["sta_metadata"], "sha256": "bad"}},
        )
    with pytest.raises(ValueError, match="source path"):
        extract_sta(replace(doc, url=doc.url.replace("/N2/", "/Air/")), context)
    meta.write_text(meta.read_text().replace("HDPE_10K_1", "HDPE_10K_2"))
    context["sta_metadata"]["sha256"] = hashlib.sha256(meta.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="replicate mismatch"):
        extract_sta(doc, context)
    meta.write_text(meta.read_text().replace("#MATERIAL:,HDPE", "#MATERIAL:,PVC"))
    context["sta_metadata"]["sha256"] = hashlib.sha256(meta.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="material mismatch"):
        extract_sta(doc, context)


def test_density_preserves_multiword_material_and_missing_temperature(tmp_path):
    from che126_data_science.data_mining.structured import extract_fsri

    name = "Black_PMMA_Density_Dry_R1.csv"
    path = tmp_path / name
    path.write_text("Sample,Wrong label\nSample Density [kg/m3],1180\n")
    doc = RawDocument(
        "density", "fsri", str(path), hashlib.sha256(path.read_bytes()).hexdigest()
    )
    rows, _ = extract_fsri(doc, {"filename": name, "polymer": "Black_PMMA"})
    assert rows[0].polymer == "Black_PMMA"
    assert rows[0].temperature_C is None and rows[0].value == 1180
    rows, _ = extract_fsri(doc, {"filename": name})
    assert rows[0].polymer == "Black_PMMA"
