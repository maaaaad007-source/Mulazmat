from firststapp import countries
from firststapp.filters import EXPERIENCE_LEVELS, values_for


def test_options_are_alphabetical_after_the_sentinel():
    options = countries.country_options()
    assert options[0] == countries.ANYWHERE
    assert options[1:] == sorted(options[1:])


def test_country_list_has_no_duplicates():
    assert len(countries.COUNTRIES) == len(set(countries.COUNTRIES))


def test_every_geo_id_maps_to_a_real_country():
    assert set(countries.GEO_IDS) <= set(countries.COUNTRIES)


def test_geo_id_lookup():
    assert countries.geo_id_for("Netherlands") == "102890719"
    assert countries.geo_id_for("Tuvalu") == ""


def test_location_string():
    assert countries.location_string("Netherlands") == "Netherlands"
    assert countries.location_string("Netherlands", "Utrecht") == "Utrecht, Netherlands"
    assert countries.location_string(countries.ANYWHERE) == ""
    assert countries.location_string(countries.ANYWHERE, "Utrecht") == "Utrecht"


def test_values_for_translates_labels_and_skips_unknowns():
    assert values_for(["Entry level", "Director"], EXPERIENCE_LEVELS) == ("2", "5")
    assert values_for(["Nonsense"], EXPERIENCE_LEVELS) == ()
