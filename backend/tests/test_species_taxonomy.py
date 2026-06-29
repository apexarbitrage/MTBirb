"""Hermetic tests for eBird taxonomy mapping + name ranking (no DB, no network)."""

from app.services.species_taxonomy import rank_by_name, taxon_from_record

OWL_RECORD = {
    "speciesCode": "grhowl",
    "comName": "Great Horned Owl",
    "sciName": "Bubo virginianus",
    "category": "species",
}


def test_taxon_from_record_maps_fields() -> None:
    t = taxon_from_record(OWL_RECORD)
    assert t is not None
    assert t.species_code == "grhowl"
    assert t.common_name == "Great Horned Owl"
    assert t.scientific_name == "Bubo virginianus"


def test_taxon_from_record_without_code_or_name_is_skipped() -> None:
    assert taxon_from_record({"comName": "X", "sciName": "Y"}) is None
    assert taxon_from_record({"speciesCode": "x", "sciName": "Y"}) is None


def test_taxon_from_record_tolerates_missing_scientific_name() -> None:
    t = taxon_from_record({"speciesCode": "x", "comName": "X"})
    assert t is not None
    assert t.scientific_name == ""


def test_rank_by_name_lifts_prefix_match_above_mid_string_match() -> None:
    matches = [
        {"species_code": "a", "common_name": "American Crow"},
        {"species_code": "b", "common_name": "Crow"},
    ]
    ranked = rank_by_name(matches, "crow")
    assert [m["species_code"] for m in ranked] == ["b", "a"]


def test_rank_by_name_alphabetical_within_tier() -> None:
    matches = [
        {"species_code": "a", "common_name": "Owl, Great Horned"},
        {"species_code": "b", "common_name": "Barred Owl"},
        {"species_code": "c", "common_name": "Barn Owl"},
    ]
    ranked = rank_by_name(matches, "owl")
    assert [m["species_code"] for m in ranked] == ["a", "c", "b"]


def test_rank_by_name_is_case_insensitive() -> None:
    matches = [{"species_code": "a", "common_name": "great horned owl"}]
    assert rank_by_name(matches, "GREAT") == matches
