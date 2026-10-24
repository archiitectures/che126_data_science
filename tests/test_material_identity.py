import pytest

from che126_data_science.data_mining.material_identity import PatentIdentities


def identities(html):
    bs4 = pytest.importorskip("bs4")
    return PatentIdentities(
        bs4.BeautifulSoup(
            '<section itemprop="description">' + html + "</section>", "lxml"
        )
    )


def test_recipe_inheritance_changes_process_but_not_material():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyethylene composition was prepared by blending HDPE and UHMWPE powders.</div>
      <heading>Example 2</heading>
      <div class="description-line" id="p2">A membrane was prepared in the same manner as Example 1 except that stretching was at 115 C.</div>
      <heading>Comparative Example 1</heading>
      <div class="description-line" id="p3">A polypropylene porous film was used as the substrate.</div>""")
    result = resolver.resolve("Ex.2")
    assert result.polymer == "PE" and result.status == "inherited_recipe"
    assert {e["locator"] for e in result.evidence} == {"p1", "p2"}
    assert resolver.resolve("Comp.Ex.1").polymer == "PP"


def test_background_and_optional_lists_do_not_establish_sample_material():
    resolver = identities("""
      <div class="description-line" id="background">Polyethylene and polypropylene were used in prior art.</div>
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyolefin porous substrate was used.</div>
      <div class="description-line" id="p2">The substrate may be polyethylene or polypropylene.</div>""")
    result = resolver.resolve("Example 1")
    assert result.polymer is None and result.status == "generic_polyolefin_only"


def test_composition_change_is_not_blindly_inherited():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polypropylene porous film was used as the substrate.</div>
      <heading>Example 2</heading>
      <div class="description-line" id="p2">The same manner as Example 1 was used except polyethylene was used instead of polypropylene.</div>""")
    assert resolver.resolve("Example 2").polymer is None
    assert resolver.resolve("Example 2").status == "changed_recipe_needs_link"


def test_cyclic_and_missing_recipe_links_are_unassigned():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">Prepared in the same manner as Example 2.</div>
      <heading>Example 2</heading>
      <div class="description-line" id="p2">Prepared in the same manner as Example 1.</div>""")
    assert resolver.resolve("Example 1").polymer is None
    assert resolver.resolve("Example 55").polymer is None


def test_coating_is_not_mislabeled_as_base_polymer():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A PVDF slurry was prepared and coated on a polyethylene porous substrate.</div>""")
    assert resolver.resolve("Example 1").polymer == "PE"


def test_complete_composition_table_links_sample_columns():
    resolver = identities("""
      <table id="t1"><tr><td>Component</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>HDPE</td><td></td><td></td></tr>
      <tr><td>Parts by mass</td><td>80</td><td>100</td></tr>
      <tr><td>PP</td><td></td><td></td></tr>
      <tr><td>Parts by mass</td><td>20</td><td>0</td></tr></table>""")
    assert resolver.resolve("Example 1").polymer == "PE/PP"
    assert resolver.resolve("Example 2").polymer == "PE"
    assert resolver.resolve("Example 2").evidence[0]["locator"] == "t1"


def test_incomplete_and_conflicting_tables_do_not_assign_material():
    resolver = identities("""
      <table id="t1"><tr><td>Component</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>HDPE parts by mass</td><td>70</td><td>100</td></tr></table>
      <table id="t2"><tr><td>Component</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>PP parts by mass</td><td>70</td><td>100</td></tr></table>""")
    assert resolver.resolve("Example 1").polymer is None
    assert resolver.resolve("Example 2").status == "conflicting_recipe"


def test_pressure_abbreviation_is_not_polyamide_and_comparison_is_boundary():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyethylene porous film was prepared at 100 Pa.</div>
      <heading>Comparison Example 1</heading>
      <div class="description-line" id="p2">A polypropylene porous film was used as a substrate.</div>""")
    assert resolver.resolve("Example 1").polymer == "PE"
    assert resolver.resolve("Comparative Example 1").polymer == "PP"


def test_battery_preparation_reference_does_not_link_separator_recipe():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyethylene porous film was used as the substrate.</div>
      <heading>Example 2</heading>
      <div class="description-line" id="p2">Charging was evaluated after preparing a battery in the same manner as Example 1.</div>""")
    assert resolver.resolve("Example 2").polymer is None


def test_group_headings_do_not_leak_into_following_comparison():
    resolver = identities("""
      <heading>Working Examples 1 to 3</heading>
      <div class="description-line" id="p1">A polyethylene porous film was used as the substrate.</div>
      <heading>Conventional Example 1</heading>
      <div class="description-line" id="p2">A polypropylene porous film was prepared.</div>""")
    assert resolver.resolve("Example 2").polymer == "PE"
    assert resolver.resolve("Conventional Example 1").polymer == "PP"


def test_ratio_changes_preserve_proven_polymer_family_but_not_removal():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyethylene composition was prepared by blending HDPE and UHMWPE powders.</div>
      <heading>Example 2</heading>
      <div class="description-line" id="p2">Prepared in the same manner as Example 1 except 70.0 parts by mass of HDPE and 30.0 parts by mass of UHMWPE were used.</div>""")
    assert resolver.resolve("Example 2").polymer == "PE"


def test_child_layer_description_keeps_unchanged_parent_materials():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyolefin composition was prepared by blending 80 parts polyethylene and 20 parts polypropylene.</div>
      <heading>Example 2</heading>
      <div class="description-line" id="p2">A membrane was obtained in the same manner as Example 1 except the stretching temperature was changed.</div>
      <div class="description-line" id="p3">The polypropylene resin used for the layer was prepared by extrusion.</div>""")
    assert resolver.resolve("Example 2").polymer == "PE/PP"


def test_separate_coating_recipe_and_electrode_binder_do_not_pollute_base():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">PVDF was mixed in a mass ratio of 90:10 to prepare a resin solution.</div>
      <div class="description-line" id="p2">A polyethylene porous film was used as the substrate and coated with the solution.</div>
      <div class="description-line" id="p3">PVDF was mixed by weight to prepare a cathodic active material paste.</div>""")
    assert resolver.resolve("Example 1").polymer == "PE"


def test_crystal_dispersion_is_not_coating_and_tables_end_recipe_blocks():
    resolver = identities("""
      <heading>Example 1</heading>
      <div class="description-line" id="p1">A polyethylene and polypropylene resin composition was dry-blended by mass. Crystal dispersion temperature was measured.</div>
      <table id="results"><tr><td>Thickness</td><td>5</td></tr></table>
      <div class="description-line" id="p2">A polyamide raw material was prepared by blending.</div>""")
    assert resolver.resolve("Example 1").polymer == "PE/PP"


def test_split_patent_table_layers_and_comparative_headers_are_linked():
    resolver = identities("""
      <tables id="TABLE-US-00001"><table>
      <tr><td></td><td>Comparative</td><td>Comparative</td></tr>
      <tr><td></td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>Surface layer resin composition</td></tr>
      <tr><td>HDPE</td><td>Content (wt %)</td><td>80</td><td>100</td></tr>
      <tr><td>PP</td><td>Content (wt %)</td><td>20</td><td>0</td></tr>
      <tr><td>Core layer resin composition</td></tr>
      <tr><td>HDPE</td><td>Content (wt %)</td><td>100</td><td>100</td></tr>
      </table></tables>""")
    assert resolver.resolve("Comparative Example 1").polymer == "PE/PP"
    assert resolver.resolve("Comparative Example 2").polymer == "PE"
    assert resolver.resolve("Example 1").polymer is None


def test_binder_composition_table_does_not_assign_separator_base_material():
    resolver = identities("""
      <table id="t1"><tr><td>Property</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>PVDF:PVAc (parts by weight)</td><td>0:100</td><td>20:80</td></tr>
      <tr><td>Content of amorphous adhesive binder (parts by weight)</td><td>100</td><td>100</td></tr></table>""")
    assert resolver.resolve("Example 1").polymer is None
    assert resolver.resolve("Example 2").polymer is None


def test_wrapped_binder_label_does_not_supply_pure_base_material():
    resolver = identities("""
      <table id="t1"><tr><td>Property</td><td>Example 1</td><td>Example 2</td></tr>
      <tr><td>PVDF:PVAc (parts by weight)</td><td>0:100</td><td>20:80</td></tr>
      <tr><td>Content of</td><td>100</td><td>80</td></tr>
      <tr><td>amorphous adhesive</td></tr>
      <tr><td>binder polymer</td></tr></table>""")
    assert resolver.resolve("Example 1").polymer is None
    assert resolver.resolve("Example 2").polymer is None
