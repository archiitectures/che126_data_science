"""Explicit property aliases and test-condition parsing, shared by adapters."""

import re

ALIASES = (
    (r"contact\s*[- ]?\s*angle", "contact_angle"),
    (r"shutdown\s+(?:response\s+time|speed)", "shutdown_response_time"),
    (r"tortuosity", "tortuosity"),
    (r"electric(?:al)?\s+resistance", "electrical_resistance"),
    (r"ionic\s+conductivity", "ionic_conductivity"),
    (
        r"electrolyte\s+(?:uptake|absorption)(?!\s+(?:speed|rate|time))",
        "electrolyte_uptake",
    ),
    (r"(?:thermal\s+)?shrink(?:age)?", "thermal_shrinkage"),
    (r"(?:tensile\s+(?:rupture\s+)?)?elongation", "elongation"),
    (r"tensile\s+(?:rupture\s+)?(?:strength|stress)", "tensile_strength"),
    (r"puncture\s+(?:strength|force|resistance)", "puncture_force"),
    (r"(?:film\s+)?thickness", "thickness"),
    (r"porosity", "porosity"),
    (r"gurley", "gurley_time"),
    (r"air\s+permeability", "air_permeability_time"),
    (r"pore\s+(?:size|diameter)", "pore_size"),
    (r"basis\s+weight", "basis_weight"),
    (r"thermal\s+conductivity", "thermal_conductivity"),
    (r"(?:specific\s+heat|heat\s+capacity)", "specific_heat_capacity"),
    (r"density", "density"),
    (r"shutdown\s+temp(?:erature)?\b", "shutdown_temperature"),
    (r"meltdown\s+temp(?:erature)?\b", "meltdown_temperature"),
    (r"melting\s+(?:point|temperature)", "melting_temperature"),
)
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def property_name(label: str) -> str | None:
    for pattern, name in ALIASES:
        if re.search(pattern, label, re.IGNORECASE):
            if name in {
                "tortuosity",
                "electrical_resistance",
                "shutdown_temperature",
                "meltdown_temperature",
                "air_permeability_time",
            } and re.search(r"difference|increase|change|ratio", label, re.IGNORECASE):
                return None
            return name
    return None


def canonical_unit_text(text: str) -> str:
    text = (
        text.strip()
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("²", "2")
        .replace("³", "3")
    )
    text = re.sub(r"(?<=[a-zA-Z])\s+(?=[23]\b)", "", text)
    if re.fullmatch(r"[°º]?\s*C\.?", text, re.IGNORECASE):
        return "C"
    return {
        "Seconds": "s",
        "seconds": "s",
        "sec": "s",
        "second": "s",
        "Ω": "ohm",
        "°": "deg",
        "degrees": "deg",
        "Grams Force (gf)": "gf",
        "Kg/cm2": "kg/cm2",
        "sec/100 ml": "s",
        "sec/100 cc": "s",
        "sec/100 cm3": "s",
        "seconds/100 cm3": "s",
        "kgf/cm2": "kgf/cm2",
        "W/mK": "W/(m K)",
        "J/(m³K)": "J/(m3 K)",
        "°C": "C",
    }.get(text, text)


def conditions(text: str, *, role="exposure") -> dict:
    """Extract only explicit temperature/duration; caller chooses context scope."""
    result = {}
    rate = re.search(rf"({NUMBER})\s*[°º]?\s*(?:C|K)\s*/\s*min", text, re.IGNORECASE)
    if rate:
        result["heating_rate_C_min"] = float(rate[1])
    temperatures = [
        m
        for m in re.finditer(rf"({NUMBER})\s*[°º]?\s*(C|K|F)\b", text, re.IGNORECASE)
        if not re.match(r"\s*/\s*(?:min|s|h)", text[m.end() :], re.IGNORECASE)
    ]
    ambiguous = len({(m[1], m[2].upper()) for m in temperatures}) > 1 or bool(
        re.search(
            rf"{NUMBER}\s*(?:[–—-]|to|and|/|±|\+/-)\s*{NUMBER}\s*[°º]?\s*[CKF]\b",
            text,
            re.IGNORECASE,
        )
    )
    if ambiguous:
        result["quality_flag"] = "ambiguous_temperature_condition"
    if temperatures and not ambiguous:
        temperature = temperatures[0]
        value = float(temperature[1])
        unit = temperature[2].upper()
        result.update(
            temperature_C=value - 273.15
            if unit == "K"
            else (value - 32) * 5 / 9
            if unit == "F"
            else value,
            temperature_role=role,
        )
    duration = re.search(
        rf"({NUMBER})\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b",
        text,
        re.IGNORECASE,
    )
    if duration:
        factor = (
            60
            if duration[2].lower().startswith("h")
            else 1 / 60
            if duration[2].lower().startswith("s")
            else 1
        )
        result["duration_min"] = float(duration[1]) * factor
    return result


def direction(text: str) -> str:
    found = re.findall(r"(?<![A-Z0-9])(MD|TD)(?:[12])?(?![A-Z0-9])", text.upper())
    return found[0] if len(set(found)) == 1 else "unspecified"


def values(cell: str, label: str, *, default="reported") -> list[tuple[str, str]]:
    """Only scalar/paired numeric cells; ranges and qualifiers require review."""
    cell = cell.strip().replace("−", "-")
    pair = re.fullmatch(rf"\s*({NUMBER})\s*/\s*({NUMBER})\s*", cell)
    if pair:
        if re.search(r"typical\s*/\s*(?:min|minimum)", label, re.IGNORECASE):
            return [(pair[1], "typical"), (pair[2], "minimum")]
        if re.search(r"typical\s*/\s*(?:max|maximum)", label, re.IGNORECASE):
            return [(pair[1], "typical"), (pair[2], "maximum")]
        return [(cell, "reported")]
    comparison = re.fullmatch(rf"\s*(>=|<=|≥|≤)\s*({NUMBER})\s*", cell)
    if comparison:
        return [
            (comparison[2], "minimum" if comparison[1] in {">=", "≥"} else "maximum")
        ]
    if re.fullmatch(NUMBER, cell):
        statistic = (
            "maximum"
            if re.search(r"\(max(?:imum)?\b", label, re.IGNORECASE)
            else "minimum"
            if re.search(r"\(min(?:imum)?\b", label, re.IGNORECASE)
            else default
        )
        return [(cell, statistic)]
    return [(cell, "reported")]
