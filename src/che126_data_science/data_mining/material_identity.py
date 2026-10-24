"""Evidence-bound sample recipes and explicit recipe inheritance in patent HTML.

Only experimental sample blocks and complete composition tables can assign a
polymer. Background text and optional material lists never label a sample.
"""

import json
import re
from dataclasses import dataclass

SAMPLE = re.compile(
    r"(?P<kind>comparative|comparison|comp(?:arative)?\.?|com\.?|conventional|reference|preparation|working)?\s*"
    r"(?:examples?|ex\.?)\s*(?P<number>\d+(?:[-–]\d+)?)",
    re.IGNORECASE,
)
POLYMERS = {
    "PE": r"\b(?:polyethylene(?!\s+(?:terephthalate|naphthalate|glycol|oxide))|UHM?W?PE|UHMwPE|HDPE|LDPE|LLDPE|PE(?:[a-c]|\s*\d+)?)\b",
    "PP": r"\b(?:polypropylene(?!\s+(?:glycol|carbonate))|PP(?:[a-c]|\s*\d+)?)\b",
    "PET": r"\b(?:polyethylene terephthalate|PET|co-PET)\b",
    "PI": r"\b(?:polyimide|PI)\b",
    "PA": r"\b(?:polyamide(?!-imide)|PA|nylon)\b",
    "PAN": r"\b(?:polyacrylonitrile|PAN)\b",
    "PPTA": r"\b(?:poly-p-phenylene terephthalamide|PPTA|Kevlar)\b",
    "Aramid": r"\baramid\b",
    "PBO": r"\b(?:poly-p-phenylene (?:benzodioxazole|benzoxazole|benzoxadiazole)|PBO)\b",
    "Cellulose": r"\b(?:cellulose|lyocell|tencel)\b",
    "PVDF": r"\b(?:polyvinylidene (?:fluoride|difluoride)|PVDF(?:-HFP)?)\b",
    "PTFE": r"\b(?:polytetrafluoroethylene|PTFE)\b",
    "PEEK": r"\b(?:polyether ether ketone|PEEK)\b",
    "PPS": r"\b(?:polyphenylene sulfide|PPS)\b",
    "PVA": r"\b(?:polyvinyl alcohol|PVA)\b",
    "PS": r"\b(?:polystyrene|PS)\b",
    "PMMA": r"\b(?:polymethyl methacrylate|PMMA)\b",
    "PEO": r"\b(?:polyethylene oxide|PEO)\b",
}
PATTERNS = {p: re.compile(pattern, re.IGNORECASE) for p, pattern in POLYMERS.items()}
OPTIONAL = re.compile(
    r"\b(?:may|preferably|can be|selected from|such as|for example|either)\b",
    re.IGNORECASE,
)
ACTION = re.compile(
    r"prepar|mix|combin|blend|knead|extrud|laminat|used|using|compos|consist|formed|manufactur|obtain|provid",
    re.IGNORECASE,
)
BASE = re.compile(
    r"substrate|base (?:film|membrane)|porous (?:film|membrane)|microporous|polymer[- ](?:mixture|diluent)|polyolefin (?:composition|resin)|polyethylene (?:composition|solution)|resin composition|raw material|powder|pellet|web|fiber|fibre|fabric|nonwoven",
    re.IGNORECASE,
)
COATING = re.compile(r"coat|binder|slurry|adhesive", re.IGNORECASE)
INHERIT = re.compile(
    r"(?:same\s+(?:manner|method|way|procedure|conditions|substrate)|method\s+(?:of|as)|according to|similar(?:ly)?(?: manner)? to|(?:membrane|film|substrate)\s+(?:obtained|prepared|produced)\s+in)"
    r".{0,100}?(?P<sample>(?:comparative\s+|comp\.?\s*|preparation\s+|working\s+)?(?:example|ex\.?)\s*\d+(?:[-–]\d+)?)",
    re.IGNORECASE,
)


def normalize_sample(text):
    match = SAMPLE.fullmatch(text.strip().strip("[]()<>{}* .:"))
    if not match:
        return None
    kind = (match["kind"] or "").lower().rstrip(".")
    prefix = (
        "Comparative "
        if kind.startswith("com")
        else (kind.capitalize() + " " if kind else "")
    )
    return prefix + "Example " + match["number"].replace("–", "-")


def material_names(text):
    names = set()
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            token = match[0]
            # Pa is pressure, not PA (polyamide). Other short acronyms likewise
            # require their printed capitalization; full chemical names do not.
            if (
                len(token) <= 5
                and not token.isupper()
                and not re.fullmatch(r"(?:PE|PP)[abc0-9]", token)
            ):
                continue
            names.add(name)
    if "PPTA" in names:
        names.discard("Aramid")
    return names


def material_label(names):
    if not names:
        return None
    if names <= {"PE", "PP"}:
        return "PE/PP" if len(names) == 2 else next(iter(names))
    return "/".join(sorted(names))


def locator(element):
    named = element.get("id") or (
        "num:" + element["num"] if element.get("num") else None
    )
    if named:
        return named
    # Older patent HTML has no paragraph IDs. A deterministic DOM path plus the
    # immutable document SHA still provides an exact, checkable locator.
    path = []
    current = element
    while current is not None and current.name != "[document]":
        siblings = current.find_previous_siblings(current.name)
        path.append(f"{current.name}:nth-of-type({len(siblings) + 1})")
        current = current.parent
    return "css:" + " > ".join(reversed(path))


def explicit_base_names(text):
    names = set()
    for name, pattern in PATTERNS.items():
        for hit in pattern.finditer(text):
            if name not in material_names(hit[0]):
                continue
            if re.match(
                r"\s*(?:\([^)]{0,100}\)\s*)?(?:(?:fine\s+)?(?:micro[- ]?)?porous\s+(?:film|membrane|substrate)|fabric panel|nonwoven fabric)",
                text[hit.end() :],
                re.IGNORECASE,
            ):
                names.add(name)
    return names


def clean_text(element):
    return " ".join(
        str(s).strip()
        for s in element.find_all(string=True)
        if str(s).strip() and s.find_parent("table") is None
    )


@dataclass(frozen=True)
class Identity:
    polymer: str | None
    status: str
    evidence: tuple = ()
    reason: str = ""

    def fields(self):
        return {
            "material_identity_status": self.status,
            "material_identity_evidence": json.dumps(self.evidence, ensure_ascii=False)
            if self.evidence
            else None,
            "material_identity_reason": self.reason or None,
        }


class PatentIdentities:
    def __init__(self, soup):
        self.description = soup.select_one(
            'section[itemprop="description"]'
        ) or soup.select_one(".description")
        self.blocks = {}
        self.tables = {}
        self.descriptions = {}
        self.memo = {}
        if self.description is not None:
            self._blocks()
            self._tables()
            self._sample_descriptions()

    def _sample_descriptions(self):
        for elem in self.description.select(
            ".description-line, .description-paragraph"
        ):
            text = clean_text(elem)
            if not re.search(r"\bFIG|SEM image", text, re.IGNORECASE):
                continue
            if not re.search(
                r"(?:membrane|separator|film).{0,45}(?:made|formed|obtained|prepared).{0,35}(?:example|ex)",
                text,
                re.IGNORECASE,
            ):
                continue
            samples = {normalize_sample(m[0]) for m in SAMPLE.finditer(text)}
            if len(samples) != 1:
                continue
            names = material_names(text)
            if not names or not names <= {"PE", "PP"}:
                continue
            polymer = (
                "PP/PE/PP"
                if re.search(r"PP\s*/\s*PE\s*/\s*PP", text)
                else material_label(names)
            )
            self.descriptions.setdefault(next(iter(samples)), []).append(
                Identity(
                    polymer,
                    "explicit_sample_description",
                    ({"locator": locator(elem), "text": text},),
                )
            )

    def _blocks(self):
        active = []
        for elem in self.description.select(
            "heading, .description-line, .description-paragraph, table"
        ):
            if elem.name == "table":
                active = []
                continue
            if elem.name != "heading" and elem.find("heading") is not None:
                continue
            text = clean_text(elem)
            if elem.name == "heading":
                text = re.sub(
                    r"\s*\(for reference\)\s*$", "", text, flags=re.IGNORECASE
                )
                if ":" in text and normalize_sample(text.split(":", 1)[0]):
                    text = text.split(":", 1)[0]
            key = normalize_sample(text)
            if key and not re.search(
                r"examples\s+\d+\s*[-–]\s*\d+", text, re.IGNORECASE
            ):
                active = [key]
                self.blocks.setdefault(key, [])
                continue
            # Experimental ranges have one common recipe; a dash inside a sample
            # number (Example 2-1) is not interpreted as a range.
            range_match = re.fullmatch(
                r"[\[(<]?\s*((?:comparative|working|preparation)\s+)?examples?\s+(\d+)\s*(?:to|through|[-–])\s*(?:(?:comparative\s+|working\s+)?example\s+)?(\d+)\s*[\])>]?",
                text,
                re.IGNORECASE,
            )
            if range_match:
                prefix = (
                    range_match[1].strip().capitalize() + " " if range_match[1] else ""
                )
                active = [
                    f"{prefix}Example {i}"
                    for i in range(int(range_match[2]), int(range_match[3]) + 1)
                ]
                for sample in active:
                    self.blocks.setdefault(sample, [])
                continue
            if elem.name == "heading":
                group_pattern = re.compile(
                    r"(?P<kind>comparative|comparison|working|preparation|conventional)?\s*"
                    r"examples?\s+(?P<first>\d+)\s*(?:to|through|[-–])\s*"
                    r"(?:example\s+)?(?P<last>\d+)",
                    re.IGNORECASE,
                )
                groups = list(group_pattern.finditer(text))
                remainder = group_pattern.sub("", text)
                if groups and not re.sub(
                    r"\band\b|[\s\[\](),<>;:*]", "", remainder, flags=re.IGNORECASE
                ):
                    active = []
                    for group in groups:
                        kind = group["kind"] or ""
                        prefix = (
                            "Comparative "
                            if kind.lower().startswith("comp")
                            else (kind.capitalize() + " " if kind else "")
                        )
                        active.extend(
                            f"{prefix}Example {i}"
                            for i in range(int(group["first"]), int(group["last"]) + 1)
                        )
                    for sample in active:
                        self.blocks.setdefault(sample, [])
                    continue
                if re.search(r"example.*\d", text, re.IGNORECASE):
                    active = []
            inline = re.match(
                r"^(?:In|For)\s+((?:Comparative\s+)?Example\s+\d+)\s*[,;:]",
                text,
                re.IGNORECASE,
            )
            if inline:
                active = [normalize_sample(inline[1])]
                self.blocks.setdefault(active[0], [])
            if (
                elem.name == "heading" or (elem.get("id") or "").startswith("h")
            ) and re.search(
                r"test example|evaluation|measurement|claims|industrial applicability|positive electrode|negative electrode|electrolyte|supplementary|reference (?:numeral|sign)",
                text,
                re.IGNORECASE,
            ):
                active = []
            if locator(elem) and text:
                for sample in active:
                    self.blocks[sample].append({"locator": locator(elem), "text": text})
            if elem.find("table") is not None:
                active = []

    def _tables(self):
        from .patent_html import expand_rows

        containers = self.description.find_all(attrs={"id": re.compile(r"^TABLE-")})
        if not containers:
            containers = [
                t
                for t in self.description.find_all("table")
                if t.find_parent("table") is None and locator(t)
            ]
        for table in containers:
            rows = expand_rows(table)
            columns, components, current, section = {}, {}, set(), 0
            for row_index, row in enumerate(rows):
                headers = {
                    i: normalize_sample(c)
                    for i, c in enumerate(row)
                    if normalize_sample(c)
                }
                if len(headers) >= 2 and min(headers) > 0:
                    columns = {}
                    for index, sample in headers.items():
                        above = (
                            rows[row_index - 1][index]
                            if row_index and index < len(rows[row_index - 1])
                            else ""
                        )
                        if re.fullmatch(
                            r"comparative|comp\.?|working", above, re.IGNORECASE
                        ):
                            sample = (
                                "Working "
                                if above.lower() == "working"
                                else "Comparative "
                            ) + sample
                        columns[index] = sample
                    current = set()
                    continue
                if not columns:
                    continue
                if re.search(
                    r"(?:skin|core|first|second|middle|surface).*layer.*(?:resin|composition)|layer [AB]\b",
                    " ".join(row),
                    re.IGNORECASE,
                ):
                    section += 1
                    current = set()
                first = len(row) - len(columns)
                if first < 1 or first > 5:
                    continue
                label = " ".join(row[:first])
                wrapped_label = (
                    label
                    + " "
                    + " ".join(
                        " ".join(following[:first])
                        for following in rows[row_index + 1 : row_index + 3]
                    )
                )
                if re.search(
                    r"binder|adhesive|slurry|coating", wrapped_label, re.IGNORECASE
                ):
                    current = set()
                    continue
                if re.search(
                    r"stretch|physical propert|membrane propert|resin concentration|heat.fix|tensile|porosity",
                    label,
                    re.IGNORECASE,
                ):
                    current = set()
                names = material_names(label)
                if names:
                    current = names
                # Only complete mass recipes can establish absence of other resin.
                if not current or not re.search(
                    r"(?:wt\.?\s*%|mass|weight|content|parts|ratio)",
                    label,
                    re.IGNORECASE,
                ):
                    continue
                if re.search(
                    r"molecular|melting|density|concentration", label, re.IGNORECASE
                ):
                    continue
                if len(current) != 1:
                    continue
                polymer = next(iter(current))
                for ordinal, sample in enumerate(columns.values()):
                    index = first + ordinal
                    value = row[index].strip()
                    if value in {"", "-", "—", "–"}:
                        amount = 0.0
                    elif re.fullmatch(r"\d+(?:\.\d+)?", value):
                        amount = float(value)
                    else:
                        continue
                    components.setdefault(sample, {}).setdefault(section, []).append(
                        (polymer, amount)
                    )
            for sample, sections in components.items():
                if all(
                    abs(sum(v for _, v in parts) - 100) < 0.01
                    for parts in sections.values()
                ):
                    names = {
                        p for parts in sections.values() for p, v in parts if v > 0
                    }
                    self.tables.setdefault(sample, []).append(
                        Identity(
                            material_label(names),
                            "explicit_composition_table",
                            (
                                {
                                    "locator": locator(table),
                                    "text": table.get_text(" ", strip=True),
                                },
                            ),
                        )
                    )

    def resolve(self, sample, visiting=()):
        key = normalize_sample(sample)
        if key is None:
            return Identity(
                None,
                "not_linked_to_recipe",
                reason="Sample label has no unique experimental-example mapping",
            )
        # Patent tables often shorten "Working Example" to "Example". Only
        # accept that alias if a uniquely matching working block exists.
        if (
            key not in self.blocks
            and key not in self.tables
            and key.startswith("Example ")
        ):
            working = "Working " + key
            if working in self.blocks or working in self.tables:
                key = working
        if key in self.memo:
            return self.memo[key]
        if key in visiting:
            return Identity(
                None, "conflicting_recipe", reason="Cyclic example recipe references"
            )
        table_ids = self.tables.get(key, [])
        descriptions = self.descriptions.get(key, [])
        if len({v.polymer for v in table_ids}) == 1:
            result = table_ids[0]
        elif len({v.polymer for v in table_ids}) > 1:
            result = Identity(
                None,
                "conflicting_recipe",
                reason="Multiple composition tables disagree for this sample label",
            )
        elif descriptions and len({v.polymer for v in descriptions}) == 1:
            result = descriptions[0]
        else:
            result = self._resolve_block(key, visiting)
        self.memo[key] = result
        return result

    def _resolve_block(self, key, visiting):
        block = self.blocks.get(key, [])
        direct, links, uncertain_changes = [], [], False
        explicit_bases = set()
        changed_names = set()
        removal = False
        for passage in block:
            text = passage["text"]
            # An introductory conditional sentence must not hide the explicit
            # experimental recipe in the next sentence of the same paragraph.
            sentences = re.split(r"(?<=[.;])\s+(?=[A-Z])", text)
            text = " ".join(s for s in sentences if not OPTIONAL.search(s))
            if re.search(
                r"cathod|anod|current collector|active material paste",
                text,
                re.IGNORECASE,
            ):
                continue
            refs = [
                m
                for m in INHERIT.finditer(text)
                if not re.search(
                    r"prepar.{0,20}(?:battery|cell)|(?:battery|cell).{0,20}(?:prepar|assembl|fabricat)|charging|electrode|electrolyte",
                    text[max(0, m.start() - 80) : m.start()],
                    re.IGNORECASE,
                )
            ]
            links.extend((normalize_sample(m["sample"]), passage) for m in refs)
            names = material_names(text)
            if refs:
                # Composition changes must be supported by a complete table or
                # a direct standalone recipe; never copy a parent's type blindly.
                if names and re.search(
                    r"instead|replac|not used|without|containing no|only\s+(?:poly|PP|PE)|parts by mass|wt\.?\s*%|mass%",
                    text,
                    re.IGNORECASE,
                ):
                    uncertain_changes = True
                    changed_names |= names
                    removal |= bool(
                        re.search(
                            r"instead|replac|not used|without|containing no|only\s+(?:poly|PP|PE)|(?<![\d.])0(?:\.0)?\s*(?:parts|wt|mass)",
                            text,
                            re.IGNORECASE,
                        )
                    )
                continue
            if (
                not names
                or OPTIONAL.search(text)
                or not ACTION.search(text)
                or not (
                    BASE.search(text)
                    or (
                        re.search(r"blend|knead|mix|combin", text, re.IGNORECASE)
                        and re.search(
                            r"wt\.?\s*%|mass|weight|parts", text, re.IGNORECASE
                        )
                    )
                )
            ):
                continue
            if re.search(
                r"tensile|shrinkage|contact angle|electrical resistance",
                text,
                re.IGNORECASE,
            ) and not re.search(
                r"prepar|knead|blend|extrud|as.{0,30}substrate", text, re.IGNORECASE
            ):
                continue
            if COATING.search(text):
                # A coating recipe is not the substrate recipe. Only explicit
                # base-film/substrate material clauses are usable in this block.
                names = explicit_base_names(text)
            if names:
                direct.append((names, passage))
                explicit_bases |= explicit_base_names(text)
        parents = {p for p, _ in links if p and p != key}
        if direct and not parents:
            layered = any(
                re.search(
                    r"first polyolefin|second polyolefin|layer [AB]\b|three.layer|multilayer",
                    p["text"],
                    re.IGNORECASE,
                )
                for p in block
            )
            coating = any(
                re.search(r"coat|slurry|paint", p["text"], re.IGNORECASE) for p in block
            )
            combined = (
                explicit_bases if coating and not layered else set()
            ) or set().union(*(p[0] for p in direct))
            if coating and not layered and not explicit_bases:
                return Identity(
                    None,
                    "coating_material_only",
                    tuple(p[1] for p in direct),
                    "Named polymer is in coating preparation; base substrate material has not been established",
                )
            if len(combined) > 1 and not combined <= {"PE", "PP"}:
                return Identity(
                    None,
                    "complex_material_recipe",
                    tuple(p[1] for p in direct),
                    "Recipe mentions "
                    + material_label(combined)
                    + "; base, additive and layer roles require a sample-specific link",
                )
            return Identity(
                material_label(combined), "explicit_recipe", tuple(p[1] for p in direct)
            )
        if len(parents) == 1:
            parent = self.resolve(next(iter(parents)), (*visiting, key))
            same_family_change = (
                not removal
                and parent.polymer
                and changed_names == set(parent.polymer.split("/"))
            )
            if parent.polymer and (not uncertain_changes or same_family_change):
                # A child paragraph may describe only the changed layer. Keep
                # the complete parent recipe, including the unchanged layers.
                combined = set(parent.polymer.split("/"))
                for names, _ in direct:
                    combined |= names
                if len(combined) > 1 and not combined <= {"PE", "PP"}:
                    return Identity(
                        None,
                        "complex_material_recipe",
                        parent.evidence + tuple(p for _, p in direct),
                        "Changed recipe has multiple polymer roles: "
                        + material_label(combined),
                    )
                return Identity(
                    material_label(combined),
                    "inherited_recipe",
                    parent.evidence
                    + tuple(p for _, p in links)
                    + tuple(p for _, p in direct),
                )
        if links and uncertain_changes:
            return Identity(
                None,
                "changed_recipe_needs_link",
                tuple(p for _, p in links),
                "Inherited recipe changes material composition; exact resulting recipe not yet linked",
            )
        if parents:
            return Identity(
                None,
                "recipe_reference_not_linked",
                tuple(p for _, p in links),
                "Referenced sample recipe has not been resolved: "
                + ", ".join(sorted(parents)),
            )
        if block and any("polyolefin" in p["text"].lower() for p in block):
            return Identity(
                None,
                "generic_polyolefin_only",
                tuple(p for p in block if "polyolefin" in p["text"].lower())[:2],
                "Sample recipe names polyolefin but does not establish a specific PE/PP composition",
            )
        return Identity(
            None,
            "not_linked_to_recipe" if block else "sample_label_not_found",
            reason="No complete sample-specific material recipe linked; document-wide mentions are insufficient",
        )
