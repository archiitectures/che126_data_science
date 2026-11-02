"""Keep finite strains, differential coefficients and phase fractions distinct."""

from types import SimpleNamespace

import pytest

from che126_data_science.data_science.master import make_observation


def observation(prop, value, unit):
    document = SimpleNamespace(
        restrictions="test source",
        source_id="test",
        source="manual",
        url="https://example.org/source",
        path="source.csv",
        sha256="a" * 64,
    )
    return make_observation(
        document,
        label=prop,
        prop=prop,
        raw_value=value,
        raw_unit=unit,
        sample_id="sample",
        polymer="PE",
        sample_form="separator",
    )


def test_finite_expansion_strain_is_not_a_per_kelvin_coefficient():
    strain = observation("thermal_expansion_strain", -2, "%")
    coefficient = observation("linear_thermal_expansion_coefficient", 80, "ppm/K")
    assert strain.value == -2 and strain.unit == "%"
    assert coefficient.value == pytest.approx(80e-6)
    wrong = observation("isothermal_compressibility", 10, "%")
    assert wrong.review_status == "pending"


def test_compression_sign_and_crystallinity_bounds():
    assert observation("maximum_compression_strain", -18.56, "%").value == -18.56
    invalid = observation("crystallinity", 101, "%")
    assert invalid.review_status == "pending"
    assert invalid.quality_flag == "validation_failed"
